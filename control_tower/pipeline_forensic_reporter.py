"""
Pipeline Forensic Reporter — daily observational telemetry accumulator.

Aggregates pipeline metrics across all scan cycles and emits structured
[Pipeline*] log tags each cycle plus a [PipelineForensicSummary] at EOD.

GOVERNANCE: Purely observational — no behavioral mutation, no threshold
auto-tuning, no strategy disabling.  Purpose: research-quality explainability.

Usage:
    from control_tower.pipeline_forensic_reporter import get_forensic_reporter
    reporter = get_forensic_reporter()
    reporter.record_scan_cycle(...)      # called every scan()
    reporter.record_invalidation(...)    # called on every breakout invalidation
    reporter.emit_daily_summary()        # called at EOD from _do_eod_learning()
"""

from __future__ import annotations

import threading
from collections import defaultdict
from datetime import date
from typing import Dict, List, Optional

from utils.logger import get_logger

log = get_logger(__name__)

_REPORTER_INSTANCE: Optional["PipelineForensicReporter"] = None
_REPORTER_LOCK = threading.Lock()


# ---------------------------------------------------------------------------
# Rejection-reason → filter category mapping
# Sourced from _identify_setup() docstring in equity_scanner_ai.py
# ---------------------------------------------------------------------------
_FILTER_MAP: Dict[str, str] = {
    "high_atr":          "atr_filter",
    "bear_market":       "regime_filter",
    "bull_gate":         "regime_filter",
    "breakout_vol_low":  "liquidity_filter",
    "breakout_rsi_hi":   "trend_filter",
    "retest_rsi_oob":    "trend_filter",
    "pullback_miss":     "trend_filter",
    "short_conditions":  "trend_filter",
    "bounce_price_hi":   "trend_filter",
    "rsi_neutral":       "trend_filter",
}

# Rejection-reason → strategy label
_STRATEGY_MAP: Dict[str, str] = {
    "breakout_vol_low":  "breakout",
    "breakout_rsi_hi":   "breakout",
    "retest_rsi_oob":    "momentum_retest",
    "pullback_miss":     "trend_pullback",
    "bull_gate":         "trend_pullback",
    "short_conditions":  "high_rsi_short",
    "bounce_price_hi":   "mean_reversion",
    "rsi_neutral":       "mean_reversion",
}


class PipelineForensicReporter:
    """
    Thread-safe daily pipeline metrics accumulator.

    All ``record_*`` methods are safe to call from scan() threads.
    Counters auto-reset at midnight (date rollover).
    ``emit_daily_summary()`` snapshots counters under lock before emitting.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._reset()

    # ------------------------------------------------------------------
    # Internal reset (called at init and on date rollover)
    # ------------------------------------------------------------------
    def _reset(self) -> None:
        """Reset all counters.  Must be called under self._lock."""
        self._date = date.today()

        # ── Universe stage ──────────────────────────────────────────
        self._cycles:             int = 0
        self._sym_attempted:      int = 0
        self._sym_signals:        int = 0   # signals found (passed all filters)
        self._sym_atr_rejected:   int = 0   # high_atr rejections
        self._sym_regime_blocked: int = 0   # bear_market rejections

        # ── Filtering stage ─────────────────────────────────────────
        self._filter_counts: Dict[str, int] = defaultdict(int)
        self._rejected_total: int = 0

        # ── Strategy stage ──────────────────────────────────────────
        self._strategy_signals:  Dict[str, int] = defaultdict(int)   # strategy → accepted
        self._strategy_rejected: Dict[str, int] = defaultdict(int)   # strategy → rejected
        self._regime_history:    List[str]       = []                 # regime per cycle

        # ── Premarket / lifecycle ────────────────────────────────────
        self._premarket_promoted:    int = 0
        self._premarket_downgraded:  int = 0
        self._premarket_invalidated: int = 0
        self._premarket_revived:     int = 0
        self._premarket_reranked:    int = 0
        self._lifecycle_transitions: int = 0

        # ── Intraday events ──────────────────────────────────────────
        self._conviction_decays:      int = 0
        self._invalidation_count:     int = 0
        self._invalidation_reasons:   Dict[str, int] = defaultdict(int)
        self._replenishment_events:   int = 0

        # ── Exploration ──────────────────────────────────────────────
        self._explore_rotations: int = 0
        self._explore_new:       int = 0
        self._explore_recycled:  int = 0

        # ── Execution stage ──────────────────────────────────────────
        self._exec_candidates:  int = 0   # signals produced by scanner
        self._exec_approved:    int = 0   # passed debate + risk
        self._exec_orders:      int = 0   # orders actually placed
        self._exec_drift:       int = 0   # cycles where top-1 candidate changed
        self._stale_exec:       int = 0
        self._sector_dist:      Dict[str, int] = defaultdict(int)

        # ── Sector coverage (across all scan cycles today) ───────────
        self._sector_coverage: Dict[str, int] = defaultdict(int)

    def _check_rollover(self) -> None:
        """If the calendar date has changed, reset all counters."""
        if date.today() != self._date:
            self._reset()

    # ==================================================================
    # Public record_* API — called from pipeline hooks
    # ==================================================================

    def record_scan_cycle(
        self,
        watchlist_total: int,
        rejection_reasons: Dict[str, int],
        signals_found: int,
        regime: str = "",
        sector_coverage: Optional[Dict[str, int]] = None,
    ) -> None:
        """
        Call once per EquityScannerAI.scan() invocation.

        Parameters
        ----------
        watchlist_total   : total symbols evaluated this cycle
        rejection_reasons : the _r dict built by scan() (reason → count)
        signals_found     : signals that passed (== _r.get("signal_found", 0))
        regime            : current market regime string
        sector_coverage   : sector → count map of evaluated symbols (optional)
        """
        with self._lock:
            self._check_rollover()
            self._cycles           += 1
            self._sym_attempted    += watchlist_total
            self._sym_signals      += signals_found
            self._sym_atr_rejected += rejection_reasons.get("high_atr", 0)
            self._sym_regime_blocked += rejection_reasons.get("bear_market", 0)
            self._rejected_total   += sum(
                v for k, v in rejection_reasons.items() if k != "signal_found"
            )
            if regime:
                self._regime_history.append(regime)

            for reason, cnt in rejection_reasons.items():
                if reason == "signal_found":
                    continue
                cat = _FILTER_MAP.get(reason, "other_filter")
                self._filter_counts[cat] += cnt
                strat = _STRATEGY_MAP.get(reason)
                if strat:
                    self._strategy_rejected[strat] += cnt

            if sector_coverage:
                for sec, cnt in sector_coverage.items():
                    self._sector_coverage[sec] += cnt

    def record_invalidation(self, symbol: str, reason: str) -> None:
        """Call for every breakout invalidation event in _prepared_watchlist()."""
        with self._lock:
            self._check_rollover()
            self._invalidation_count += 1
            # Normalise: strip parameter values e.g. "support_breakdown(ltp=...)"
            tag = reason.split("(")[0] if "(" in reason else reason
            self._invalidation_reasons[tag] += 1

    def record_lifecycle_transition(self, symbol: str, old_state: str, new_state: str) -> None:
        """Call when a candidate's lifecycle state changes."""
        with self._lock:
            self._check_rollover()
            self._lifecycle_transitions += 1

    def record_conviction_decay(self) -> None:
        """Call once per candidate where a non-normal decay rule fires."""
        with self._lock:
            self._check_rollover()
            self._conviction_decays += 1

    def record_premarket_stats(
        self,
        promoted: int = 0,
        downgraded: int = 0,
        invalidated: int = 0,
        revived: int = 0,
        reranked: int = 0,
    ) -> None:
        """Call after premarket refinement pass (if any)."""
        with self._lock:
            self._check_rollover()
            self._premarket_promoted    += promoted
            self._premarket_downgraded  += downgraded
            self._premarket_invalidated += invalidated
            self._premarket_revived     += revived
            self._premarket_reranked    += reranked

    def record_exploration_rotation(
        self,
        new_symbols: int = 0,
        recycled_symbols: int = 0,
    ) -> None:
        """Call after exploration budget runs in scan()."""
        with self._lock:
            self._check_rollover()
            self._explore_rotations += 1
            self._explore_new       += new_symbols
            self._explore_recycled  += recycled_symbols

    def record_execution_cycle(
        self,
        candidates: int,
        approved: int,
        orders: int,
        regime: str = "",
        decision_drift: bool = False,
        stale_count: int = 0,
        sector_dist: Optional[Dict[str, int]] = None,
    ) -> None:
        """
        Call once per run_full_cycle() at the SignalLifecycle summary point.

        Parameters
        ----------
        candidates     : signals produced by scanner this cycle
        approved       : signals that survived debate + risk gate
        orders         : orders actually placed this cycle
        regime         : current market regime string
        decision_drift : True if top-1 candidate changed from previous cycle
        stale_count    : carry positions held at this cycle
        sector_dist    : sector → signal count for executed signals
        """
        with self._lock:
            self._check_rollover()
            self._exec_candidates += candidates
            self._exec_approved   += approved
            self._exec_orders     += orders
            self._stale_exec      += stale_count
            self._exec_drift      += 1 if decision_drift else 0
            if sector_dist:
                for sec, cnt in sector_dist.items():
                    self._sector_dist[sec] += cnt

    # ==================================================================
    # Telemetry emission
    # ==================================================================

    def emit_cycle_pipeline_tags(
        self,
        cycle_num: int,
        prepared_count: int,
        invalidated_count: int,
        signals: int,
        approved: int,
        regime: str,
    ) -> None:
        """
        Emit lightweight per-cycle [PipelineUniverse] + [PipelineFiltering]
        + [PipelineStrategy] + [PipelineIntraday] tags.

        Fired once per run_full_cycle() for intraday observability.
        Not the daily summary — that is emit_daily_summary().
        """
        try:
            with self._lock:
                self._check_rollover()
                cycles     = max(1, self._cycles)
                avg_syms   = self._sym_attempted // cycles
                total_rej  = self._rejected_total
                fc         = dict(self._filter_counts)
                sr         = dict(self._strategy_rejected)
                inv_cnt    = self._invalidation_count
                dec_cnt    = self._conviction_decays

            dominant_filter   = max(fc, key=fc.get) if fc else "none"
            dominant_strategy = max(sr, key=sr.get) if sr else "none"

            log.info(
                "[PipelineUniverse] cycle=%d regime=%s "
                "watchlist=%d prepared=%d signals=%d "
                "atr_blocked=%d regime_blocked=%d session_avg=%d",
                cycle_num, regime,
                avg_syms, prepared_count, signals,
                self._sym_atr_rejected // cycles,
                self._sym_regime_blocked // cycles,
                avg_syms,
            )
            log.info(
                "[PipelineFiltering] cycle=%d "
                "atr=%d regime=%d liquidity=%d trend=%d other=%d "
                "total_rejected=%d dominant=%s",
                cycle_num,
                fc.get("atr_filter", 0),
                fc.get("regime_filter", 0),
                fc.get("liquidity_filter", 0),
                fc.get("trend_filter", 0),
                fc.get("other_filter", 0),
                total_rej,
                dominant_filter,
            )
            log.info(
                "[PipelineStrategy] cycle=%d "
                "breakout_rej=%d momentum_retest_rej=%d trend_pullback_rej=%d "
                "high_rsi_short_rej=%d mean_reversion_rej=%d "
                "dominant_strategy_blocked=%s signals_accepted=%d",
                cycle_num,
                sr.get("breakout", 0),
                sr.get("momentum_retest", 0),
                sr.get("trend_pullback", 0),
                sr.get("high_rsi_short", 0),
                sr.get("mean_reversion", 0),
                dominant_strategy,
                self._sym_signals,
            )
            log.info(
                "[PipelineIntraday] cycle=%d "
                "invalidated=%d conviction_decays=%d lifecycle_transitions=%d "
                "approved=%d orders_placed_session=%d",
                cycle_num,
                invalidated_count,
                dec_cnt,
                self._lifecycle_transitions,
                approved,
                self._exec_orders,
            )
        except Exception:
            pass   # forensic tags must never propagate

    def emit_daily_summary(self) -> None:
        """
        Emit the full [PipelineForensicSummary] plus all stage summaries.
        Called once at EOD from _do_eod_learning().

        All stage tags ([PipelineUniverse] … [PipelineExecution]) are
        re-emitted here with daily totals, then the master
        [PipelineForensicSummary] synthesises the whole day.
        """
        try:
            with self._lock:
                # Snapshot everything under lock
                d            = self._date.isoformat()
                cycles       = max(1, self._cycles)
                sym_att      = self._sym_attempted
                sym_sig      = self._sym_signals
                sym_atr      = self._sym_atr_rejected
                sym_reg      = self._sym_regime_blocked
                rej_total    = self._rejected_total
                fc           = dict(self._filter_counts)
                sr           = dict(self._strategy_rejected)
                inv_count    = self._invalidation_count
                inv_reasons  = dict(self._invalidation_reasons)
                lc_trans     = self._lifecycle_transitions
                decay_cnt    = self._conviction_decays
                repl_cnt     = self._replenishment_events
                exp_rot      = self._explore_rotations
                exp_new      = self._explore_new
                exp_rec      = self._explore_recycled
                pm_promo     = self._premarket_promoted
                pm_down      = self._premarket_downgraded
                pm_inv       = self._premarket_invalidated
                pm_rev       = self._premarket_revived
                pm_rerank    = self._premarket_reranked
                exec_cand    = self._exec_candidates
                exec_appr    = self._exec_approved
                exec_ord     = self._exec_orders
                drift_cnt    = self._exec_drift
                stale_cnt    = self._stale_exec
                sec_dist     = dict(self._sector_dist)
                sec_cov      = dict(self._sector_coverage)
                regime_hist  = list(self._regime_history)

            # Derived aggregates
            avg_syms       = sym_att // cycles
            cov_pct        = round(sym_sig / max(1, avg_syms) * 100.0, 1)
            top_filters    = sorted(fc.items(), key=lambda x: -x[1])
            top_strat_rej  = sorted(sr.items(), key=lambda x: -x[1])
            top_inv        = sorted(inv_reasons.items(), key=lambda x: -x[1])
            top_sectors    = sorted(sec_dist.items(), key=lambda x: -x[1])[:5]
            top_cov        = sorted(sec_cov.items(), key=lambda x: -x[1])[:5]
            drift_pct      = round(drift_cnt / cycles * 100.0, 1)
            inv_rate       = round(inv_count / cycles, 2)
            fresh_rate     = round(exp_new / max(1, exp_new + exp_rec) * 100.0, 1)

            # Dominant regime today
            regime_today = "UNKNOWN"
            if regime_hist:
                from collections import Counter
                regime_today = Counter(regime_hist).most_common(1)[0][0]

            # ── Stage 1: Universe ──────────────────────────────────────────
            log.info(
                "[PipelineUniverse] date=%s DAILY_SUMMARY "
                "cycles=%d symbols_attempted=%d signals_accepted=%d "
                "atr_blocked=%d regime_blocked=%d coverage_pct=%.1f%% "
                "dominant_regime=%s sector_coverage_top5=%s",
                d, cycles, sym_att, sym_sig,
                sym_atr, sym_reg, cov_pct,
                regime_today,
                str(top_cov),
            )

            # ── Stage 2: Filtering ─────────────────────────────────────────
            log.info(
                "[PipelineFiltering] date=%s DAILY_SUMMARY "
                "total_rejected=%d atr_filter=%d regime_filter=%d "
                "liquidity_filter=%d trend_filter=%d other_filter=%d "
                "dominant_filter=%s",
                d, rej_total,
                fc.get("atr_filter", 0),
                fc.get("regime_filter", 0),
                fc.get("liquidity_filter", 0),
                fc.get("trend_filter", 0),
                fc.get("other_filter", 0),
                top_filters[0][0] if top_filters else "none",
            )

            # ── Stage 3: Strategy ──────────────────────────────────────────
            log.info(
                "[PipelineStrategy] date=%s DAILY_SUMMARY "
                "breakout_rejected=%d momentum_retest_rejected=%d "
                "trend_pullback_rejected=%d high_rsi_short_rejected=%d "
                "mean_reversion_rejected=%d total_signals=%d "
                "dominant_blocked_strategy=%s",
                d,
                sr.get("breakout", 0),
                sr.get("momentum_retest", 0),
                sr.get("trend_pullback", 0),
                sr.get("high_rsi_short", 0),
                sr.get("mean_reversion", 0),
                sym_sig,
                top_strat_rej[0][0] if top_strat_rej else "none",
            )

            # ── Stage 4: Premarket ─────────────────────────────────────────
            log.info(
                "[PipelinePremarket] date=%s DAILY_SUMMARY "
                "promoted=%d downgraded=%d invalidated=%d revived=%d reranked=%d",
                d,
                pm_promo, pm_down, pm_inv, pm_rev, pm_rerank,
            )

            # ── Stage 5+6: Intraday + Lifecycle ───────────────────────────
            log.info(
                "[PipelineIntraday] date=%s DAILY_SUMMARY "
                "invalidation_events=%d avg_invalidations_per_cycle=%.2f "
                "conviction_decay_events=%d lifecycle_transitions=%d "
                "replenishment_events=%d",
                d,
                inv_count, inv_rate,
                decay_cnt, lc_trans, repl_cnt,
            )

            # ── Stage 7: Invalidation ──────────────────────────────────────
            log.info(
                "[PipelineInvalidation] date=%s DAILY_SUMMARY "
                "total=%d top_reasons=%s",
                d, inv_count, str(top_inv[:4]),
            )

            # ── Stage 8: Exploration ───────────────────────────────────────
            log.info(
                "[PipelineExploration] date=%s DAILY_SUMMARY "
                "rotations=%d new_symbols=%d recycled=%d discovery_rate=%.1f%% "
                "exploration_effectiveness=%s",
                d, exp_rot, exp_new, exp_rec, fresh_rate,
                "HIGH" if fresh_rate > 60 else "MEDIUM" if fresh_rate > 30 else "LOW",
            )

            # ── Stage 9: Execution ─────────────────────────────────────────
            log.info(
                "[PipelineExecution] date=%s DAILY_SUMMARY "
                "execution_candidates=%d approved=%d orders_placed=%d "
                "decision_drift_pct=%.1f%% stale_carry_cycles=%d "
                "sector_distribution=%s",
                d,
                exec_cand, exec_appr, exec_ord,
                drift_pct, stale_cnt,
                str(top_sectors),
            )

            # ── Stage 10: Master Forensic Summary ─────────────────────────
            log.info(
                "[PipelineForensicSummary] date=%s "
                "total_cycles=%d dominant_regime=%s "
                "avg_universe_size=%d total_signals=%d total_orders=%d "
                "invalidation_rate=%.2f/cycle conviction_decays=%d "
                "dominant_rejection_filter=%s dominant_rejection_strategy=%s "
                "exploration_fresh_rate=%.1f%% decision_drift_pct=%.1f%% "
                "lifecycle_transitions=%d "
                "AUDIT_A_strategy_producing=%s "
                "AUDIT_B_dominant_filter=%s "
                "AUDIT_C_top_sector=%s "
                "AUDIT_D_exploration=%s "
                "AUDIT_E_invalidation_realistic=%s "
                "AUDIT_F_stale_carries=%d "
                "AUDIT_G_execution_rate=%.1f%%",
                d,
                cycles, regime_today,
                avg_syms, sym_sig, exec_ord,
                inv_rate, decay_cnt,
                top_filters[0][0] if top_filters else "none",
                top_strat_rej[0][0] if top_strat_rej else "none",
                fresh_rate, drift_pct,
                lc_trans,
                # Audit answers (observational)
                top_strat_rej[0][0] if top_strat_rej else "none",   # A: which strategy is dominant rejector
                top_filters[0][0] if top_filters else "none",         # B: dominant filter
                top_sectors[0][0] if top_sectors else "none",         # C: top sector
                "FRESH" if fresh_rate > 60 else "RECYCLING" if fresh_rate < 30 else "MIXED",  # D: exploration
                "NORMAL" if inv_rate < 2.0 else "ELEVATED",           # E: invalidation realistic?
                stale_cnt,                                             # F: stale carries
                round(exec_ord / max(1, exec_cand) * 100.0, 1),      # G: execution rate
            )

            # ── Patch 5/9: Data Integrity + FalseBreakoutLearning extension ──
            try:
                from data_feeds.data_integrity_tracker import get_data_integrity_tracker as _gdit_s
                _dit = _gdit_s()
                _scalar_rec  = _dit.get_scalar_recovery_count()
                _corruptions = _dit.get_total_corruptions()
                _untrusted   = len(_dit.get_untrusted_symbols())
                log.info(
                    "[PipelineForensicSummary] date=%s "
                    "DATA_INTEGRITY: scalar_recoveries=%d corruptions=%d "
                    "untrusted_symbols=%d",
                    d, _scalar_rec, _corruptions, _untrusted,
                )
                # Trigger per-symbol trust score summary
                _dit.emit_daily_summary()
            except Exception:
                pass

            try:
                from data_feeds.false_breakout_tracker import get_false_breakout_tracker as _gfbt_s
                _gfbt_s().emit_daily_summary()
            except Exception:
                pass

        except Exception as exc:
            log.debug("[PipelineForensicSummary] emit failed: %s", exc)


# ===========================================================================
# Singleton accessor
# ===========================================================================

def get_forensic_reporter() -> PipelineForensicReporter:
    """Return (or create) the process-level forensic reporter singleton."""
    global _REPORTER_INSTANCE
    if _REPORTER_INSTANCE is None:
        with _REPORTER_LOCK:
            if _REPORTER_INSTANCE is None:
                _REPORTER_INSTANCE = PipelineForensicReporter()
    return _REPORTER_INSTANCE
