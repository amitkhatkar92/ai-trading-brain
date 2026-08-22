"""
AngelOne Readiness Auditor — Dhan Exit Preparation
===================================================
Tracks 7 phases of AngelOne vs Dhan comparison.
Pure observability — no feed priority changes, no execution changes.

Phase 1 — FeedComparisonAudit   : per-request source selection + latency
Phase 2 — LTPParityAudit        : shadow LTP comparison (background thread)
Phase 3 — OptionsChainReadiness : options chain quality per source per symbol
Phase 4 — CandidateParityAudit  : candidate score sensitivity to LTP source
Phase 5 — SignalParityAudit     : signal parity (driven by Phase 2 deltas)
Phase 6 — FeedReliabilityAudit  : failure forensics per source
Phase 7 — AngelOneReadinessReport: EOD migration readiness score
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from utils import get_logger

log = get_logger(__name__)

# ── Singleton ────────────────────────────────────────────────────────────────
_AUDITOR: Optional["AngelOneReadinessAuditor"] = None
_LOCK = threading.Lock()


def get_readiness_auditor() -> "AngelOneReadinessAuditor":
    global _AUDITOR
    if _AUDITOR is None:
        with _LOCK:
            if _AUDITOR is None:
                _AUDITOR = AngelOneReadinessAuditor()
    return _AUDITOR


# ── Constants ────────────────────────────────────────────────────────────────
# LTP shadow comparison: run at most every N seconds in background
_SHADOW_INTERVAL_SEC = 300   # every 5 minutes
# Parity thresholds for scoring
_LTP_WARN_PCT  = 1.0   # 1%  — flag as divergent
_LTP_CRIT_PCT  = 2.0   # 2%  — flag as critical


class AngelOneReadinessAuditor:
    """Thread-safe singleton accumulating all 6 phase metrics each session."""

    def __init__(self) -> None:
        self._mu = threading.Lock()

        # Phase 1 — per-request metrics
        self._p1: Dict[str, Dict[str, Any]] = {
            "ANGELONE": {"requests": 0, "success": 0, "failure": 0, "latency_ms_sum": 0, "timeouts": 0},
            "DHAN":     {"requests": 0, "success": 0, "failure": 0, "latency_ms_sum": 0, "timeouts": 0},
            "YAHOO":    {"requests": 0, "success": 0, "failure": 0, "latency_ms_sum": 0, "timeouts": 0},
        }

        # Phase 2 — LTP parity
        self._p2_diffs: List[float] = []       # abs % differences
        self._p2_over1: int = 0
        self._p2_over2: int = 0
        self._p2_total_symbols: int = 0
        self._p2_last_run: float = 0.0
        self._p2_running = threading.Event()

        # Phase 3 — options chain readiness per symbol per source
        self._p3: Dict[str, Dict[str, Any]] = {}   # symbol → {ANGELONE: {...}, DHAN: {...}}

        # Phase 4 — candidate parity (LTP delta → score delta proxy)
        self._p4_deltas: List[float] = []
        self._p4_rank_flips: int = 0

        # Phase 5 — signal parity (simple: were signals affected by LTP divergence?)
        self._p5_signals: int = 0
        self._p5_divergent: int = 0   # signals where LTP diff > 1% for that symbol

        # Phase 6 — reliability
        self._p6: Dict[str, Dict[str, int]] = {
            "ANGELONE": {"auth_fail": 0, "token_fail": 0, "rate_limit": 0,
                         "timeout": 0, "empty": 0, "partial": 0, "total": 0},
            "DHAN":     {"auth_fail": 0, "token_fail": 0, "rate_limit": 0,
                         "timeout": 0, "empty": 0, "partial": 0, "total": 0},
        }

        # Phase 3 options chain success/fail counts
        self._p3_success: Dict[str, int] = defaultdict(int)  # source → success count
        self._p3_failure: Dict[str, int] = defaultdict(int)  # source → failure count
        self._p3_chain_records: List[Dict] = []              # last N chain records
        self._p3_oi_nonzero: Dict[str, int] = defaultdict(int)   # source → chains with total_oi>0
        self._p3_iv_nonzero: Dict[str, int] = defaultdict(int)   # source → chains with atm_iv>0

        # Internal LTP shadow cache: symbol → {ao_ltp, dhan_ltp, diff_pct, ts}
        self._ltp_shadow: Dict[str, Dict] = {}

        log.info("[AngelOneReadiness] Auditor initialised — tracking 7 phases.")

    # ─────────────────────────────────────────────────────────────────────────
    # Phase 1 — FeedComparisonAudit
    # ─────────────────────────────────────────────────────────────────────────

    def record_request(
        self,
        source: str,
        success: bool,
        latency_ms: float,
        timeout: bool = False,
        failure_reason: str = "",
    ) -> None:
        """Called by data_feed_manager for every LTP/quote request."""
        src = source.upper()
        with self._mu:
            bucket = self._p1.get(src)
            if bucket is None:
                return
            bucket["requests"] += 1
            bucket["latency_ms_sum"] += latency_ms
            if success:
                bucket["success"] += 1
            else:
                bucket["failure"] += 1
                if timeout:
                    bucket["timeouts"] += 1

    def emit_feed_comparison_audit(self) -> None:
        """Emit [FeedComparisonAudit] one-liner — called periodically (e.g. every cycle)."""
        with self._mu:
            parts = []
            for src, b in self._p1.items():
                req = b["requests"]
                if req == 0:
                    continue
                sr  = round(b["success"] / req * 100, 1)
                fr  = round(b["failure"] / req * 100, 1)
                avg = round(b["latency_ms_sum"] / max(1, b["success"]), 0)
                tr  = round(b["timeouts"] / req * 100, 1)
                parts.append(
                    f"{src}: req={req} sr={sr}% fr={fr}% avg_ms={avg:.0f} timeout_rate={tr}%"
                )
        if parts:
            log.info("[FeedComparisonAudit] %s", " | ".join(parts))

    # ─────────────────────────────────────────────────────────────────────────
    # Phase 2 — LTP Parity Shadow
    # ─────────────────────────────────────────────────────────────────────────

    def trigger_ltp_shadow(self, symbols: List[str]) -> None:
        """
        Fire-and-forget background LTP comparison.
        Throttled to once per _SHADOW_INTERVAL_SEC.
        """
        now = time.monotonic()
        if now - self._p2_last_run < _SHADOW_INTERVAL_SEC:
            return
        if self._p2_running.is_set():
            return
        if not symbols:
            return
        self._p2_last_run = now
        self._p2_running.set()
        t = threading.Thread(
            target=self._run_ltp_shadow,
            args=(list(symbols[:50]),),   # cap at 50 symbols per run
            daemon=True,
            name="AO_LTPShadow",
        )
        t.start()

    def _run_ltp_shadow(self, symbols: List[str]) -> None:
        """Background: fetch both AngelOne and Dhan LTPs and compare."""
        try:
            from data_feeds import get_feed_manager
            fm = get_feed_manager()

            t0 = time.monotonic()

            # AngelOne batch
            ao_quotes = {}
            try:
                if fm.angelone.is_live:
                    ao_quotes = fm.angelone.get_multiple_quotes(symbols) or {}
            except Exception as exc:
                log.debug("[LTPShadow] AngelOne fetch error: %s", exc)

            # Dhan individual (no reliable batch for arbitrary symbols)
            dhan_quotes = {}
            try:
                if fm.dhan.is_live:
                    from data_feeds.dhan_feed import DHAN_SECURITY_MAP
                    dhan_syms = [s for s in symbols if s.upper() in DHAN_SECURITY_MAP]
                    if dhan_syms:
                        dhan_quotes = fm.dhan.get_multiple_quotes(dhan_syms) or {}
            except Exception as exc:
                log.debug("[LTPShadow] Dhan fetch error: %s", exc)

            # Compare
            compared = 0
            diffs: List[float] = []
            over1 = 0
            over2 = 0
            samples: List[str] = []

            for sym in symbols:
                ao_q  = ao_quotes.get(sym)
                dh_q  = dhan_quotes.get(sym)
                if not ao_q or not dh_q:
                    continue
                ao_ltp = getattr(ao_q, "ltp", 0.0)
                dh_ltp = getattr(dh_q, "ltp", 0.0)
                if ao_ltp <= 0 or dh_ltp <= 0:
                    continue
                diff_pct = abs(ao_ltp - dh_ltp) / dh_ltp * 100.0
                diffs.append(diff_pct)
                compared += 1

                # Update shadow cache
                with self._mu:
                    self._ltp_shadow[sym] = {
                        "ao_ltp": ao_ltp, "dhan_ltp": dh_ltp,
                        "diff_pct": diff_pct, "ts": datetime.now(timezone.utc).isoformat(),
                    }

                if diff_pct > _LTP_CRIT_PCT:
                    over2 += 1
                    over1 += 1
                    samples.append(f"{sym}:{diff_pct:.2f}%")
                elif diff_pct > _LTP_WARN_PCT:
                    over1 += 1
                    samples.append(f"{sym}:{diff_pct:.2f}%")

            elapsed = round((time.monotonic() - t0) * 1000, 0)

            with self._mu:
                self._p2_diffs.extend(diffs)
                self._p2_over1 += over1
                self._p2_over2 += over2
                self._p2_total_symbols += compared

            if compared > 0:
                avg_diff = sum(diffs) / len(diffs)
                max_diff = max(diffs)
                log.info(
                    "[LTPParityAudit] compared=%d avg_difference_pct=%.3f max_difference_pct=%.3f "
                    "symbols_over_1pct=%d symbols_over_2pct=%d elapsed_ms=%.0f%s",
                    compared, avg_diff, max_diff, over1, over2, elapsed,
                    f" divergent={','.join(samples[:5])}" if samples else "",
                )
            else:
                log.debug("[LTPShadow] No comparable symbols (ao=%d dhan=%d)", len(ao_quotes), len(dhan_quotes))

        except Exception as exc:
            log.debug("[LTPShadow] Run failed: %s", exc)
        finally:
            self._p2_running.clear()

    def get_ltp_shadow(self, symbol: str) -> Optional[Dict]:
        """Return latest shadow comparison for a symbol, or None."""
        with self._mu:
            return dict(self._ltp_shadow.get(symbol, {})) or None

    # ─────────────────────────────────────────────────────────────────────────
    # Phase 3 — Options Chain Readiness
    # ─────────────────────────────────────────────────────────────────────────

    def record_options_chain(
        self,
        symbol: str,
        source: str,
        success: bool,
        contracts: int = 0,
        atm_iv: float = 0.0,
        dte: int = 0,
        expiry: str = "",
        total_oi: float = 0.0,
    ) -> None:
        src = source.upper()
        with self._mu:
            if success:
                self._p3_success[src] += 1
                if total_oi > 0:
                    self._p3_oi_nonzero[src] += 1
                if atm_iv > 0:
                    self._p3_iv_nonzero[src] += 1
            else:
                self._p3_failure[src] += 1
            record = {
                "symbol": symbol, "source": src, "success": success,
                "contracts": contracts, "atm_iv": atm_iv, "dte": dte,
                "expiry": expiry, "total_oi": total_oi,
                "ts": datetime.now(timezone.utc).isoformat(),
            }
            self._p3_chain_records.append(record)
            if len(self._p3_chain_records) > 200:
                self._p3_chain_records.pop(0)

    def emit_options_chain_readiness(self, symbol: str, source: str,
                                     contracts: int, atm_iv: float,
                                     dte: int, chain_live: bool) -> None:
        """Emit [OptionsChainReadiness] immediately after a chain fetch."""
        with self._mu:
            total_ao = self._p3_success.get("ANGELONE", 0) + self._p3_failure.get("ANGELONE", 0)
            total_dh = self._p3_success.get("DHAN", 0) + self._p3_failure.get("DHAN", 0)
            ao_rate = round(self._p3_success.get("ANGELONE", 0) / max(1, total_ao) * 100, 1)
            dh_rate = round(self._p3_success.get("DHAN", 0) / max(1, total_dh) * 100, 1)

        log.info(
            "[OptionsChainReadiness] symbol=%s source=%s chain_live=%s contracts=%d "
            "atm_iv=%.1f%% dte=%d | session: ao_live_rate=%.1f%% dh_live_rate=%.1f%%",
            symbol, source, chain_live, contracts, atm_iv, dte, ao_rate, dh_rate,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Phase 4 — Candidate Parity (LTP delta → score sensitivity proxy)
    # ─────────────────────────────────────────────────────────────────────────

    def record_candidate_parity(self, candidates: List[Dict]) -> None:
        """
        For each candidate, look up LTP shadow and estimate score sensitivity.
        score_delta_proxy = ltp_diff_pct × breakout_proximity_factor
        (If LTP differs by X%, breakout/resistance distance changes proportionally)
        """
        if not candidates:
            return
        divergent_count = 0
        deltas: List[float] = []
        parts: List[str] = []

        for c in candidates:
            sym = c.get("symbol", "")
            shadow = self.get_ltp_shadow(sym)
            if not shadow:
                continue
            diff_pct = shadow.get("diff_pct", 0.0)
            # Score sensitivity: resistance/support proximity is the score driver
            # A 1% LTP difference near resistance (within 2%) → ~50% score sensitivity
            # Simple proxy: delta_score = diff_pct * 0.3 (conservative estimate)
            score_dhan   = c.get("score", 0.5)
            score_ao     = round(max(0.0, min(1.0, score_dhan * (1 + (diff_pct / 100) * 0.3))), 4)
            score_delta  = abs(score_ao - score_dhan)
            deltas.append(score_delta)
            if diff_pct > _LTP_WARN_PCT:
                divergent_count += 1
                parts.append(f"{sym}:Δscore={score_delta:.4f}")

        with self._mu:
            self._p4_deltas.extend(deltas)
            if divergent_count > 0:
                self._p4_rank_flips += divergent_count

        if parts:
            log.info(
                "[CandidateParityAudit] checked=%d divergent_ltp=%d "
                "avg_score_delta=%.4f rank_flip_proxy=%d divergent=%s",
                len(candidates), divergent_count,
                sum(deltas) / max(1, len(deltas)),
                divergent_count, " | ".join(parts[:5]),
            )

    # ─────────────────────────────────────────────────────────────────────────
    # Phase 5 — Signal Parity
    # ─────────────────────────────────────────────────────────────────────────

    def record_signal(self, symbol: str, entry: float, stop: float,
                      target: float, confidence: float) -> None:
        """Called when a signal is generated. Checks if LTP shadow suggests divergence."""
        shadow = self.get_ltp_shadow(symbol)
        diff_pct = shadow.get("diff_pct", 0.0) if shadow else 0.0
        is_divergent = diff_pct > _LTP_WARN_PCT

        with self._mu:
            self._p5_signals += 1
            if is_divergent:
                self._p5_divergent += 1

        if is_divergent:
            ao_ltp   = shadow.get("ao_ltp", 0.0) if shadow else 0.0
            dhan_ltp = shadow.get("dhan_ltp", 0.0) if shadow else 0.0
            log.info(
                "[SignalParityAudit] symbol=%s entry=%.2f stop=%.2f target=%.2f "
                "confidence=%.2f dhan_ltp=%.2f angel_ltp=%.2f diff_pct=%.2f%% "
                "signal_affected=True",
                symbol, entry, stop, target, confidence, dhan_ltp, ao_ltp, diff_pct,
            )

    # ─────────────────────────────────────────────────────────────────────────
    # Capability Inventory
    # ─────────────────────────────────────────────────────────────────────────

    def _build_capability_inventory(self) -> List[Tuple[str, str, str]]:
        """
        Build a per-capability status list derived from observed runtime data.
        Returns list of (capability, status, reason) tuples.
        Status values: SUPPORTED | PARTIALLY_SUPPORTED | UNSUPPORTED
        """
        inv: List[Tuple[str, str, str]] = []

        # quotes_supported — did AngelOne return any successful single-symbol quote?
        ao_req  = self._p1["ANGELONE"]["requests"]
        ao_succ = self._p1["ANGELONE"]["success"]
        if ao_succ > 0:
            inv.append(("quotes_supported", "SUPPORTED",
                         f"success_rate={round(ao_succ/max(1,ao_req)*100,1)}%"))
        elif ao_req > 0:
            inv.append(("quotes_supported", "PARTIALLY_SUPPORTED",
                         f"requests={ao_req}_success=0_check_token"))
        else:
            inv.append(("quotes_supported", "UNSUPPORTED",
                         "no_requests_observed_this_session"))

        # multi_quotes_supported — same evidence pool (batch uses same API path)
        if ao_succ > 0:
            inv.append(("multi_quotes_supported", "SUPPORTED",
                         "batch_via_getMarketData_FULL"))
        else:
            inv.append(("multi_quotes_supported",
                         "PARTIALLY_SUPPORTED" if ao_req > 0 else "UNSUPPORTED",
                         "no_successful_batch_observed"))

        # options_chain_supported — from Phase 3 success rate
        ao_opt_ok  = self._p3_success.get("ANGELONE", 0)
        ao_opt_tot = ao_opt_ok + self._p3_failure.get("ANGELONE", 0)
        if ao_opt_ok > 0:
            rate = round(ao_opt_ok / max(1, ao_opt_tot) * 100, 1)
            status = "SUPPORTED" if rate >= 80 else "PARTIALLY_SUPPORTED"
            inv.append(("options_chain_supported", status,
                         f"live_rate={rate}%_contracts_delivered"))
        elif ao_opt_tot > 0:
            inv.append(("options_chain_supported", "UNSUPPORTED",
                         f"attempted={ao_opt_tot}_all_failed"))
        else:
            inv.append(("options_chain_supported", "UNSUPPORTED",
                         "no_options_chain_requests_observed"))

        # expiry_selection_supported — structural: AngelOne ExpirySelectionAudit fires
        # and correctly selects nearest DTE.  Static SUPPORTED.
        inv.append(("expiry_selection_supported", "SUPPORTED",
                     "nearest_dte_selection_via_ExpirySelectionAudit"))

        # iv_supported — AngelOne getMarketData FULL mode does not return IV.
        # iv=0.0 is hardcoded in angelone_feed.py with explicit comment.
        ao_iv_chains = self._p3_iv_nonzero.get("ANGELONE", 0)
        if ao_iv_chains > 0:
            inv.append(("iv_supported", "PARTIALLY_SUPPORTED",
                         f"{ao_iv_chains}_chains_had_nonzero_iv"))
        else:
            inv.append(("iv_supported", "UNSUPPORTED",
                         "getMarketData_FULL_does_not_return_iv_field"
                         "_NSE_synthetic_chain_required_for_iv"))

        # oi_supported — AngelOne returns total_oi and per-contract OI from market data
        ao_oi_chains = self._p3_oi_nonzero.get("ANGELONE", 0)
        if ao_oi_chains > 0:
            inv.append(("oi_supported", "SUPPORTED",
                         f"{ao_oi_chains}_chains_had_nonzero_total_oi"))
        elif ao_opt_ok > 0:
            # Chains were fetched successfully but total_oi was always 0
            inv.append(("oi_supported", "PARTIALLY_SUPPORTED",
                         "chains_fetched_but_total_oi_was_zero_confirm_manually"))
        else:
            inv.append(("oi_supported", "UNSUPPORTED",
                         "no_successful_chains_to_evaluate"))

        # greeks_supported — AngelOne API does not provide delta/gamma/vega/theta
        # They are computed from Black-Scholes locally, which requires IV.
        # Since IV is UNSUPPORTED, greeks are also UNSUPPORTED.
        inv.append(("greeks_supported", "UNSUPPORTED",
                     "not_provided_by_AngelOne_API"
                     "_computed_locally_via_BS_but_requires_iv_which_is_unsupported"))

        return inv

    # ─────────────────────────────────────────────────────────────────────────
    # Phase 6 — Feed Reliability
    # ─────────────────────────────────────────────────────────────────────────

    def record_failure(self, source: str, failure_type: str) -> None:
        """Record a feed failure event. failure_type: auth_fail|token_fail|rate_limit|timeout|empty|partial"""
        src = source.upper()
        with self._mu:
            bucket = self._p6.get(src)
            if bucket is None:
                return
            bucket["total"] += 1
            ft = failure_type.lower()
            if ft in bucket:
                bucket[ft] += 1

    def emit_feed_reliability_audit(self) -> None:
        """Emit [FeedReliabilityAudit] summary."""
        with self._mu:
            parts = []
            for src, b in self._p6.items():
                total = b["total"]
                # Reliability score: 100 - weighted failure rate
                rel = max(0, 100 - b["auth_fail"] * 5 - b["timeout"] * 2
                          - b["rate_limit"] * 3 - b["empty"] * 1)
                parts.append(
                    f"{src}: total_failures={total} auth={b['auth_fail']} "
                    f"timeout={b['timeout']} rate_limit={b['rate_limit']} "
                    f"empty={b['empty']} partial={b['partial']} "
                    f"reliability_score={rel}",
                )
        log.info("[FeedReliabilityAudit] %s", " | ".join(parts))

    # ─────────────────────────────────────────────────────────────────────────
    # Phase 7 — AngelOneReadinessReport (EOD)
    # ─────────────────────────────────────────────────────────────────────────

    def emit_readiness_report(self) -> None:
        """Emit [AngelOneReadinessReport] — call at EOD."""
        with self._mu:
            # LTP parity score (0–100)
            total_sym = self._p2_total_symbols
            ltp_over1 = self._p2_over1
            ltp_over2 = self._p2_over2
            avg_ltp_diff = (sum(self._p2_diffs) / len(self._p2_diffs)) if self._p2_diffs else 0.0
            max_ltp_diff = max(self._p2_diffs) if self._p2_diffs else 0.0
            ltp_score = max(0, round(100 - ltp_over1 * 2 - ltp_over2 * 5))

            # Options parity score
            ao_opt_ok  = self._p3_success.get("ANGELONE", 0)
            ao_opt_tot = ao_opt_ok + self._p3_failure.get("ANGELONE", 0)
            dh_opt_ok  = self._p3_success.get("DHAN", 0)
            dh_opt_tot = dh_opt_ok + self._p3_failure.get("DHAN", 0)
            ao_opt_rate = ao_opt_ok / max(1, ao_opt_tot) * 100
            options_score = round(ao_opt_rate)

            # Candidate parity score
            avg_score_delta = (sum(self._p4_deltas) / len(self._p4_deltas)) if self._p4_deltas else 0.0
            candidate_score = max(0, round(100 - self._p4_rank_flips * 2 - avg_score_delta * 200))

            # Signal parity score
            sig_div_rate = (self._p5_divergent / max(1, self._p5_signals)) * 100
            signal_score = max(0, round(100 - sig_div_rate * 2))

            # Feed reliability score (AngelOne)
            ao_fail = self._p6["ANGELONE"]
            ao_total_fail = ao_fail["total"]
            reliability_score = max(0, 100 - ao_fail["auth_fail"] * 10
                                    - ao_fail["timeout"] * 2 - ao_fail["rate_limit"] * 5
                                    - ao_fail["empty"] * 1)

            # Phase 1 AO success rate
            ao_req = self._p1["ANGELONE"]["requests"]
            ao_succ = self._p1["ANGELONE"]["success"]
            ao_req_rate = round(ao_succ / max(1, ao_req) * 100, 1)

            # Overall confidence
            confidence = round((ltp_score + options_score + candidate_score
                                + signal_score + reliability_score) / 5)
            migration_ready = "YES" if confidence >= 80 else "NO"
            recommendation = (
                "Ready for Dhan retirement" if confidence >= 80
                else "Continue dual-feed — gaps remain"
            )

        log.info(
            "[AngelOneReadinessReport] "
            "ltp_parity_score=%d options_parity_score=%d candidate_parity_score=%d "
            "signal_parity_score=%d reliability_score=%d "
            "overall_confidence=%d migration_ready=%s "
            "recommendation=%s | "
            "detail: ltp_compared=%d avg_ltp_diff=%.3f%% max_ltp_diff=%.3f%% "
            "symbols_over_1pct=%d symbols_over_2pct=%d "
            "ao_options_rate=%.1f%% dh_options_rate=%.1f%% "
            "ao_quote_success_rate=%.1f%% ao_total_failures=%d "
            "signals_total=%d signals_divergent=%d",
            ltp_score, options_score, candidate_score,
            signal_score, reliability_score,
            confidence, migration_ready, recommendation,
            total_sym, avg_ltp_diff, max_ltp_diff,
            ltp_over1, ltp_over2,
            ao_opt_rate, dh_opt_ok / max(1, dh_opt_tot) * 100,
            ao_req_rate, ao_total_fail,
            self._p5_signals, self._p5_divergent,
        )

        # Capability inventory — one line per capability
        cap_inv = self._build_capability_inventory()
        for cap_name, cap_status, cap_reason in cap_inv:
            log.info(
                "[CapabilityInventory] capability=%-35s status=%-20s reason=%s",
                cap_name, cap_status, cap_reason,
            )
