"""
Filter Funnel Audit
====================
Session-scoped (in-memory) tracker for per-stage candidate attrition in the
scan pipeline.

Problem it detects:
    The system processes a candidate universe of ~65 symbols per cycle, but
    only emits 0-3 signals.  Without stage-by-stage counting, it's impossible
    to distinguish between:
      - "no signals because the market regime is right but we're over-filtering"
      - "no signals because candidates expired / were invalidated upstream"
      - "no signals because ATR volatility guard is firing on everything"
      - "no signals because conviction thresholds are too tight"

Funnel stages (in order):
    PREPARED          — store candidates that passed TTL check (entry)
    ttl_rejected      — expired before reaching _identify_setup (pre-filter)
    invalidated       — breakout invalidated this cycle (pre-filter)
    atr_blocked       — volatility guard fired (high_atr)
    trend_blocked     — regime guard fired (bear_market, bull_gate)
    liquidity_blocked — volume too low (breakout_vol_low)
    conviction_blocked — RSI/price condition not met (breakout_rsi_hi,
                         retest_rsi_oob, bounce_price_hi, rsi_neutral,
                         short_conditions, pullback_miss)
    signal_found      — candidate produced a TradeSignal

Emitted log tags:
    [FilterFunnelAudit]  — per scan cycle, with full per-stage breakdown
    [FilterFunnelReport] — EOD session summary

Governance: strictly observational.
    - Never blocks execution.
    - Never changes thresholds, filters, or strategy logic.
    - funnel_efficiency and top_block are purely diagnostic.
"""
from __future__ import annotations

import threading
from collections import defaultdict
from datetime import date
from typing import Dict, Optional

from utils.logger import get_logger

log = get_logger(__name__)

# ── Mapping: _identify_setup reason codes → funnel stages ─────────────────
REASON_TO_STAGE: Dict[str, str] = {
    "high_atr":           "atr_blocked",
    "bear_market":        "trend_blocked",
    "bull_gate":          "trend_blocked",
    "breakout_vol_low":   "liquidity_blocked",
    "breakout_rsi_hi":    "conviction_blocked",
    "retest_rsi_oob":     "conviction_blocked",
    "bounce_price_hi":    "conviction_blocked",
    "rsi_neutral":        "conviction_blocked",
    "short_conditions":   "conviction_blocked",
    "pullback_miss":      "conviction_blocked",
    "signal_found":       "signal_found",
}

FUNNEL_STAGES = (
    "ttl_rejected",
    "invalidated",
    "atr_blocked",
    "trend_blocked",
    "liquidity_blocked",
    "conviction_blocked",
    "signal_found",
)

# Scanner-level stages (market_scanner.py funnel, upstream of equity_scanner_ai)
SCANNER_STAGES = (
    "data_failed",          # symbol fetch/compute failed entirely
    "sector_cap_removed",   # removed by _apply_sector_cap()
    "score_floor_removed",  # removed by MIN_PREPARED_SCORE floor
    "simulation_rejected",  # removed by simulation/governance path
    "governance_rejected",  # removed by risk/governance gate
)


class FilterFunnelAudit:
    """
    Thread-safe, session-scoped tracker for filter-stage attrition.

    Auto-resets at date rollover (midnight).
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._reset_date: date = date.today()
        self._reset()

    # ── Internal lifecycle ────────────────────────────────────────────────────

    def _reset(self) -> None:
        # Per-session cumulative counts per funnel stage
        self._session_totals: Dict[str, int] = defaultdict(int)
        self._session_prepared: int = 0
        self._session_scans: int = 0

        # Scanner-level stage totals (market_scanner.py funnel)
        self._scanner_totals: Dict[str, int] = defaultdict(int)
        self._scanner_attempted: int = 0   # symbols attempted total
        self._scanner_data_ok: int = 0     # passed data processing

        # Last cycle snapshot (for quick diagnostics)
        self._last_cycle: dict = {}
        self._last_scanner: dict = {}

    def _ensure_today(self) -> None:
        today = date.today()
        if today != self._reset_date:
            with self._lock:
                if today != self._reset_date:
                    self._reset_date = today
                    self._reset()

    # ── Public API ────────────────────────────────────────────────────────────
    def record_scanner_stage(
        self,
        symbols_attempted:     int,
        data_ok:               int,
        after_sector_cap:      int,
        after_score_floor:     int,
        simulation_rejected:   int = 0,
        governance_rejected:   int = 0,
    ) -> None:
        """
        Record market_scanner.py funnel stage counts for one scan run.

        Args:
            symbols_attempted:   total symbols attempted (raw universe)
            data_ok:             symbols that passed data fetch + compute
            after_sector_cap:    candidates remaining after _apply_sector_cap()
            after_score_floor:   candidates remaining after MIN_PREPARED_SCORE filter
            simulation_rejected: candidates dropped by simulation gate (optional)
            governance_rejected: candidates dropped by governance gate (optional)
        """
        self._ensure_today()
        data_failed          = symbols_attempted - data_ok
        sector_cap_removed   = data_ok - after_sector_cap
        score_floor_removed  = after_sector_cap - after_score_floor

        snap = {
            "symbols_attempted":   symbols_attempted,
            "data_ok":             data_ok,
            "data_failed":         data_failed,
            "after_sector_cap":    after_sector_cap,
            "sector_cap_removed":  sector_cap_removed,
            "after_score_floor":   after_score_floor,
            "score_floor_removed": score_floor_removed,
            "simulation_rejected": simulation_rejected,
            "governance_rejected": governance_rejected,
        }
        with self._lock:
            self._scanner_attempted += symbols_attempted
            self._scanner_data_ok   += data_ok
            for stage in SCANNER_STAGES:
                self._scanner_totals[stage] += snap.get(stage, 0)
            self._last_scanner = snap

    def record_cycle(
        self,
        prepared_count:    int,
        ttl_rejected:      int,
        invalidated:       int,
        rejection_reasons: Dict[str, int],
    ) -> None:
        """
        Record one scan cycle's filter funnel.

        Args:
            prepared_count:    number of candidates that reached _identify_setup
            ttl_rejected:      dropped due to TTL expiry before setup check
            invalidated:       dropped due to breakout invalidation this cycle
            rejection_reasons: the ``_r`` dict from scan() — reason_code → count
        """
        self._ensure_today()

        # Build per-stage counts for this cycle
        cycle: Dict[str, int] = {s: 0 for s in FUNNEL_STAGES}
        cycle["ttl_rejected"] = ttl_rejected
        cycle["invalidated"]  = invalidated

        for reason, count in rejection_reasons.items():
            stage = REASON_TO_STAGE.get(reason)
            if stage:
                cycle[stage] += count

        with self._lock:
            self._session_scans += 1
            self._session_prepared += prepared_count
            for stage, count in cycle.items():
                self._session_totals[stage] += count
            self._last_cycle = dict(cycle)
            self._last_cycle["prepared"] = prepared_count

    def emit_cycle_audit(self) -> None:
        """Emit [FilterFunnelAudit] with this cycle's per-stage breakdown."""
        self._ensure_today()
        with self._lock:
            c = dict(self._last_cycle)
            sc = dict(self._last_scanner)

        if not c:
            return

        prepared      = c.get("prepared", 0)
        signals_found = c.get("signal_found", 0)
        blocked       = sum(c.get(s, 0) for s in FUNNEL_STAGES if s != "signal_found")
        funnel_eff    = (signals_found / prepared * 100.0) if prepared > 0 else 0.0

        # Find the top blocking stage
        top_stage, top_count = "none", 0
        for stage in FUNNEL_STAGES:
            if stage == "signal_found":
                continue
            if c.get(stage, 0) > top_count:
                top_count = c[stage]
                top_stage = stage

        log.info(
            "[FilterFunnelAudit]"
            " prepared=%d ttl_rejected=%d invalidated=%d"
            " atr_blocked=%d trend_blocked=%d liquidity_blocked=%d conviction_blocked=%d"
            " signal_found=%d total_blocked=%d funnel_efficiency=%.1f%%"
            " top_block=%s(%d)"
            " | scanner_attempted=%d data_ok=%d sector_cap_removed=%d score_floor_removed=%d",
            prepared,
            c.get("ttl_rejected", 0),
            c.get("invalidated", 0),
            c.get("atr_blocked", 0),
            c.get("trend_blocked", 0),
            c.get("liquidity_blocked", 0),
            c.get("conviction_blocked", 0),
            signals_found,
            blocked,
            funnel_eff,
            top_stage, top_count,
            sc.get("symbols_attempted", 0),
            sc.get("data_ok", 0),
            sc.get("sector_cap_removed", 0),
            sc.get("score_floor_removed", 0),
        )

    def emit_funnelcompression(self) -> None:
        """
        Emit [FunnelCompression] — full end-to-end candidate attrition in one line.
        Call once after both scanner and scan() stages are complete.
        """
        self._ensure_today()
        with self._lock:
            sc = dict(self._last_scanner)
            cy = dict(self._last_cycle)

        attempted      = sc.get("symbols_attempted", 0)
        data_ok        = sc.get("data_ok", 0)
        after_sec_cap  = sc.get("after_sector_cap", 0)
        after_floor    = sc.get("after_score_floor", 0)
        prepared       = cy.get("prepared", 0)       # equity_scanner TTL/invalid survivors
        signals_found  = cy.get("signal_found", 0)

        # Compression ratio: fraction of attempted that become signals
        compression = (signals_found / attempted * 100.0) if attempted > 0 else 0.0

        log.info(
            "[FunnelCompression]"
            " attempted=%d"
            " \u2192 data_ok=%d (-%d data_failed)"
            " \u2192 sector_cap=%d (-%d removed)"
            " \u2192 score_floor=%d (-%d removed)"
            " \u2192 scanner_prepared=%d (-%d ttl_invalidated)"
            " \u2192 signals=%d"
            " compression_ratio=%.2f%%",
            attempted,
            data_ok,        attempted - data_ok,
            after_sec_cap,  data_ok - after_sec_cap,
            after_floor,    after_sec_cap - after_floor,
            prepared,       after_floor - prepared if after_floor >= prepared else 0,
            signals_found,
            compression,
        )

    def emit_eod_report(self) -> None:
        """Emit [FilterFunnelReport] EOD session summary."""
        self._ensure_today()
        with self._lock:
            totals   = dict(self._session_totals)
            sc_tot   = dict(self._scanner_totals)
            prepared = self._session_prepared
            scans    = self._session_scans
            sc_att   = self._scanner_attempted
            sc_ok    = self._scanner_data_ok

        avg_signals  = totals.get("signal_found", 0) / max(1, scans)
        funnel_eff   = (totals.get("signal_found", 0) / max(1, prepared) * 100.0)

        # Session top-block
        top_s, top_c = "none", 0
        for stage in FUNNEL_STAGES:
            if stage == "signal_found":
                continue
            if totals.get(stage, 0) > top_c:
                top_c = totals[stage]
                top_s = stage

        log.info(
            "[FilterFunnelReport]"
            " session_scans=%d total_prepared=%d avg_signals_per_scan=%.1f"
            " funnel_efficiency=%.1f%%"
            " ttl_rejected=%d invalidated=%d"
            " atr_blocked=%d trend_blocked=%d liquidity_blocked=%d conviction_blocked=%d"
            " signal_found=%d  top_block=%s(%d)"
            " | scanner_session: attempted=%d data_ok=%d"
            " sector_cap_removed=%d score_floor_removed=%d"
            " simulation_rejected=%d governance_rejected=%d",
            scans, prepared, avg_signals,
            funnel_eff,
            totals.get("ttl_rejected", 0),
            totals.get("invalidated", 0),
            totals.get("atr_blocked", 0),
            totals.get("trend_blocked", 0),
            totals.get("liquidity_blocked", 0),
            totals.get("conviction_blocked", 0),
            totals.get("signal_found", 0),
            top_s, top_c,
            sc_att, sc_ok,
            sc_tot.get("sector_cap_removed", 0),
            sc_tot.get("score_floor_removed", 0),
            sc_tot.get("simulation_rejected", 0),
            sc_tot.get("governance_rejected", 0),
        )

    def get_stats(self) -> dict:
        """Return current stats dict (for programmatic access)."""
        self._ensure_today()
        with self._lock:
            return {
                "session_scans":   self._session_scans,
                "session_totals":  dict(self._session_totals),
                "last_cycle":      dict(self._last_cycle),
            }


# ── Singleton ─────────────────────────────────────────────────────────────────
_INSTANCE: Optional[FilterFunnelAudit] = None
_INSTANCE_LOCK = threading.Lock()


def get_filter_funnel_audit() -> FilterFunnelAudit:
    """Thread-safe singleton accessor."""
    global _INSTANCE
    if _INSTANCE is None:
        with _INSTANCE_LOCK:
            if _INSTANCE is None:
                _INSTANCE = FilterFunnelAudit()
    return _INSTANCE
