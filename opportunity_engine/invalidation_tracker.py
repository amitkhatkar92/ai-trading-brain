"""
InvalidationTracker — Phase A / B / C forensic persistence layer
================================================================
Persists invalidation events across scan cycles, intraday refreshes,
and container restarts.  Classifies feed source before recording.
Detects repeated-fire patterns.

Emits (structured log lines — grep-able):
  [InvalidationPersistence]  — new record created or existing count updated
  [InvalidationRecovery]     — symbol previously invalidated now passes checks
  [InvalidationRepeatFire]   — same symbol fires again within the current session
  [InvalidationFeedSource]   — feed-source classification for every invalidation
  [RepeatedInvalidation]     — recurrence analysis: genuine | cached_price | stale_feed

Design constraints
──────────────────
* DO NOT modify thresholds.
* DO NOT modify strategy logic.
* Observe only — never suppress, gate, or change the invalidation decision.
* Thread-safe: record_invalidation() is called from the scan thread;
  check_recovery() from the same scan thread.  Both write to self._state which
  is protected by self._write_lock.
* Atomic disk writes: .tmp → .replace() to survive power loss / SIGKILL.
"""

from __future__ import annotations

import json
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from utils import get_logger

log = get_logger(__name__)

# ── Paths ─────────────────────────────────────────────────────────────────────
_STATE_FILE = Path(__file__).parent.parent / "data" / "invalidation_state.json"
# ── Feed-Unreliable Suppression constants ──────────────────────────────────────────
# A symbol is considered feed-unreliable when it has accumulated at least
# FEED_SUPPRESS_THRESHOLD feed-induced invalidations AND zero genuine ones.
# Suppression lasts FEED_SUPPRESS_SESSIONS trading sessions, then resets.
FEED_SUPPRESS_THRESHOLD: int = 10   # feed_induced_count must reach this
FEED_SUPPRESS_SESSIONS:  int = 5    # sessions to suppress after trigger
# Minimum seconds between disk saves (rate-limiter to avoid excessive I/O).
# Forced saves (e.g. on first record) bypass this limit.
_SAVE_INTERVAL_S: float = 30.0

# ── Feed-source classification constants ──────────────────────────────────────
FEED_LIVE      = "LIVE"       # Dhan API returned a fresh quote
FEED_FALLBACK  = "FALLBACK"   # Yahoo / NSE fallback used
FEED_SYNTHETIC = "SYNTHETIC"  # yfinance ~1000 sim-artifact detected
FEED_STALE     = "STALE"      # no live data — fell back to stored base_ltp

# ── Sim-artifact detection window ─────────────────────────────────────────────
# yfinance returns live_ltp ≈ 995–1005 for ALL symbols when its cache is
# populated with a bad "~1000" batch.  Any stock whose base_ltp is outside
# the [900, 1100] band (i.e. NOT a genuinely ≈₹1000 stock) is a false positive
# when its live_ltp falls in this window from a non-DHAN source.
_SIM_LO: float   = 975.0
_SIM_HI: float   = 1025.0
_SIM_BASE_BAND_LO: float = 900.0
_SIM_BASE_BAND_HI: float = 1100.0


# ═════════════════════════════════════════════════════════════════════════════
class InvalidationTracker:
    """
    Singleton: persists invalidation metadata across scan cycles and restarts.

    Phase A  — tracks first_invalidated_at / last_invalidated_at /
               invalidation_count / invalidation_reason per symbol.
    Phase B  — classifies the price-feed source (LIVE / FALLBACK / SYNTHETIC /
               STALE) before recording, and buckets counts into
               genuine_count vs feed_induced_count.
    Phase C  — detects recurrence within the current session and determines
               whether repeated fires are genuine, cached_price, or stale_feed.
    """

    _instance: Optional["InvalidationTracker"] = None
    _class_lock = threading.Lock()

    def __new__(cls) -> "InvalidationTracker":
        with cls._class_lock:
            if cls._instance is None:
                obj = super().__new__(cls)
                # Persistent state (survives container restarts via disk)
                obj._state: Dict[str, Dict[str, Any]] = {}
                # In-memory session state (resets on container restart — intentional)
                obj._session_fire:    Dict[str, Dict[str, int]] = {}
                obj._session_ltps:    Dict[str, List[float]]    = {}
                obj._session_recovered: set                      = set()
                # I/O helpers
                obj._write_lock    = threading.Lock()
                obj._io_lock       = threading.Lock()
                obj._last_save_ts: float = 0.0
                # Feed-unreliable suppression: symbol → sessions_remaining
                # (in-memory; resets on container restart — intentional; conservative)
                obj._feed_suppressed: Dict[str, int] = {}
                obj._load()
                cls._instance = obj
        return cls._instance

    # ── Persistence ───────────────────────────────────────────────────────────

    def _load(self) -> None:
        """Load persisted state from disk (called once on first instantiation)."""
        try:
            if _STATE_FILE.exists():
                raw = json.loads(_STATE_FILE.read_text(encoding="utf-8"))
                if isinstance(raw, dict):
                    self._state = raw
                    log.info(
                        "[InvalidationRecovery] State loaded from disk: %d symbols tracked"
                        " (genuine=%d  feed_induced=%d).",
                        len(self._state),
                        sum(v.get("genuine_count", 0) for v in self._state.values()),
                        sum(v.get("feed_induced_count", 0) for v in self._state.values()),
                    )
        except Exception as exc:
            log.warning("[InvalidationTracker] Failed to load state file: %s — starting fresh.", exc)
            self._state = {}

    def _save(self, force: bool = False) -> None:
        """Atomic write to disk.  Rate-limited unless force=True."""
        now = time.monotonic()
        if not force and (now - self._last_save_ts) < _SAVE_INTERVAL_S:
            return
        try:
            with self._io_lock:
                tmp = _STATE_FILE.with_suffix(".tmp")
                tmp.write_text(
                    json.dumps(self._state, indent=2, default=str),
                    encoding="utf-8",
                )
                tmp.replace(_STATE_FILE)
                self._last_save_ts = now
        except Exception as exc:
            log.warning("[InvalidationTracker] Disk save failed: %s", exc)

    # ── Feed-source classification (Phase B) ─────────────────────────────────

    @staticmethod
    def classify_feed_source(
        symbol: str,
        live_ltp: float,
        base_ltp: float,
        raw_source: str,
    ) -> str:
        """
        Classify the price source that produced live_ltp.

        Priority order:
        1. STALE      — live_ltp == base_ltp (cache miss; stored value used)
        2. SYNTHETIC  — live_ltp ≈ 1000 AND base_ltp outside the ≈1000 band
                        AND source is not DHAN (yfinance sim artifact)
        3. LIVE       — raw_source is "DHAN" or "LIVE"
        4. FALLBACK   — everything else (YAHOO, NSE, unknown)
        """
        # STALE: no live price available; fell back to the stored base_ltp
        if base_ltp > 0 and live_ltp == base_ltp:
            return FEED_STALE

        # SYNTHETIC: yfinance ~1000 contamination
        # A genuinely ≈₹1000 stock has base_ltp also near 1000; exclude those.
        if (
            _SIM_LO <= live_ltp <= _SIM_HI
            and not (_SIM_BASE_BAND_LO <= base_ltp <= _SIM_BASE_BAND_HI)
            and raw_source.upper() not in ("DHAN", "LIVE")
        ):
            return FEED_SYNTHETIC

        # LIVE: Dhan API returned this price
        if raw_source.upper() in ("DHAN", "LIVE"):
            return FEED_LIVE

        # FALLBACK: Yahoo, NSE, or any other non-Dhan source
        return FEED_FALLBACK

    # ── Core recording (Phase A + B + C) ────────────────────────────────────

    def record_invalidation(
        self,
        symbol: str,
        reason: str,
        live_ltp: float,
        base_ltp: float,
        raw_source: str,
    ) -> None:
        """
        Record a fired invalidation event with full provenance.

        Called from _prepared_watchlist() for every symbol that fires
        _check_breakout_invalidation().  Never raises — all errors are logged.
        """
        try:
            now_iso      = datetime.now(timezone.utc).isoformat()
            feed_class   = self.classify_feed_source(symbol, live_ltp, base_ltp, raw_source)
            is_genuine   = (feed_class == FEED_LIVE)

            # ── Phase B — emit feed-source classification ─────────────────────
            log.info(
                "[InvalidationFeedSource]  symbol=%-16s  classification=%-10s"
                "  raw_source=%-6s  live_ltp=%8.2f  base_ltp=%8.2f"
                "  ratio=%.3f  is_genuine=%s",
                symbol, feed_class,
                raw_source or "none",
                live_ltp, base_ltp,
                (live_ltp / base_ltp) if base_ltp > 0 else 0.0,
                is_genuine,
            )

            # ── Phase C — recurrence detection ───────────────────────────────
            with self._write_lock:
                sym_fires = self._session_fire.setdefault(symbol, {})
                prior_fire_count = sym_fires.get(reason, 0)
                sym_fires[reason] = prior_fire_count + 1

                sym_ltps = self._session_ltps.setdefault(symbol, [])
                recurrence_type: str = ""

                if prior_fire_count > 0:
                    # Classify WHY it's repeating
                    if sym_ltps and sym_ltps[-1] == live_ltp:
                        recurrence_type = "cached_price"
                    elif feed_class in (FEED_SYNTHETIC, FEED_STALE):
                        recurrence_type = "stale_feed"
                    else:
                        recurrence_type = "genuine"

                    log.warning(
                        "[InvalidationRepeatFire]  symbol=%-16s  reason=%s"
                        "  session_count=%d",
                        symbol, reason, prior_fire_count + 1,
                    )
                    log.warning(
                        "[RepeatedInvalidation]  symbol=%-16s  recurrence_type=%-14s"
                        "  live_ltp=%8.2f  feed=%-10s  session_count=%d",
                        symbol, recurrence_type,
                        live_ltp, feed_class, prior_fire_count + 1,
                    )

                sym_ltps.append(live_ltp)

                # ── Phase A — update persistent state ────────────────────────
                existing = self._state.get(symbol)
                if existing is None:
                    self._state[symbol] = {
                        "first_invalidated_at":  now_iso,
                        "last_invalidated_at":   now_iso,
                        "invalidation_reason":   reason,
                        "invalidation_count":    1,
                        "last_live_ltp":         live_ltp,
                        "last_base_ltp":         base_ltp,
                        "last_feed_source":      raw_source or "",
                        "feed_classification":   feed_class,
                        "genuine_count":         1 if is_genuine else 0,
                        "feed_induced_count":    0 if is_genuine else 1,
                        "recurrence_type":       recurrence_type,
                    }
                    log.info(
                        "[InvalidationPersistence]  NEW  symbol=%-16s"
                        "  reason=%s  feed=%-10s"
                        "  genuine_cumulative=%d  feed_induced_cumulative=%d",
                        symbol, reason, feed_class,
                        1 if is_genuine else 0,
                        0 if is_genuine else 1,
                    )
                else:
                    existing["last_invalidated_at"]  = now_iso
                    existing["invalidation_reason"]  = reason
                    existing["invalidation_count"]  += 1
                    existing["last_live_ltp"]        = live_ltp
                    existing["last_base_ltp"]        = base_ltp
                    existing["last_feed_source"]     = raw_source or ""
                    existing["feed_classification"]  = feed_class
                    if is_genuine:
                        existing["genuine_count"] = existing.get("genuine_count", 0) + 1
                    else:
                        existing["feed_induced_count"] = existing.get("feed_induced_count", 0) + 1
                    if recurrence_type:
                        existing["recurrence_type"] = recurrence_type
                    log.info(
                        "[InvalidationPersistence]  UPDATE  symbol=%-16s"
                        "  reason=%s  feed=%-10s"
                        "  total=%d  genuine=%d  feed_induced=%d",
                        symbol, reason, feed_class,
                        existing["invalidation_count"],
                        existing.get("genuine_count", 0),
                        existing.get("feed_induced_count", 0),
                    )

            # Save to disk (rate-limited; first-ever record is forced)
            force_save = (self._last_save_ts == 0.0)
            self._save(force=force_save)

        except Exception as exc:
            log.warning("[InvalidationTracker] record_invalidation failed for %s: %s", symbol, exc)

    # ── Recovery check (Phase A) ──────────────────────────────────────────────

    def check_recovery(self, symbol: str) -> None:
        """
        Called when a symbol PASSES all invalidation checks this cycle.

        Emits [InvalidationRecovery] once per session if the symbol has a prior
        invalidation record (either from this session or a previous one loaded
        from disk).  Only emits once per session per symbol to avoid log flood.
        """
        try:
            if symbol in self._session_recovered:
                return   # already emitted this session

            prior = self._state.get(symbol)
            if prior is None or prior.get("invalidation_count", 0) == 0:
                return   # no prior record

            self._session_recovered.add(symbol)
            log.info(
                "[InvalidationRecovery]  symbol=%-16s  prior_reason=%s"
                "  prior_count=%d  first_invalidated=%s  last_invalidated=%s"
                "  genuine=%d  feed_induced=%d  status=PASSING",
                symbol,
                prior.get("invalidation_reason", ""),
                prior.get("invalidation_count", 0),
                prior.get("first_invalidated_at", ""),
                prior.get("last_invalidated_at", ""),
                prior.get("genuine_count", 0),
                prior.get("feed_induced_count", 0),
            )
        except Exception as exc:
            log.warning("[InvalidationTracker] check_recovery failed for %s: %s", symbol, exc)

    # ── Feed-Unreliable Suppression (Phase D) ────────────────────────────────

    def is_feed_suppressed(self, symbol: str) -> bool:
        """
        Return True if the symbol is currently suppressed due to accumulated
        feed-induced invalidations with zero genuine invalidations.

        Trigger:  feed_induced_count >= FEED_SUPPRESS_THRESHOLD AND genuine_count == 0
        Duration: FEED_SUPPRESS_SESSIONS sessions (decremented by tick_session_end)

        Caller decides what to do with the result — this method never alters
        the invalidation decision or pipeline routing itself.
        """
        with self._write_lock:
            # Already actively suppressed from a prior trigger
            if self._feed_suppressed.get(symbol, 0) > 0:
                return True

            # Check persistent record for trigger condition
            rec = self._state.get(symbol)
            if rec is None:
                return False
            fi = rec.get("feed_induced_count", 0)
            g  = rec.get("genuine_count", 0)
            if fi >= FEED_SUPPRESS_THRESHOLD and g == 0:
                # Trigger: enter suppression
                self._feed_suppressed[symbol] = FEED_SUPPRESS_SESSIONS
                log.info(
                    "[FeedUnreliableSuppression] symbol=%-16s  source=%-10s"
                    "  feed_induced_count=%d  genuine_count=0"
                    "  suppression_duration=%d sessions",
                    symbol,
                    rec.get("last_feed_source", "unknown"),
                    fi,
                    FEED_SUPPRESS_SESSIONS,
                )
                return True

        return False

    def tick_session_end(self) -> None:
        """
        Decrement suppression counters by one session.
        Call once per EOD from emit_session_summary().
        Symbols whose counter reaches 0 are automatically re-evaluated.
        """
        with self._write_lock:
            expired = [sym for sym, n in self._feed_suppressed.items() if n <= 1]
            for sym in expired:
                del self._feed_suppressed[sym]
                log.info(
                    "[FeedUnreliableSuppression] symbol=%-16s"
                    "  suppression_expired — will re-evaluate next session.",
                    sym,
                )
            for sym in list(self._feed_suppressed):
                if sym not in expired:
                    self._feed_suppressed[sym] -= 1

    # ── Summary ──────────────────────────────────────────────────────────────

    def get_summary(self) -> Dict[str, Any]:
        """Return aggregate counts (for telemetry / dashboard queries)."""
        with self._write_lock:
            total          = len(self._state)
            genuine        = sum(v.get("genuine_count", 0) for v in self._state.values())
            feed_induced   = sum(v.get("feed_induced_count", 0) for v in self._state.values())
            session_fires = sum(
                count
                for v in self._session_fire.values()
                for k, count in v.items()
                if not k.startswith("_") and isinstance(count, int)
            )
        return {
            "unique_symbols_ever_invalidated":  total,
            "total_genuine_invalidations":      genuine,
            "total_feed_induced_invalidations": feed_induced,
            "session_fire_count":               session_fires,
        }

    # ── EOD session summary (Phase A/B/C combined report) ────────────────────

    def emit_session_summary(self) -> None:
        """
        EOD effectiveness summary — call once from _do_eod_learning().

        Cross-references the persistent state (invalidation_state.json) with
        the current candidate store (daily_candidates.json) to classify each
        symbol's outcome.  Emits structured [InvalidationEffectivenessReport]
        log lines covering all 5 requested dimensions:

          1. Genuine invalidations (feed=LIVE) with recovery status
          2. Feed-induced invalidations (SYNTHETIC / FALLBACK / STALE)
          3. Top recurring symbols (all-time invalidation_count)
          4. Recovery rate (recovered / still_invalid / removed / active)
          5. Session summary counts
        """
        try:
            # ── Cross-reference with current store ──────────────────────────
            store_lc: Dict[str, str] = {}   # symbol → lifecycle_state
            try:
                store_file = _STATE_FILE.parent / "daily_candidates.json"
                if store_file.exists():
                    raw = json.loads(store_file.read_text(encoding="utf-8"))
                    if isinstance(raw, list):
                        for c in raw:
                            if isinstance(c, dict) and c.get("symbol"):
                                store_lc[c["symbol"]] = c.get("lifecycle_state", "ACTIVE")
            except Exception as _se:
                log.debug("[InvalidationEffectivenessReport] store read failed: %s", _se)

            with self._write_lock:
                state     = dict(self._state)
                recovered = set(self._session_recovered)

            # ── Classify every symbol ────────────────────────────────────────
            genuine_list:      List[Dict] = []
            feed_induced_list: List[Dict] = []
            ever_invalidated   = set(state.keys())

            for sym, rec in state.items():
                g  = rec.get("genuine_count", 0)
                fi = rec.get("feed_induced_count", 0)
                lc = store_lc.get(sym)
                if lc is None:
                    outcome = "REMOVED"
                elif lc == "INVALIDATED":
                    outcome = "STILL_INVALID"
                elif sym in recovered:
                    outcome = "RECOVERED"
                else:
                    outcome = "ACTIVE"

                if g > 0:
                    genuine_list.append({
                        "symbol":        sym,
                        "reason":        rec.get("invalidation_reason", ""),
                        "feed":          rec.get("feed_classification", ""),
                        "genuine_count": g,
                        "total_count":   rec.get("invalidation_count", 0),
                        "first_at":      rec.get("first_invalidated_at", "")[:19],
                        "last_at":       rec.get("last_invalidated_at", "")[:19],
                        "outcome":       outcome,
                    })
                if fi > 0:
                    feed_induced_list.append({
                        "symbol":            sym,
                        "feed":              rec.get("feed_classification", ""),
                        "source":            rec.get("last_feed_source", ""),
                        "feed_induced_count": fi,
                        "recurrence_type":   rec.get("recurrence_type", ""),
                        "first_at":          rec.get("first_invalidated_at", "")[:19],
                    })

            genuine_list.sort(key=lambda x: -x["genuine_count"])
            feed_induced_list.sort(key=lambda x: -x["feed_induced_count"])
            top_recurring = sorted(state.items(), key=lambda x: -x[1].get("invalidation_count", 0))

            # Recovery rate buckets
            n_recovered     = len({s for s in ever_invalidated if s in recovered})
            n_still_invalid = len({s for s in ever_invalidated if store_lc.get(s) == "INVALIDATED"})
            n_removed       = len({s for s in ever_invalidated if s not in store_lc})
            n_active        = len({
                s for s in ever_invalidated
                if s in store_lc and store_lc[s] not in ("INVALIDATED", "EXPIRED")
            })
            total_sym       = max(len(ever_invalidated), 1)
            total_events    = sum(v.get("invalidation_count", 0) for v in state.values())
            total_genuine   = sum(v.get("genuine_count", 0) for v in state.values())
            total_fi        = sum(v.get("feed_induced_count", 0) for v in state.values())

            # ── Section 0: headline ─────────────────────────────────────────
            log.info(
                "[InvalidationEffectivenessReport] ═══ EOD SUMMARY  %s ═══"
                "  symbols_ever_invalidated=%d"
                "  total_events=%d  genuine=%d  feed_induced=%d"
                "  session_recovered=%d",
                datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                len(ever_invalidated), total_events,
                total_genuine, total_fi, n_recovered,
            )

            # ── Section 1: Genuine ──────────────────────────────────────────
            log.info(
                "[InvalidationEffectivenessReport] ─── [1/5] GENUINE INVALIDATIONS: %d symbol(s) ───",
                len(genuine_list),
            )
            if genuine_list:
                for g in genuine_list:
                    log.info(
                        "[InvalidationEffectivenessReport]"
                        "  GENUINE  %-16s  reason=%-60s"
                        "  feed=%-5s  fires=%d  outcome=%-12s"
                        "  first=%s  last=%s",
                        g["symbol"], g["reason"][:60],
                        g["feed"], g["genuine_count"], g["outcome"],
                        g["first_at"], g["last_at"],
                    )
            else:
                log.info("[InvalidationEffectivenessReport]  (none this session — all LIVE-price checks passed)")

            # ── Section 2: Feed-induced ─────────────────────────────────────
            log.info(
                "[InvalidationEffectivenessReport] ─── [2/5] FEED-INDUCED INVALIDATIONS: %d symbol(s) ───",
                len(feed_induced_list),
            )
            if feed_induced_list:
                for fi in feed_induced_list:
                    log.info(
                        "[InvalidationEffectivenessReport]"
                        "  FEED_INDUCED  %-16s  class=%-10s  source=%-6s"
                        "  count=%d  recurrence=%s  first=%s",
                        fi["symbol"], fi["feed"], fi["source"],
                        fi["feed_induced_count"], fi["recurrence_type"], fi["first_at"],
                    )
            else:
                log.info("[InvalidationEffectivenessReport]  (none — feed quality was clean this session)")

            # ── Section 3: Top recurring ────────────────────────────────────
            log.info("[InvalidationEffectivenessReport] ─── [3/5] TOP RECURRING SYMBOLS (all-time, top 10) ───")
            for sym, rec in top_recurring[:10]:
                log.info(
                    "[InvalidationEffectivenessReport]"
                    "  RECURRING  %-16s  total=%3d  genuine=%3d  feed_induced=%3d"
                    "  recurrence_type=%-14s  last_reason=%s",
                    sym,
                    rec.get("invalidation_count", 0),
                    rec.get("genuine_count", 0),
                    rec.get("feed_induced_count", 0),
                    rec.get("recurrence_type", ""),
                    rec.get("invalidation_reason", "")[:50],
                )

            # ── Section 4: Recovery rate ────────────────────────────────────
            log.info(
                "[InvalidationEffectivenessReport] ─── [4/5] RECOVERY RATE ───"
                "  recovered=%d(%.0f%%)  still_invalid=%d(%.0f%%)"
                "  removed=%d(%.0f%%)  active=%d(%.0f%%)",
                n_recovered,     100 * n_recovered     / total_sym,
                n_still_invalid, 100 * n_still_invalid / total_sym,
                n_removed,       100 * n_removed       / total_sym,
                n_active,        100 * n_active         / total_sym,
            )
            for sym in sorted(s for s in ever_invalidated if s in recovered):
                log.info("[InvalidationEffectivenessReport]  RECOVERED     %s", sym)
            for sym in sorted(s for s in ever_invalidated if store_lc.get(s) == "INVALIDATED"):
                log.info("[InvalidationEffectivenessReport]  STILL_INVALID %s  reason=%s",
                         sym, state.get(sym, {}).get("invalidation_reason", "")[:50])
            for sym in sorted(s for s in ever_invalidated if s not in store_lc):
                log.info("[InvalidationEffectivenessReport]  REMOVED       %s", sym)

            # ── Section 5: Counts summary ───────────────────────────────────
            log.info(
                "[InvalidationEffectivenessReport] ─── [5/5] SESSION COUNTS ───"
                "  genuine_invalidations=%d"
                "  feed_induced_invalidations=%d"
                "  recovered_candidates=%d"
                "  permanently_removed_candidates=%d"
                "  repeated_invalidations=%d",
                total_genuine,
                total_fi,
                n_recovered,
                n_removed,
                sum(
                    v.get("invalidation_count", 0) - 1
                    for v in state.values()
                    if v.get("invalidation_count", 0) > 1
                ),
            )
            log.info("[InvalidationEffectivenessReport] ═══ END EOD SUMMARY ═══")

            # Phase D: decrement session counters for all suppressed symbols
            self.tick_session_end()

        except Exception as exc:
            log.warning("[InvalidationEffectivenessReport] emit_session_summary failed: %s", exc)


# ── Module-level singleton accessor ──────────────────────────────────────────

_tracker_instance:  Optional[InvalidationTracker] = None
_tracker_init_lock: threading.Lock                = threading.Lock()


def get_invalidation_tracker() -> InvalidationTracker:
    """Return the process-wide InvalidationTracker singleton."""
    global _tracker_instance
    if _tracker_instance is None:
        with _tracker_init_lock:
            if _tracker_instance is None:
                _tracker_instance = InvalidationTracker()
    return _tracker_instance
