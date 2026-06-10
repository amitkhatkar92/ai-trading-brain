"""
Candidate Store — Phase C
=========================
Persistent daily candidate universe for the Multi-Stage Market Preparation Engine.

Responsibilities:
  - Atomic write of daily_candidates.json (tmp → rename, never partial reads)
  - Schema versioning + checksum validation
  - Freshness enforcement (28-hour max file age)
  - Coverage validation (rejects files below PREPARED_UNIVERSE_MIN_COVERAGE_PCT)
  - UTC-only timestamps (no local time assumptions)

Dependencies:
  - Python stdlib only (json, pathlib, hashlib, datetime)
  - NO imports from any trading layer (Layers 1-17)

Rollback: set USE_PREPARED_UNIVERSE = False in config.py → this module is never called.
"""

from __future__ import annotations

import hashlib
import json
import os
import time as _time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from utils import get_logger

log = get_logger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────
SCHEMA_VERSION    = "1.0"
STORE_FILE        = Path(__file__).parent.parent / "data" / "daily_candidates.json"
MEMORY_FILE       = Path(__file__).parent.parent / "data" / "scanner_memory.json"
MAX_AGE_HOURS     = 28          # candidate file older than this → treat as invalid
MIN_COVERAGE_PCT  = 60.0        # below this → file rejected (partial scan)


# ── Candidate record keys consumed by _identify_setup() ─────────────────────
# These MUST be present and non-zero for a candidate to enter the live pipeline.
_REQUIRED_FIELDS = ("symbol", "resistance", "support", "rsi", "volume_ratio")

# ── Candidate lifecycle state constants ─────────────────────────────────────
# Derived at runtime from candidate attributes + live market data.
# Persisted to store file via update_enrichment() after each scan cycle.
# See: compute_lifecycle_state() below for transition logic.
LIFECYCLE_FRESH       = "FRESH"          # < 6h since preparation, momentum intact
LIFECYCLE_ACTIVE      = "ACTIVE"         # > 6h, setup ongoing and confirmed
LIFECYCLE_WEAKENING   = "WEAKENING"      # 2+ deterioration signals detected
LIFECYCLE_INVALIDATED = "INVALIDATED"    # structural price-action failure
LIFECYCLE_EXPIRED     = "EXPIRED"        # TTL elapsed (not revived by refresh)
LIFECYCLE_REACTIVATED = "REACTIVATED"    # TTL was extended by intraday refresh

# ── Enrichment persistence throttle ─────────────────────────────────────────
# update_enrichment() writes at most once per 5 minutes to avoid write storms.
_ENRICHMENT_LAST_WRITE_TS: float = 0.0
_ENRICHMENT_WRITE_INTERVAL: float = 300.0  # seconds
_ENRICHMENT_REQUIRED_FIELDS = frozenset({
    "strategy", "lifecycle_state", "data_trust_score",
    "conviction_score", "candidate_origin",
})
_VALID_LIFECYCLE_STATES = frozenset({
    "FRESH", "ACTIVE", "WEAKENING", "INVALIDATED", "EXPIRED", "REACTIVATED", "UNKNOWN",
})


def _apply_baseline_enrichment(c: Dict[str, Any]) -> None:
    """
    Apply baseline enrichment defaults to a candidate dict in-place.
    Only fills fields that are None or empty-string — never overwrites existing values.

    Derives lifecycle_state from valid_until_utc TTL (FRESH if valid, EXPIRED if elapsed)
    and momentum_state from RSI.

    Called by:
    - CandidateStore.write()                    — all candidates enriched at write time
    - CandidateStore.backfill_baseline_enrichment() — for pre-existing store files

    Tags: [BaselineEnrichment] emitted by caller context.
    """
    # Derive lifecycle_state from TTL
    _vu = c.get("valid_until_utc") or ""
    _lc_default = "FRESH"
    if _vu:
        try:
            _exp = datetime.fromisoformat(_vu.replace("Z", "+00:00"))
            if datetime.now(timezone.utc) > _exp:
                _lc_default = "EXPIRED"
        except Exception:
            pass

    # Derive momentum_state from RSI
    _rsi = float(c.get("rsi") or 50)
    _momentum = (
        "overbought" if _rsi > 70 else
        "oversold"   if _rsi < 30 else
        "strong"     if _rsi > 60 else
        "weak"       if _rsi < 40 else
        "neutral"
    )

    _defaults: Dict[str, Any] = {
        "strategy":              "pending_scan",
        "lifecycle_state":       _lc_default,
        "data_trust_score":      1.0,
        "conviction_score":      0.0,
        "invalidation_state":    "valid",
        "exploration_flag":      False,
        "refinement_status":     "raw",
        "candidate_origin":      "prepared_universe",
        "momentum_state":        _momentum,
        "breakout_state":        "unknown",
        "freshness_age_minutes": 0,
        "last_refresh_time":     "",  # populated by write() with prepared_at timestamp
        "fallback_contaminated": False,
        "corruption_flags":      [],
        "simulation_status":     "live",
        "rerank_reason":         "",
        "regime_bias_applied":   "",
    }

    for _fk, _fv in _defaults.items():
        if c.get(_fk) is None or c.get(_fk) == "":
            c[_fk] = _fv


class CandidateStore:
    """
    Manages read/write of data/daily_candidates.json.

    All methods are class-methods — no instantiation needed.
    """

    # ── Write ────────────────────────────────────────────────────────────────

    @classmethod
    def write(
        cls,
        candidates: List[Dict[str, Any]],
        context: Dict[str, Any],
        scanner_stats: Dict[str, Any],
        premarket_refresh_complete: bool = False,
        premarket_refreshed_at: Optional[str] = None,
    ) -> bool:
        """
        Atomically write the candidate store file.

        Returns True on success, False on any failure.
        The live engine is never affected if this write fails — it will simply
        continue using the previous day's file (or static fallback if stale).
        """
        try:
            # Baseline enrichment — fill all enrichment fields at write time.
            # Architecture: scanner → baseline enrichment → candidate persistence
            # → execution refinement → forensic updates.
            _write_prepared_at = _utcnow_iso()  # single timestamp for all candidates
            for _wc in candidates:
                _apply_baseline_enrichment(_wc)
                # Bug fix: stamp each candidate with prepared_at so read() consumers
                # can compute freshness_age_minutes without the payload-level field.
                if not _wc.get("prepared_at"):
                    _wc["prepared_at"] = _write_prepared_at
                # Bug fix: last_refresh_time should be actual prep time, not expiry.
                if not _wc.get("last_refresh_time"):
                    _wc["last_refresh_time"] = _write_prepared_at
            log.info(
                "[BaselineEnrichment] Applied write-time baseline to %d candidates.",
                len(candidates),
            )

            payload: Dict[str, Any] = {
                "schema_version":             SCHEMA_VERSION,
                "timezone":                   "UTC",
                "prepared_at":                _write_prepared_at,
                "premarket_refreshed_at":     premarket_refreshed_at,
                "premarket_refresh_complete": premarket_refresh_complete,
                "context":                    context,
                "scanner_stats":              scanner_stats,
                "candidates":                 candidates,
            }
            # Add checksum over candidates payload (detects corruption / truncation)
            payload["checksum"] = _checksum(candidates)

            # Validate coverage before writing
            coverage = scanner_stats.get("coverage_pct", 0.0)
            if coverage < MIN_COVERAGE_PCT:
                log.warning(
                    "[CandidateStore] Coverage %.1f%% below minimum %.1f%% — NOT writing file.",
                    coverage, MIN_COVERAGE_PCT,
                )
                return False

            # Atomic write: tmp → rename
            tmp_path = STORE_FILE.with_suffix(".json.tmp")
            STORE_FILE.parent.mkdir(parents=True, exist_ok=True)
            tmp_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
            tmp_path.replace(STORE_FILE)

            log.info(
                "[CandidateStore] Written: candidates=%d coverage=%.1f%% prepared_at=%s",
                len(candidates), coverage, payload["prepared_at"],
            )
            return True

        except Exception as exc:
            log.error("[CandidateStore] Write failed: %s", exc)
            return False

    # ── Read ─────────────────────────────────────────────────────────────────

    @classmethod
    def read(cls) -> Optional[List[Dict[str, Any]]]:
        """
        Read and validate the candidate store.

        Returns the candidates list if the file is:
          - present
          - fresh (< MAX_AGE_HOURS old)
          - valid schema version
          - checksum-passing
          - sufficient coverage

        Returns None on any failure — callers must fall back to static watchlist.
        Logs the specific failure reason for every rejection.
        """
        try:
            if not STORE_FILE.exists():
                log.debug("[CandidateStore] File not found: %s", STORE_FILE)
                return None

            raw = STORE_FILE.read_text(encoding="utf-8")
            payload = json.loads(raw)

            # Schema version check
            if payload.get("schema_version") != SCHEMA_VERSION:
                log.warning(
                    "[CandidateStore] Schema mismatch: file=%s expected=%s — rejecting.",
                    payload.get("schema_version"), SCHEMA_VERSION,
                )
                return None

            # Freshness check
            prepared_at_str = payload.get("prepared_at", "")
            age_hours = _age_hours(prepared_at_str)
            if age_hours is None or age_hours > MAX_AGE_HOURS:
                log.warning(
                    "[CandidateStore] File stale: age=%.1fh max=%dh — "
                    "[StaticFallbackActivated] reason=FILE_STALE last_prepared_at=%s",
                    age_hours or -1, MAX_AGE_HOURS, prepared_at_str,
                )
                return None

            # Coverage check
            stats    = payload.get("scanner_stats", {})
            coverage = float(stats.get("coverage_pct", 0.0))
            if coverage < MIN_COVERAGE_PCT:
                log.warning(
                    "[CandidateStore] Coverage %.1f%% < minimum %.1f%% — "
                    "[StaticFallbackActivated] reason=LOW_COVERAGE",
                    coverage, MIN_COVERAGE_PCT,
                )
                return None

            candidates = payload.get("candidates", [])

            # Checksum verification
            expected_checksum = payload.get("checksum", "")
            actual_checksum   = _checksum(candidates)
            if expected_checksum and expected_checksum != actual_checksum:
                log.error(
                    "[CandidateStore] Checksum mismatch — file may be corrupt. "
                    "[StaticFallbackActivated] reason=CHECKSUM_FAIL"
                )
                return None

            # Field validation: drop candidates missing required fields
            valid = [c for c in candidates if _is_valid_candidate(c)]
            dropped = len(candidates) - len(valid)
            if dropped:
                log.warning("[CandidateStore] Dropped %d candidates with missing required fields.", dropped)

            if not valid:
                log.warning("[CandidateStore] No valid candidates after field validation — "
                            "[StaticFallbackActivated] reason=NO_VALID_CANDIDATES")
                return None

            # Bug fix (backward compat): inject payload-level prepared_at into candidates
            # that were written before per-candidate stamping was introduced.
            _payload_pa = payload.get("prepared_at", "")
            if _payload_pa:
                for _rc in valid:
                    if not _rc.get("prepared_at"):
                        _rc["prepared_at"] = _payload_pa
                    if not _rc.get("last_refresh_time"):
                        _rc["last_refresh_time"] = _payload_pa

            premarket_complete = payload.get("premarket_refresh_complete", False)
            premarket_at = payload.get("premarket_refreshed_at") or "not_yet"
            log.debug(
                "[CandidateStore] Loaded: candidates=%d age=%.1fh coverage=%.1f%%"
                " premarket_complete=%s premarket_at=%s",
                len(valid), age_hours, coverage, premarket_complete, premarket_at,
            )
            return valid

        except json.JSONDecodeError as exc:
            log.error("[CandidateStore] JSON parse error: %s — "
                      "[StaticFallbackActivated] reason=PARSE_ERROR", exc)
            return None
        except Exception as exc:
            log.error("[CandidateStore] Unexpected read error: %s — "
                      "[StaticFallbackActivated] reason=EXCEPTION", exc)
            return None

    # ── Premarket update ─────────────────────────────────────────────────────

    @classmethod
    def update_premarket(
        cls,
        updated_candidates: List[Dict[str, Any]],
        complete: bool,
    ) -> bool:
        """
        Update candidates section with premarket-refined data.
        Preserves the original context and scanner_stats sections.
        Sets premarket_refresh_complete = complete.
        """
        try:
            if not STORE_FILE.exists():
                log.warning("[CandidateStore] Cannot update premarket — store file not found.")
                return False

            payload = json.loads(STORE_FILE.read_text(encoding="utf-8"))
            payload["candidates"]                 = updated_candidates
            # Elevate refinement_status for all premarket-processed candidates
            for _pc in updated_candidates:
                if not _pc.get("refinement_status") or _pc.get("refinement_status") == "raw":
                    _pc["refinement_status"] = "premarket_refined"
            payload["premarket_refreshed_at"]     = _utcnow_iso()
            payload["premarket_refresh_complete"] = complete
            payload["checksum"]                   = _checksum(updated_candidates)

            tmp_path = STORE_FILE.with_suffix(".json.tmp")
            tmp_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
            tmp_path.replace(STORE_FILE)

            log.info(
                "[CandidateStore] Premarket update: candidates=%d complete=%s",
                len(updated_candidates), complete,
            )
            return True
        except Exception as exc:
            log.error("[CandidateStore] Premarket update failed: %s", exc)
            return False

    # ── Fix 1: Intraday expired-candidate refresh ─────────────────────────────

    @classmethod
    def refresh_expired(
        cls,
        fresh_prices: Dict[str, float],
        extend_hours: float = 4.0,
    ) -> int:
        """
        Re-validate expired candidates against current live prices.

        For each candidate whose valid_until_utc has passed, check whether
        its setup conditions still hold (price within ±5% of base_ltp at
        scan time).  If yes, extend valid_until_utc by ``extend_hours`` from
        now and write the store atomically.

        Args:
            fresh_prices: mapping of bare symbol → current LTP (e.g. from
                          data_feed_manager.get_multiple_quotes).
            extend_hours: how many hours to extend a revived candidate's TTL.

        Returns:
            Number of candidates whose TTL was extended (0 if nothing changed
            or the store file is absent / unreadable).
        """
        if not fresh_prices:
            return 0
        try:
            if not STORE_FILE.exists():
                return 0
            payload = json.loads(STORE_FILE.read_text(encoding="utf-8"))
            candidates: List[Dict[str, Any]] = payload.get("candidates", [])
            now_utc   = datetime.now(timezone.utc)
            extended  = 0

            for c in candidates:
                vu = c.get("valid_until_utc")
                if not vu:
                    continue
                try:
                    expiry = datetime.fromisoformat(vu.replace("Z", "+00:00"))
                except Exception:
                    continue
                if expiry >= now_utc:
                    continue   # still valid — leave untouched

                sym       = c.get("symbol", "")
                base_ltp  = c.get("base_ltp", 0.0) or 0.0
                live_ltp  = fresh_prices.get(sym, 0.0)

                # Keep candidate only when price is within ±5% of stored base_ltp
                if base_ltp > 0 and live_ltp > 0:
                    drift_pct = abs(live_ltp - base_ltp) / base_ltp
                    if drift_pct <= 0.05:
                        new_expiry = now_utc.replace(microsecond=0)
                        import datetime as _dt_mod
                        new_expiry = now_utc + _dt_mod.timedelta(hours=extend_hours)
                        c["valid_until_utc"] = new_expiry.strftime("%Y-%m-%dT%H:%M:%SZ")
                        c["base_ltp"]        = round(live_ltp, 2)   # anchor to today's price
                        extended += 1
                        log.debug(
                            "[RefreshValidationAudit] symbol=%s base_ltp=%.2f live_ltp=%.2f "
                            "drift_pct=%.2f%% result=EXTENDED new_expiry=%s",
                            sym, base_ltp, live_ltp, drift_pct * 100,
                            c["valid_until_utc"],
                        )
                    else:
                        log.debug(
                            "[RefreshValidationAudit] symbol=%s base_ltp=%.2f live_ltp=%.2f "
                            "drift_pct=%.2f%% result=SKIPPED_DRIFT_TOO_HIGH",
                            sym, base_ltp, live_ltp, drift_pct * 100,
                        )
                elif live_ltp == 0:
                    log.debug(
                        "[RefreshValidationAudit] symbol=%s base_ltp=%.2f live_ltp=0 "
                        "result=SKIPPED_NO_LIVE_PRICE",
                        sym, base_ltp,
                    )

            if extended:
                payload["candidates"] = candidates
                payload["checksum"]   = _checksum(candidates)
                tmp_path = STORE_FILE.with_suffix(".json.tmp")
                tmp_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
                tmp_path.replace(STORE_FILE)
                log.info(
                    "[CandidateStore] refresh_expired: extended %d/%d expired candidates"
                    " by %.0fh — store updated.",
                    extended, len(candidates), extend_hours,
                )

            # ── [RefreshValidationAudit] summary ───────────────────────
            def _is_expired(vu_str: str) -> bool:
                try:
                    return datetime.fromisoformat(vu_str.replace("Z", "+00:00")) < now_utc
                except Exception:
                    return False

            _exp_total = sum(
                1 for c in candidates
                if _is_expired(c.get("valid_until_utc") or "")
            )
            _has_price = sum(1 for c in candidates
                             if c.get("symbol") in fresh_prices and fresh_prices[c["symbol"]] > 0)
            log.info(
                "[RefreshValidationAudit] candidates_total=%d expired_at_start=%d "
                "prices_available=%d extended=%d "
                "dominant_skip_reason=%s",
                len(candidates), _exp_total + extended,
                _has_price, extended,
                "NONE" if extended > 0 else (
                    "NO_PRICES" if _has_price == 0 else "PRICE_DRIFT_EXCEEDED"
                ),
            )

            return extended

        except Exception as exc:
            log.error("[CandidateStore] refresh_expired failed: %s", exc)
            return 0
    # ── V2: Smart conviction decay ─────────────────────────────────────────

    @classmethod
    def apply_conviction_decay(
        cls,
        candidates: List[Dict[str, Any]],
        price_map: Dict[str, float],
        rsi_map: Optional[Dict[str, float]] = None,
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        Apply context-sensitive conviction decay to candidate scores IN-MEMORY.

        Modifies the score field of each candidate dict in place.
        Does NOT write to disk — use after CandidateStore.read() for in-cycle
        priority adjustment only.

        Returns (candidates, log_lines) where log_lines lists notable decays.

        Decay rules (single worst-applicable rule, never stacked):
          vol_collapse      vol_ratio < 0.40                    → ×0.840 (fastest)
          momentum_extreme  RSI > 72 or RSI < 28               → ×0.910
          vol_compression   ATR/ltp < 0.5%                     → ×0.925
          aging             estimated age > 12h                → ×0.950
          vol_continuation  vol_ratio ≥ 2.0                    → ×0.972
          strong_breakout   vol_ratio ≥ 3.0 + ltp near res     → ×0.988 (slowest)
          normal            default                            → ×0.980
        """
        if not candidates:
            return candidates, []

        now_utc   = datetime.now(timezone.utc)
        rsi_map   = rsi_map or {}
        log_lines: List[str] = []

        for c in candidates:
            sym       = c.get("symbol", "")
            score     = float(c.get("score",        0.5) or 0.5)
            vol_ratio = float(c.get("volume_ratio", 1.0) or 1.0)
            live_ltp  = float(price_map.get(sym, 0) or 0)
            live_rsi  = rsi_map.get(sym) or float(c.get("rsi", 50) or 50)
            res       = float(c.get("resistance",   0) or 0)
            sup       = float(c.get("support",      0) or 0)
            atr       = float(c.get("atr14",        0) or 0)

            if atr <= 0 and res > sup > 0:
                atr = (res - sup) * 0.40
            if atr <= 0 and live_ltp > 0:
                atr = live_ltp * 0.020

            # Estimate age from remaining TTL (24h original assumed)
            age_h = 0.0
            vu = c.get("valid_until_utc")
            if vu:
                try:
                    expiry = datetime.fromisoformat(vu.replace("Z", "+00:00"))
                    remaining_h = (expiry - now_utc).total_seconds() / 3600.0
                    age_h = max(0.0, 24.0 - remaining_h)
                except Exception:
                    pass

            near_res = res > 0 and live_ltp > 0 and abs(live_ltp - res) / res <= 0.025

            if vol_ratio < 0.40:
                rate, reason = 0.840, "vol_collapse"
            elif live_rsi > 72 or live_rsi < 28:
                rate, reason = 0.910, "momentum_extreme"
            elif atr > 0 and live_ltp > 0 and atr / live_ltp < 0.005:
                rate, reason = 0.925, "vol_compression"
            elif age_h > 12.0:
                rate, reason = 0.950, "aging"
            elif vol_ratio >= 3.0 and near_res:
                rate, reason = 0.988, "strong_breakout"
            elif vol_ratio >= 2.0:
                rate, reason = 0.972, "vol_continuation"
            else:
                rate, reason = 0.980, "normal"

            new_score = round(score * rate, 4)
            if abs(new_score - score) > 0.0005:
                c["score"] = new_score
                if reason != "normal":
                    log_lines.append(f"{sym}:{score:.3f}→{new_score:.3f}[{reason}]")

        return candidates, log_lines

    # ── Enrichment persistence ────────────────────────────────────────────────

    @classmethod
    def update_enrichment(
        cls,
        enrichment_map: Dict[str, Dict[str, Any]],
    ) -> bool:
        """
        Patch 2 (wiring) — Overlay enrichment metadata onto existing candidates.

        Throttled: at most once per 5 minutes to prevent write storms.
        Atomic write: tmp → rename.

        Args:
            enrichment_map: {symbol: {strategy, lifecycle_state, data_trust_score, ...}}

        Returns True on successful write, False if throttled or on error.

        Emits: [EnrichedCandidateWrite], [CandidateSerializationValidation],
               [PersistenceDriftAudit], [CandidateMetadataCoverage],
               [CandidateStrategyIntegrity], [CandidateLifecycleIntegrity],
               [CandidateTrustIntegrity]
        """
        global _ENRICHMENT_LAST_WRITE_TS

        if not enrichment_map:
            return False

        # Priority 8 (IntegrityPersistenceAudit): record every attempt
        try:
            from opportunity_engine.integrity_persistence_audit import get_integrity_audit as _gia
            _gia().record_attempt()
        except Exception:
            pass

        # Throttle: skip if last write was too recent
        now_ts = _time.monotonic()
        if now_ts - _ENRICHMENT_LAST_WRITE_TS < _ENRICHMENT_WRITE_INTERVAL:
            try:
                from opportunity_engine.integrity_persistence_audit import get_integrity_audit as _gia
                _gia().record_throttled()
            except Exception:
                pass
            return False

        try:
            if not STORE_FILE.exists():
                return False

            payload = json.loads(STORE_FILE.read_text(encoding="utf-8"))
            candidates: List[Dict[str, Any]] = payload.get("candidates", [])
            if not candidates:
                return False

            # Patch 6 — Serialization validation: audit enrichment map before write
            valid_count = 0
            invalid_count = 0
            for _v_sym, _v_enrich in enrichment_map.items():
                _missing = _ENRICHMENT_REQUIRED_FIELDS - set(_v_enrich.keys())
                if _missing:
                    invalid_count += 1
                    log.debug(
                        "[CandidateSerializationValidation] symbol=%s missing_fields=%s — will default",
                        _v_sym, sorted(_missing),
                    )
                else:
                    valid_count += 1
            log.debug(
                "[CandidateSerializationValidation] enrichment_map: valid=%d invalid=%d total=%d",
                valid_count, invalid_count, len(enrichment_map),
            )

            # Overlay enrichment onto each matching candidate
            enriched_count = 0
            drift_count = 0
            for c in candidates:
                _sym = c.get("symbol", "")
                if _sym not in enrichment_map:
                    continue
                _enrich = enrichment_map[_sym]

                # Patch 7 — PersistenceDriftAudit: detect field changes
                _old_strategy = c.get("strategy")
                _old_lc = c.get("lifecycle_state")

                # Patch 4 — Lifecycle validation
                _lc = _enrich.get("lifecycle_state", "ACTIVE")
                if _lc not in _VALID_LIFECYCLE_STATES:
                    log.debug(
                        "[CandidateLifecycleIntegrity] symbol=%s invalid_lifecycle=%s — defaulting to ACTIVE",
                        _sym, _lc,
                    )
                    _lc = "ACTIVE"

                # Patch 5 — Trust score validation
                _trust = _enrich.get("data_trust_score", 1.0)
                try:
                    _trust = float(_trust)
                    if not (0.0 <= _trust <= 1.0):
                        raise ValueError
                except (TypeError, ValueError):
                    log.debug(
                        "[CandidateTrustIntegrity] symbol=%s invalid_trust=%s — defaulting to 1.0",
                        _sym, _enrich.get("data_trust_score"),
                    )
                    _trust = 1.0

                # Patch 3 — Strategy validation
                _strategy = str(_enrich.get("strategy") or "no_setup")

                # Apply all enrichment fields
                c.update({
                    "strategy":            _strategy,
                    "lifecycle_state":     _lc,
                    "data_trust_score":    round(_trust, 3),
                    "conviction_score":    round(float(_enrich.get("conviction_score", 0.0) or 0.0), 3),
                    "invalidation_state":  str(_enrich.get("invalidation_state", "valid")),
                    "exploration_flag":    bool(_enrich.get("exploration_flag", False)),
                    "refinement_status":   str(_enrich.get("refinement_status", "raw")),
                    "momentum_state":      str(_enrich.get("momentum_state", "neutral")),
                    "breakout_state":      str(_enrich.get("breakout_state", "unknown")),
                    "candidate_origin":    str(_enrich.get("candidate_origin", "prepared_universe")),
                    "freshness_age_minutes": int(_enrich.get("freshness_age_minutes", 0) or 0),
                    "last_refresh_time":   str(_enrich.get("last_refresh_time", "")),
                    "fallback_contaminated": bool(_enrich.get("fallback_contaminated", False)),
                    "corruption_flags":    list(_enrich.get("corruption_flags", [])),
                    "simulation_status":   str(_enrich.get("simulation_status", "live")),
                    "rerank_reason":       str(_enrich.get("rerank_reason", "")),
                    "regime_bias_applied": str(_enrich.get("regime_bias_applied", "")),
                })
                enriched_count += 1

                # Drift detection
                if _old_strategy != _strategy or _old_lc != _lc:
                    drift_count += 1

            # Coverage audit
            _total = len(candidates)
            _strat_filled = sum(1 for c in candidates if c.get("strategy") and c["strategy"] != "no_setup")
            _lc_filled    = sum(1 for c in candidates if c.get("lifecycle_state") not in (None, "", "NA"))
            _trust_filled = sum(1 for c in candidates if (c.get("data_trust_score") or 0.0) > 0.0)

            log.info(
                "[CandidateMetadataCoverage] total=%d enriched=%d"
                " strategy_filled=%d lifecycle_filled=%d trust_filled=%d",
                _total, enriched_count, _strat_filled, _lc_filled, _trust_filled,
            )

            # Integrity checks (Patches 3/4/5)
            _strat_none  = sum(1 for c in candidates if not c.get("strategy") or c["strategy"] is None)
            _lc_na       = sum(1 for c in candidates if c.get("lifecycle_state") in (None, "", "NA"))
            _trust_zero  = sum(1 for c in candidates if not c.get("data_trust_score"))
            if _strat_none > 0:
                log.debug("[CandidateStrategyIntegrity] symbols_without_strategy=%d", _strat_none)
            if _lc_na > 0:
                log.debug("[CandidateLifecycleIntegrity] symbols_without_lifecycle=%d", _lc_na)
            if _trust_zero > 0:
                log.debug("[CandidateTrustIntegrity] symbols_with_zero_trust=%d", _trust_zero)

            # Atomic write
            payload["candidates"] = candidates
            payload["checksum"] = _checksum(candidates)
            payload["enrichment_last_updated"] = _utcnow_iso()
            tmp_path = STORE_FILE.with_suffix(".json.tmp")
            tmp_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
            tmp_path.replace(STORE_FILE)

            _ENRICHMENT_LAST_WRITE_TS = now_ts

            log.info(
                "[EnrichedCandidateWrite] candidates=%d enriched=%d drift_events=%d"
                " strategy_coverage=%.1f%% lifecycle_coverage=%.1f%% trust_coverage=%.1f%%",
                _total, enriched_count, drift_count,
                _strat_filled / max(1, _total) * 100.0,
                _lc_filled    / max(1, _total) * 100.0,
                _trust_filled / max(1, _total) * 100.0,
            )
            log.debug(
                "[PersistenceDriftAudit] total=%d enriched=%d drift=%d"
                " strategy=%.1f%% lifecycle=%.1f%% trust=%.1f%%",
                _total, enriched_count, drift_count,
                _strat_filled / max(1, _total) * 100.0,
                _lc_filled    / max(1, _total) * 100.0,
                _trust_filled / max(1, _total) * 100.0,
            )

            # Priority 8 (IntegrityPersistenceAudit): record successful write
            try:
                from opportunity_engine.integrity_persistence_audit import get_integrity_audit as _gia
                _ipa = _gia()
                _ipa.record_write(
                    total         = _total,
                    enriched      = enriched_count,
                    drift         = drift_count,
                    invalid_fields= invalid_count,
                    strategy_pct  = _strat_filled / max(1, _total) * 100.0,
                    lifecycle_pct = _lc_filled    / max(1, _total) * 100.0,
                    trust_pct     = _trust_filled / max(1, _total) * 100.0,
                )
                _ipa.emit_cycle_audit()
            except Exception:
                pass

            return True

        except Exception as exc:
            log.error("[CandidateStore] update_enrichment failed: %s", exc)
            try:
                from opportunity_engine.integrity_persistence_audit import get_integrity_audit as _gia
                _gia().record_error(str(exc))
            except Exception:
                pass
            return False

    # ── Context read (for overnight overlay) ─────────────────────────────────

    @classmethod
    def read_context(cls) -> Optional[Dict[str, Any]]:
        """Returns the context section of the current store file, or None."""
        try:
            if not STORE_FILE.exists():
                return None
            payload = json.loads(STORE_FILE.read_text(encoding="utf-8"))
            return payload.get("context")
        except Exception:
            return None

    # ── Freshness check ───────────────────────────────────────────────────────

    @classmethod
    def is_fresh(cls) -> bool:
        """True if a valid, non-stale candidate file exists."""
        try:
            if not STORE_FILE.exists():
                return False
            payload = json.loads(STORE_FILE.read_text(encoding="utf-8"))
            age = _age_hours(payload.get("prepared_at", ""))
            return age is not None and age <= MAX_AGE_HOURS
        except Exception:
            return False

    # ── Scanner concentration memory ─────────────────────────────────────────

    @classmethod
    def record_selected_symbols(cls, symbols: List[str], date_str: Optional[str] = None) -> None:
        """
        Record which symbols were selected today for concentration-penalty tracking.
        Prunes history older than SCANNER_MEMORY_RETENTION_DAYS.
        """
        try:
            from config import SCANNER_MEMORY_RETENTION_DAYS
            retention_days = SCANNER_MEMORY_RETENTION_DAYS
        except ImportError:
            retention_days = 30

        today = date_str or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        mem = cls._load_memory_raw()
        mem[today] = list(symbols)

        # Prune old date-keyed entries (leave scalar metadata keys untouched)
        cutoff = _days_ago_str(retention_days)
        pruned = {
            k: v for k, v in mem.items()
            if not (len(k) == 10 and k[4] == "-" and k < cutoff)  # date keys only
        }
        cls._save_memory_raw(pruned)

    @classmethod
    def get_consecutive_selection_counts(cls) -> Dict[str, int]:
        """
        Returns {symbol: consecutive_days_in_prepared_list} for active concentration tracking.
        Used by market_scanner to apply diversification penalties.
        """
        mem = cls._load_memory_raw()
        # Extract only date-keyed entries (YYYY-MM-DD keys containing lists)
        symbol_history: Dict[str, list] = {
            k: v for k, v in mem.items()
            if len(k) == 10 and k[4] == "-" and isinstance(v, list)
        }
        if not symbol_history:
            return {}

        counts: Dict[str, int] = {}
        # Walk forward from most recent date and count consecutive appearances
        all_symbols: set = set()
        for date_syms in symbol_history.values():
            all_symbols.update(date_syms)

        sorted_dates = sorted(symbol_history.keys(), reverse=True)
        for sym in all_symbols:
            streak = 0
            for d in sorted_dates:
                if sym in symbol_history.get(d, []):
                    streak += 1
                else:
                    break
            if streak > 0:
                counts[sym] = streak

        return counts

    # ── Stale-fallback escalation tracking — Patch 5 ─────────────────────────

    @classmethod
    def record_stale_fallback(cls) -> int:
        """
        Patch 5 — Record that this scan cycle used static fallback (prepared
        universe was unavailable, stale, or corrupted).
        Increments the consecutive_fallback_sessions counter in scanner_memory.json.
        Returns the new consecutive count.
        Telemetry only — callers decide whether to escalate.
        """
        mem = cls._load_memory_raw()
        count = int(mem.get("consecutive_fallback_sessions", 0)) + 1
        mem["consecutive_fallback_sessions"] = count
        mem["last_fallback_at"] = _utcnow_iso()
        cls._save_memory_raw(mem)
        return count

    @classmethod
    def record_prepared_success(cls) -> None:
        """
        Patch 5 — Record that this scan cycle successfully used the prepared
        universe.  Resets the consecutive_fallback_sessions counter to 0.
        """
        mem = cls._load_memory_raw()
        mem["consecutive_fallback_sessions"] = 0
        mem["last_prepared_success_at"] = _utcnow_iso()
        cls._save_memory_raw(mem)

    @classmethod
    def backfill_baseline_enrichment(cls) -> int:
        """
        Apply baseline enrichment to ALL candidates already in the store.

        One-shot backfill for candidates written before baseline enrichment was
        part of write().  Only fills missing / empty fields — never overwrites.

        Returns the number of candidates patched, 0 if nothing to do or on error.
        Emits: [UniversalEnrichmentPass], [BaselineEnrichment], [CandidateMetadataCoverage]
        """
        try:
            if not STORE_FILE.exists():
                return 0

            payload = json.loads(STORE_FILE.read_text(encoding="utf-8"))
            candidates: List[Dict[str, Any]] = payload.get("candidates", [])
            if not candidates:
                return 0

            # Only backfill candidates missing strategy or lifecycle_state
            _to_fill = [
                c for c in candidates
                if c.get("strategy") is None
                or c.get("lifecycle_state") in (None, "", "NA")
            ]
            if not _to_fill:
                return 0

            for c in _to_fill:
                _apply_baseline_enrichment(c)

            backfilled = len(_to_fill)

            # Coverage audit after backfill
            _total    = len(candidates)
            _strat_ok = sum(1 for c in candidates if c.get("strategy"))
            _lc_ok    = sum(1 for c in candidates
                            if c.get("lifecycle_state") not in (None, "", "NA"))
            _trust_ok = sum(1 for c in candidates
                            if (c.get("data_trust_score") or 0.0) > 0.0)

            # Atomic write
            payload["candidates"]              = candidates
            payload["checksum"]                = _checksum(candidates)
            payload["enrichment_last_updated"] = _utcnow_iso()
            tmp_path = STORE_FILE.with_suffix(".json.tmp")
            tmp_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
            tmp_path.replace(STORE_FILE)

            log.info(
                "[UniversalEnrichmentPass] Backfilled %d/%d candidates."
                " strategy=%.0f%% lifecycle=%.0f%% trust=%.0f%%",
                backfilled, _total,
                _strat_ok / max(1, _total) * 100,
                _lc_ok    / max(1, _total) * 100,
                _trust_ok / max(1, _total) * 100,
            )
            log.info(
                "[CandidateMetadataCoverage] total=%d strategy_filled=%d"
                " lifecycle_filled=%d trust_filled=%d"
                " enrichment_coverage_pct=%.0f%%",
                _total, _strat_ok, _lc_ok, _trust_ok,
                min(_strat_ok, _lc_ok, _trust_ok) / max(1, _total) * 100,
            )
            return backfilled

        except Exception as exc:
            log.error("[CandidateStore] backfill_baseline_enrichment failed: %s", exc)
            return 0

    @classmethod
    def get_consecutive_fallback_count(cls) -> int:
        """
        Patch 5 — Return current consecutive static-fallback session count.
        Returns 0 if memory file is absent or unreadable.
        """
        mem = cls._load_memory_raw()
        return int(mem.get("consecutive_fallback_sessions", 0))

    # ── Memory file raw I/O helpers ───────────────────────────────────────────

    @classmethod
    def _load_memory_raw(cls) -> Dict[str, Any]:
        """Load scanner_memory.json as a raw dict (no type assumptions)."""
        if not MEMORY_FILE.exists():
            return {}
        try:
            return json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}

    @classmethod
    def _save_memory_raw(cls, mem: Dict[str, Any]) -> None:
        """Persist the raw memory dict atomically."""
        try:
            MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
            tmp = MEMORY_FILE.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(mem, indent=2, default=str), encoding="utf-8")
            tmp.replace(MEMORY_FILE)
        except Exception as exc:
            log.debug("[CandidateStore] Memory save failed: %s", exc)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _age_hours(iso_str: str) -> Optional[float]:
    """Return hours since the given UTC ISO-8601 timestamp, or None if unparseable."""
    if not iso_str:
        return None
    try:
        # Handle both 'Z' suffix and '+00:00'
        iso_str = iso_str.replace("Z", "+00:00")
        ts = datetime.fromisoformat(iso_str)
        now = datetime.now(timezone.utc)
        return (now - ts).total_seconds() / 3600.0
    except Exception:
        return None


def _checksum(candidates: List[Dict[str, Any]]) -> str:
    """SHA-256 of the JSON-serialised candidates list (symbols + levels only)."""
    key_data = [
        {"symbol": c.get("symbol"), "resistance": c.get("resistance"),
         "support": c.get("support"), "rsi": c.get("rsi")}
        for c in candidates
    ]
    raw = json.dumps(key_data, sort_keys=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def _is_valid_candidate(c: Dict[str, Any]) -> bool:
    """True if all required fields are present and non-zero."""
    for field in _REQUIRED_FIELDS:
        val = c.get(field)
        if val is None:
            return False
        if isinstance(val, (int, float)) and val == 0:
            return False
    return True


def _days_ago_str(n: int) -> str:
    from datetime import timedelta
    d = datetime.now(timezone.utc) - timedelta(days=n)
    return d.strftime("%Y-%m-%d")


# ── V2: Candidate lifecycle state machine ────────────────────────────────────

def compute_lifecycle_state(
    candidate: Dict[str, Any],
    live_ltp: float = 0.0,
    live_rsi: Optional[float] = None,
    sector_leaders: Optional[List[str]] = None,
    now_utc: Optional[datetime] = None,
) -> str:
    """
    Derive the lifecycle state of a prepared candidate from first principles.

    Pure function — no I/O, no side effects, never raises.
    Priority order: EXPIRED → INVALIDATED → REACTIVATED → WEAKENING → FRESH/ACTIVE

    Args:
        candidate:      candidate dict from CandidateStore.read()
        live_ltp:       current last traded price (0 = unavailable)
        live_rsi:       current RSI(14) from _RSI_CACHE (None = use stored)
        sector_leaders: current sector leaders from MarketSnapshot
        now_utc:        current UTC time (defaults to datetime.now(utc))

    Returns:
        One of the LIFECYCLE_* constants.
    """
    try:
        if now_utc is None:
            now_utc = datetime.now(timezone.utc)

        # ── 1. EXPIRED: TTL elapsed and not revived ─────────────────────────────
        vu = candidate.get("valid_until_utc")
        if vu:
            try:
                expiry = datetime.fromisoformat(vu.replace("Z", "+00:00"))
                if now_utc > expiry:
                    return LIFECYCLE_EXPIRED
            except Exception:
                pass

        # ── 2. INVALIDATED: structural price-action failure ──────────────────────
        sup      = float(candidate.get("support",    0) or 0)
        res      = float(candidate.get("resistance", 0) or 0)
        base_ltp = float(candidate.get("base_ltp",   0) or 0)
        atr      = float(candidate.get("atr14",      0) or 0)

        if atr <= 0 and res > sup > 0:
            atr = (res - sup) * 0.40
        if atr <= 0 and live_ltp > 0:
            atr = live_ltp * 0.020

        if live_ltp > 0 and atr > 0:
            # Support breakdown: price fell below support by ≥1 ATR
            if sup > 0 and live_ltp < sup - atr:
                return LIFECYCLE_INVALIDATED
            # Failed breakout: base_ltp was above resistance, now price returned below
            if base_ltp > 0 and res > 0 and base_ltp > res * 0.995 and live_ltp < res * 0.990:
                return LIFECYCLE_INVALIDATED
            # ATR shock: price drifted >3× ATR from base_ltp (runaway, original setup stale)
            if base_ltp > 0 and abs(live_ltp - base_ltp) > 3.0 * atr:
                return LIFECYCLE_INVALIDATED

        # ── 3. Deterioration signal count ───────────────────────────────────────
        rsi       = live_rsi if live_rsi is not None else float(candidate.get("rsi", 50) or 50)
        vol_ratio = float(candidate.get("volume_ratio", 1.0) or 1.0)
        score     = float(candidate.get("score",     0.5) or 0.5)

        weak = 0
        if rsi > 72 or rsi < 28:
            weak += 1
        if vol_ratio < 0.40:
            weak += 1
        if score < 0.35:
            weak += 1
        if sector_leaders:
            sector = (candidate.get("sector") or "").lower()
            leaders_lower = [s.lower() for s in sector_leaders]
            if sector and not any(ts in sector or sector in ts for ts in leaders_lower):
                weak += 1

        # ── 4. REACTIVATED: TTL was extended by refresh_expired() ────────────────
        if candidate.get("lifecycle_extended_at") or candidate.get("base_ltp_refreshed"):
            return LIFECYCLE_WEAKENING if weak >= 2 else LIFECYCLE_REACTIVATED

        if weak >= 2:
            return LIFECYCLE_WEAKENING

        # ── 5. Age-based: FRESH < 6h, ACTIVE otherwise ───────────────────────────
        pa = candidate.get("prepared_at") or candidate.get("score_updated_at")
        if pa:
            try:
                ts = datetime.fromisoformat(pa.replace("Z", "+00:00"))
                if (now_utc - ts).total_seconds() < 21600:   # 6 hours
                    return LIFECYCLE_FRESH
            except Exception:
                pass

        return LIFECYCLE_ACTIVE

    except Exception:
        return LIFECYCLE_ACTIVE   # safe default on any failure
