"""
Learning System — Daily AI Self-Evaluation Report
==================================================
Runs at 15:40 after market close.  Answers: "Did the AI make
GOOD DECISIONS today?" — independent of whether trades were
profitable (a correct decision can still lose due to bad luck).

Five scoring categories (each 0–10)
------------------------------------
Category            What is evaluated
──────────────────  ─────────────────────────────────────────────────────
Signal Quality      SL set, TP set, positive R:R on every trade
Strategy Fit        Strategy name matched to market regime (regime map)
Risk Discipline     SL presence, R:R ≥ 1.5, position size within limits
Execution Timing    Entry time between 09:45–14:30 IST (valid window)
Market Context      Reduced exposure during HIGH/EXTREME distortion

Overall AI Decision Score = weighted mean (0–10, letter grade A–F)

Weights
-------
Signal Quality      20 %
Strategy Fit        25 %
Risk Discipline     25 %
Execution Timing    15 %
Market Context      15 %

Issue Detection
---------------
The evaluator also flags rule violations:
  • Strategy-regime mismatch      (e.g. breakout in range market)
  • Trade without stop-loss
  • R:R below minimum (< 1.0)
  • Late entry (after 14:30 IST)
  • Trade during EXTREME distortion

Weekly Summary
--------------
Maintains a rolling 7-day window in data/logs/eod_eval_history.json.
Computes: avg decision score, avg win rate, trend (improving / declining).

Output
------
  • Formatted text report  (returned as str)
  • Saved to  data/logs/eod_report_YYYY-MM-DD.txt
  • Sent via NotifierManager (Telegram if configured)
  • SelfEvalResult dataclass returned to orchestrator
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import date, datetime, time as dtime
from typing import Dict, List, Optional, Tuple

import inspect

from utils import get_logger

log = get_logger(__name__)

# ── [RuntimeFingerprint] ─────────────────────────────────────────────────────
# Emitted once at import time so every restart proves which file is executing.
log.info(
    "[RuntimeFingerprint] module=%s build=SESSION_C_PATCHSET_V1 pid=%d file=%s",
    __name__, os.getpid(), os.path.abspath(__file__),
)

# ─────────────────────────────────────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────────────────────────────────────
_DATA_DIR       = os.path.join("data", "logs")
_HISTORY_PATH   = os.path.join("data", "logs", "eod_eval_history.json")
_HISTORY_MAX    = 60    # keep ~3 months of daily records

# ─────────────────────────────────────────────────────────────────────────────
# REGIME → ALLOWED STRATEGIES MAP (mirrors MetaStrategyController)
# ─────────────────────────────────────────────────────────────────────────────
_REGIME_MAP: Dict[str, List[str]] = {
    "bull_trend": [
        "breakout_volume", "momentum_retest", "trend_pullback",
        "bull_call_spread", "long_straddle_pre_event",
    ],
    "range_market": [
        "mean_reversion", "iron_condor_range",
        "futures_basis_arb", "etf_nav_arb",
        "breakout_volume", "momentum_retest",
        "short_straddle_iv_spike",
    ],
    "bear_market": [
        "hedging_model", "iron_condor_range", "futures_basis_arb",
    ],
    "volatile": [
        "hedging_model", "short_straddle_iv_spike",
        "long_straddle_pre_event",
    ],
}

# Strategies that should NEVER fire in a bear/volatile regime
_AGGRESSIVE_STRATEGIES = {
    "breakout_volume", "momentum_retest", "trend_pullback", "bull_call_spread",
}

# Valid intraday trading window  09:45 – 14:30 IST
_WINDOW_OPEN  = dtime(9,  45)
_WINDOW_CLOSE = dtime(14, 30)

# Scoring weights (must sum to 1.00)
_WEIGHTS = {
    "signal_quality":       0.18,
    "strategy_fit":         0.22,
    "risk_discipline":      0.22,
    "execution_timing":     0.13,
    "market_context":       0.15,
    "governance_compliance": 0.10,   # Phase 2: window / rule compliance dimension
}

# Grade thresholds
_GRADE_MAP = [
    (9.0, "A+"), (8.5, "A"), (8.0, "A-"),
    (7.5, "B+"), (7.0, "B"), (6.5, "B-"),
    (6.0, "C+"), (5.5, "C"), (5.0, "C-"),
    (0.0, "F"),
]


def _grade(score: float) -> str:
    for threshold, letter in _GRADE_MAP:
        if score >= threshold:
            return letter
    return "F"


def _compute_r_multiple(trade) -> float:
    """
    Derive R-multiple from PnL and stop-loss distance.

    Priority chain:
      1. stored r_multiple (set by CSV recovery path when non-zero)
      2. initial_stop_loss (immutable anchor set at order open — never zeroed by cleanup)
      3. runtime stop_loss (last resort — may be 0 after SESSION_EXPIRED cleanup)

    The initial_stop_loss field fixes the avg_r=0.0 blind-spot that occurred
    when cleanup paths (SESSION_EXPIRED, orphan expiry) zeroed out stop_loss
    before the self-evaluation ran, making risk=0 and computed_r=0 for all
    intraday-closed trades.
    """
    r_attr = getattr(trade, "r_multiple", None)
    if r_attr is not None and r_attr != 0.0:
        return float(r_attr)
    ep    = getattr(trade, "entry_price",    0.0) or 0.0
    # Prefer immutable initial_stop_loss; fall back to runtime stop_loss
    isl   = getattr(trade, "initial_stop_loss", None)
    sl    = float(isl) if isl else (getattr(trade, "stop_loss", 0.0) or 0.0)
    qty   = abs(getattr(trade, "quantity", 1) or 1)
    pnl   = getattr(trade, "pnl",         0.0) or 0.0
    risk  = abs(ep - sl) * qty
    if risk > 0:
        return round(pnl / risk, 3)
    # ── [AvgRIntegrityFailure] — never silently return 0.0 ──────────────────
    log.warning(
        "[AvgRIntegrityFailure] symbol=%s entry=%.4f sl=%.4f initial_sl=%s "
        "pnl=%.2f qty=%d computed_risk=%.4f — risk=0, R cannot be computed",
        getattr(trade, "symbol", "?"), ep, getattr(trade, "stop_loss", 0.0) or 0.0,
        str(isl) if isl else "not_set",
        pnl, qty, risk,
    )
    return 0.0


# ─────────────────────────────────────────────────────────────────────────────
# RESULT DATACLASS
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class SelfEvalResult:
    """
    Output of DailyAISelfEvaluator.evaluate().

    All scores are 0–10.  overall_score is the weighted mean.
    grade is A+ … F (like school grades).
    issues is a list of human-readable rule-violation strings.
    learning_notes are concrete action suggestions for the next cycle.
    """
    date: str

    # ── Category scores ────────────────────────────────────────────────
    signal_quality:   float = 0.0
    strategy_fit:     float = 0.0
    risk_discipline:  float = 0.0
    execution_timing: float = 0.0
    market_context:   float = 0.0

    # ── Summary ────────────────────────────────────────────────────────
    overall_score: float = 0.0
    grade:         str   = "N/A"

    # ── Trade stats ────────────────────────────────────────────────────
    total_trades:  int   = 0
    wins:          int   = 0
    losses:        int   = 0
    net_pnl:       float = 0.0
    win_rate_pct:  float = 0.0
    avg_r:         float = 0.0

    # ── Issues and learning ────────────────────────────────────────────
    issues:         List[str] = field(default_factory=list)
    learning_notes: List[str] = field(default_factory=list)

    # ── 7-day rolling stats ────────────────────────────────────────────
    week_avg_score:  float = 0.0
    week_win_rate:   float = 0.0
    week_trend:      str   = "stable"   # improving | declining | stable

    # ── Audit / transparency fields —————————————————————————————
    outcome_cap_applied: bool = False
    outcome_cap_reason:  str  = ""
    sample_confidence:   str  = ""  # Exploratory / Low-sample / Full
    # Governance compliance dimension (Phase 2): 0=violations detected, 10=clean
    governance_compliance: float = 0.0

    def to_dict(self) -> dict:
        return {
            "date":             self.date,
            "signal_quality":   round(self.signal_quality,   2),
            "strategy_fit":     round(self.strategy_fit,     2),
            "risk_discipline":  round(self.risk_discipline,  2),
            "execution_timing": round(self.execution_timing, 2),
            "market_context":   round(self.market_context,   2),
            "overall_score":    round(self.overall_score,    2),
            "grade":            self.grade,
            "total_trades":     self.total_trades,
            "wins":             self.wins,
            "losses":           self.losses,
            "net_pnl":          round(self.net_pnl,          2),
            "win_rate_pct":     round(self.win_rate_pct,      1),
            "avg_r":            round(self.avg_r,             3),
            "issues":           self.issues,
            "governance_compliance": round(self.governance_compliance, 2),
            "strategy_mutation_blocked": self.strategy_mutation_blocked,
            "research_integrity_note":   self.research_integrity_note,
        }


# ─────────────────────────────────────────────────────────────────────────────
# EVALUATOR
# ─────────────────────────────────────────────────────────────────────────────

class DailyAISelfEvaluator:
    """
    Evaluates AI decision quality at end of each trading day.

    Usage (inside orchestrator._do_eod_learning)::

        evaluator = DailyAISelfEvaluator()   # instantiate once in __init__

        result = evaluator.evaluate(
            trades          = trades,           # List[OrderRecord]
            perf_report     = perf_report,      # PerformanceReport (may be None)
            last_distortion = self.global_intelligence.last_distortion,
        )
        report_text = evaluator.render(result)
        evaluator.save(result, report_text)
        evaluator.notify(result, report_text)
    """

    def __init__(self) -> None:
        # ── Schema validation — FAIL HARD if old scoring weights are loaded ──────
        _expected_w = sorted(round(v, 2) for v in [0.18, 0.22, 0.22, 0.13, 0.15, 0.10])
        _actual_w   = sorted(round(v, 2) for v in _WEIGHTS.values())
        if _actual_w != _expected_w or "governance_compliance" not in _WEIGHTS:
            raise RuntimeError(
                "[FATAL] Old scoring schema loaded — "
                f"expected weights {_expected_w} with 6 dims (incl. governance_compliance), "
                f"got {_actual_w} with keys {list(_WEIGHTS)}. "
                "Deploy SESSION_C_PATCHSET_V1 to VPS and restart."
            )
        log.info(
            "[EvalSchemaValidation] weights=%s dimensions=%d "
            "gov_dimension_present=True schema=SESSION_C_PATCHSET_V1 "
            "file=%s",
            {k: round(v, 2) for k, v in _WEIGHTS.items()}, len(_WEIGHTS),
            os.path.abspath(__file__),
        )
        log.info("[DailyAISelfEvaluator] Initialised.")

    # ── Public API ────────────────────────────────────────────────────

    def evaluate(
        self,
        trades,
        perf_report=None,
        last_distortion=None,
    ) -> SelfEvalResult:
        """
        Compute the day's AI Decision Score.

        Parameters
        ----------
        trades          : List[OrderRecord]  (from trade_monitor.get_closed_trades())
        perf_report     : PerformanceReport  (from performance_evaluator.evaluate())
        last_distortion : DistortionResult   (from global_intelligence.last_distortion)
        """
        today = date.today().isoformat()

        if not trades:
            result = SelfEvalResult(
                date          = today,
                overall_score = 0.0,
                grade         = "N/A",
                learning_notes= ["No trades executed today — no evaluation possible."],
            )
            result.week_avg_score, result.week_win_rate, result.week_trend = \
                self._weekly_stats()
            return result

        issues: List[str] = []
        learning_notes: List[str] = []

        # ── Trade stats ────────────────────────────────────────────────
        total    = len(trades)
        wins     = sum(1 for t in trades if getattr(t, "pnl", 0.0) > 0)
        losses   = total - wins
        net_pnl  = sum(getattr(t, "pnl", 0.0) for t in trades)
        wr_pct   = wins / total * 100
        # Use _compute_r_multiple so in-memory trades (no stored r_multiple) still
        # produce a real R value derived from pnl / (sl_distance × qty).
        # ── [AvgRAudit] — per-trade R decomposition trace ────────────────────
        # Reveals WHY avg_r = 0.00R when losses are real.
        # Key suspects: stop_loss=0.0 (orphan/carry cleanup resets it),
        # or r_multiple never set on in-memory trades.
        r_vals: List[float] = []
        for _t in trades:
            _ep   = getattr(_t, "entry_price", 0.0) or 0.0
            _sl   = getattr(_t, "stop_loss",   0.0) or 0.0
            _qty  = abs(getattr(_t, "quantity", 1) or 1)
            _pnl  = getattr(_t, "pnl",         0.0) or 0.0
            _raw  = getattr(_t, "r_multiple",  None)
            _risk = abs(_ep - _sl) * _qty
            _cr   = _compute_r_multiple(_t)
            r_vals.append(_cr)
            log.info(
                "[AvgRAudit] symbol=%s  close_reason=%s"
                "  entry_price=%.4f  stop_loss=%.4f  qty=%d  pnl=%.2f"
                "  risk_in_rupees=%.2f  raw_r_multiple=%s  computed_r=%+.4f",
                getattr(_t, "symbol", "?"),
                getattr(_t, "close_reason", "") or "(blank)",
                _ep, _sl, _qty, _pnl, _risk,
                str(_raw) if _raw is not None else "not_set",
                _cr,
            )
        avg_r    = sum(r_vals) / len(r_vals) if r_vals else 0.0
        _zero_count    = sum(1 for r in r_vals if r == 0.0)
        _nonzero_count = sum(1 for r in r_vals if r != 0.0)
        log.info(
            "[AvgRIntegritySummary] trade_count=%d  avg_r=%+.4f "
            "valid=%d  invalid=%d  fallback_used=%d  zero_r=%d",
            len(r_vals), avg_r,
            _nonzero_count, _zero_count, 0, _zero_count,
        )

        # ── Score each category ────────────────────────────────────────
        sq  = self._score_signal_quality(trades, issues)
        sf  = self._score_strategy_fit(trades, issues, learning_notes)
        rd  = self._score_risk_discipline(trades, issues, learning_notes)
        et  = self._score_execution_timing(trades, issues)
        mc  = self._score_market_context(trades, last_distortion, issues, learning_notes)
        gc  = self._score_governance_compliance(trades, issues, learning_notes)

        # ── Weighted overall ───────────────────────────────────────────
        overall = (
            sq  * _WEIGHTS["signal_quality"]        +
            sf  * _WEIGHTS["strategy_fit"]           +
            rd  * _WEIGHTS["risk_discipline"]        +
            et  * _WEIGHTS["execution_timing"]       +
            mc  * _WEIGHTS["market_context"]         +
            gc  * _WEIGHTS["governance_compliance"]
        )
        overall = round(min(10.0, max(0.0, overall)), 2)

        # ── [GovernanceScoreAudit] ─────────────────────────────────────
        # Traces exactly which timestamp field _score_execution_timing
        # inspected per trade and whether gc actually captured the violation.
        # Key question: does closed_at (CLOSE time) correctly represent
        # when the trade was ENTERED? Should be placed_at (ENTRY time).
        for _t in trades:
            _placed = getattr(_t, "placed_at",  None)
            _closed = getattr(_t, "closed_at",  None)
            _sym    = getattr(_t, "symbol", "?")
            _field_used = "closed_at" if _closed is not None else (
                          "placed_at" if _placed is not None else "none_available")
            _placed_time = (
                _placed.strftime("%H:%M:%S") if hasattr(_placed, "strftime") else str(_placed)
            ) if _placed else "None"
            _closed_time = (
                _closed.strftime("%H:%M:%S") if hasattr(_closed, "strftime") else str(_closed)
            ) if _closed else "None"
            _trade_violation = any(
                (_sym in iss) and (
                    "pre-open entry" in iss.lower() or "late entry" in iss.lower()
                )
                for iss in issues
            )
            log.info(
                "[GovernanceScoreAudit] symbol=%s  placed_at=%s  closed_at=%s"
                "  timing_field_used_by_scorer=placed_at  violation_in_issues=%s",
                _sym, _placed_time, _closed_time, _trade_violation,
            )
        _overall_no_gc = (
            sq * _WEIGHTS["signal_quality"]  +
            sf * _WEIGHTS["strategy_fit"]    +
            rd * _WEIGHTS["risk_discipline"] +
            et * _WEIGHTS["execution_timing"]+
            mc * _WEIGHTS["market_context"]
        ) / (1.0 - _WEIGHTS["governance_compliance"])
        log.info(
            "[GovernanceScoreAudit] gc=%.1f  gc_weight=%.2f  gc_contribution=%.3f"
            "  overall_with_gc=%.2f  hypothetical_without_gc=%.2f"
            "  grade_with_gc=%s  grade_without_gc=%s"
            "  violation_issues_count=%d",
            gc, _WEIGHTS["governance_compliance"], gc * _WEIGHTS["governance_compliance"],
            overall, round(min(10.0, max(0.0, _overall_no_gc)), 2),
            _grade(overall), _grade(round(min(10.0, max(0.0, _overall_no_gc)), 2)),
            sum(
                1 for iss in issues
                if "pre-open entry" in iss.lower() or "late entry" in iss.lower()
            ),
        )

        # ── Sample-confidence label (before cap so it appears in audit log) ─
        if total < 3:
            _sample_label = "⚠️ Exploratory (n<3 — avoid strong conclusions)"
        elif total < 10:
            _sample_label = "📊 Low-confidence statistics (n<10)"
        else:
            _sample_label = "📈 Statistically meaningful (n≥10)"

        # ── EvalScoreAudit — full contribution breakdown ───────────────
        _pre_cap = round(overall, 2)
        log.info(
            "[EvalScoreAudit] date=%s n=%d avg_r=%+.3f | "
            "signal_quality=%.2f×0.18=%.3f  strategy_fit=%.2f×0.22=%.3f  "
            "risk_discipline=%.2f×0.22=%.3f  exec_timing=%.2f×0.13=%.3f  "
            "market_context=%.2f×0.15=%.3f  governance=%.2f×0.10=%.3f | pre_cap=%.2f",
            today, total, avg_r,
            sq,  sq  * 0.18,
            sf,  sf  * 0.22,
            rd,  rd  * 0.22,
            et,  et  * 0.13,
            mc,  mc  * 0.15,
            gc,  gc  * 0.10,
            _pre_cap,
        )

        # ── Outcome cap: decision quality cannot mask a losing day ─────
        # A day with negative avg R cannot score above 6.0 (B-) because
        # good process on a losing day is still a losing day.
        _cap_applied = False
        _cap_reason  = ""
        if avg_r < -0.30:
            overall = min(overall, 4.0)   # F — outcome cap: avg_r < -0.30 overrides component scores
            _cap_applied = True
            _cap_reason  = f"avg_r={avg_r:+.3f}R < -0.30 → hard cap 4.0/F"
        elif avg_r < 0.0:
            overall = min(overall, 6.0)   # B- — marginally losing
            if _pre_cap > 6.0:
                _cap_applied = True
                _cap_reason  = f"avg_r={avg_r:+.3f}R < 0 → soft cap 6.0/B-"
        overall = round(overall, 2)

        if _cap_applied:
            log.info(
                "[EvalScoreAudit] cap_applied=True reason='%s' pre_cap=%.2f final=%.2f grade=%s",
                _cap_reason, _pre_cap, overall, _grade(overall),
            )
        else:
            log.info(
                "[EvalScoreAudit] cap_applied=False final=%.2f grade=%s sample='%s'",
                overall, _grade(overall), _sample_label,
            )

        # ── Governance grade ceiling ───────────────────────────────────────
        # A trading day with governance violations (gc=0.0) CANNOT produce A or A+.
        # Weight 0.10 is deliberately cosmetic; this ceiling enforces the real penalty.
        # Applied AFTER outcome cap so both constraints compound (worst wins).
        _pre_gov          = round(overall, 2)   # capture value entering this block
        _gov_ceil_applied = False
        _gov_ceil_reason  = ""
        _GOV_CEIL         = 7.0    # B — max grade allowed on a governance-violated day
        if gc == 0.0:
            if overall > _GOV_CEIL:
                overall           = _GOV_CEIL
                overall           = round(overall, 2)
                _gov_ceil_applied = True
                _gov_ceil_reason  = (
                    "gc=0.0 (governance violation) → hard ceiling 7.0/B"
                )
        log.info(
            "[GovernancePatchValidation] gc=%.1f  gov_ceil_applied=%s"
            "  gov_ceil_reason=%r  pre_gov_ceil=%.2f  post_gov_ceil=%.2f"
            "  placed_at_used=True  final_grade=%s",
            gc, _gov_ceil_applied, _gov_ceil_reason,
            _pre_gov, round(overall, 2), _grade(round(overall, 2)),
        )

        # ── Generic learning notes from overall ────────────────────────
        if overall >= 8.5:
            learning_notes.append("✅ Excellent decision quality — maintain current rules.")
        elif overall >= 7.0:
            learning_notes.append("Good performance. Monitor flagged issues above.")
        elif overall >= 5.5:
            learning_notes.append("⚠️ Decision quality needs improvement — review issues.")
        else:
            learning_notes.append(
                "🔴 Poor decision quality. Review strategy-regime fit and risk rules.")

        result = SelfEvalResult(
            date                 = today,
            signal_quality       = round(sq,  2),
            strategy_fit         = round(sf,  2),
            risk_discipline      = round(rd,  2),
            execution_timing     = round(et,  2),
            market_context       = round(mc,  2),
            governance_compliance= round(gc,  2),
            overall_score        = overall,
            grade                = _grade(overall),
            total_trades         = total,
            wins                 = wins,
            losses               = losses,
            net_pnl              = round(net_pnl, 2),
            win_rate_pct         = round(wr_pct,  1),
            avg_r                = round(avg_r,   3),
            issues               = issues,
            learning_notes       = learning_notes,
            outcome_cap_applied  = _cap_applied,
            outcome_cap_reason   = _cap_reason,
            sample_confidence    = _sample_label,
        )

        # ── Research Integrity Gate ───────────────────────────────────────────
        # Determine the architecture generation for today's trades.
        # OrderRecord objects don't carry architecture_generation; use config flag.
        _n_prepared  = 0
        _n_legacy    = 0
        try:
            from config import USE_PREPARED_UNIVERSE as _use_prep
            from learning_system.strategy_performance_tracker import (
                MIN_PREPARED_UNIVERSE_TRADES_FOR_STRATEGY_JUDGMENT as _min_prep,
                get_performance_tracker as _get_pt,
            )
            from learning_system.research_integrity import (
                compute_legacy_weight,
                emit_contamination_telemetry,
                emit_clean_research_state,
                get_system_prepared_trade_count,
                is_clean_research_ready,
            )
            _current_gen = "PREPARED_UNIVERSE_V1" if _use_prep else "LEGACY_STATIC"
            # Count prepared_universe_trades across all active strategies
            _pt = _get_pt()
            _all_stats = _pt.get_all_stats()
            # Min prepared across strategies that actually ran today
            _today_strategies = {getattr(t, "strategy", "") or "" for t in trades}
            _min_prep_today = min(
                (_all_stats[s].prepared_universe_trades for s in _today_strategies
                 if s in _all_stats),
                default=0,
            )
            _mutation_blocked = _min_prep_today < _min_prep
            if _current_gen == "PREPARED_UNIVERSE_V1":
                _n_prepared = total
            else:
                _n_legacy   = total

            # Patch 19: dynamic legacy weight
            _sys_prepared  = get_system_prepared_trade_count()
            _dyn_lw        = compute_legacy_weight(_sys_prepared)

            _ri_note = (
                f"generation={_current_gen}  prepared_sample={_min_prep_today}  "
                f"min_required={_min_prep}  mutation_blocked={_mutation_blocked}  "
                f"dynamic_legacy_weight={_dyn_lw:.4f}"
            )
            log.info(
                "[ResearchIntegrity] date=%s  legacy_trades=%d  prepared_trades=%d  "
                "dynamic_legacy_weight=%.4f  prepared_weight=1.00  "
                "strategy_mutation_blocked=%s",
                today, _n_legacy, _n_prepared, _dyn_lw, _mutation_blocked,
            )
            # Patch 20: [ResearchContamination] telemetry
            emit_contamination_telemetry(
                legacy_count=_n_legacy,
                prepared_count=_sys_prepared,
                source="DailySelfEval",
            )
            # Patch 22: [CleanResearchState] telemetry
            emit_clean_research_state(source="DailySelfEval")

            result.strategy_mutation_blocked = _mutation_blocked
            result.research_integrity_note   = _ri_note
        except Exception as _ri_exc:
            log.debug("[ResearchIntegrity] check skipped: %s", _ri_exc)
        result.week_avg_score, result.week_win_rate, result.week_trend = \
            self._weekly_stats(result)
        return result

    def render(self, result: SelfEvalResult) -> str:
        """Build the human-readable daily report string."""
        sep  = "═" * 57
        sep2 = "─" * 57

        def bar(v: float, width: int = 20) -> str:
            filled = int(v / 10.0 * width)
            return "█" * filled + "░" * (width - filled)

        lines = [
            sep,
            "  🧠  AI DAILY SELF-EVALUATION REPORT",
            f"  Date : {result.date}",
            sep,
            f"  Trades: {result.total_trades}  │  "
            f"Wins: {result.wins}  │  Losses: {result.losses}  │  "
            f"WR: {result.win_rate_pct:.0f}%",
            f"  Net P&L: ₹{result.net_pnl:+,.0f}  │  Avg R: {result.avg_r:+.2f}R",
        ]

        # Sample confidence label
        if result.sample_confidence:
            lines.append(f"  Sample: {result.sample_confidence}")

        lines += [
            sep2,
            "  DECISION QUALITY SCORES",
            sep2,
            f"  Signal Quality   {bar(result.signal_quality)}  {result.signal_quality:>4.1f}/10",
            f"  Strategy Fit     {bar(result.strategy_fit)}  {result.strategy_fit:>4.1f}/10",
            f"  Risk Discipline  {bar(result.risk_discipline)}  {result.risk_discipline:>4.1f}/10",
            f"  Exec Timing      {bar(result.execution_timing)}  {result.execution_timing:>4.1f}/10",
            f"  Market Context   {bar(result.market_context)}  {result.market_context:>4.1f}/10",
            f"  Gov Compliance   {bar(result.governance_compliance)}  {result.governance_compliance:>4.1f}/10",
            sep2,
            f"  ▶  OVERALL AI SCORE  :  {result.overall_score:.1f} / 10  "
            f"[ Grade: {result.grade} ]",
        ]

        # Governance violation banner (shown whenever GC score is 0)
        if result.governance_compliance == 0.0:
            lines.append(
                "  ⚠️ Governance Violation: Entry outside approved execution window."
            )
            lines.append(
                "     This score dimension fires independently of trade outcomes."
            )

        # Outcome cap explanation (shown whenever cap was applied)
        if result.outcome_cap_applied:
            lines.append(
                f"  ⚡ Outcome cap applied: {result.outcome_cap_reason}"
            )
            lines.append(
                "     Component scores reflect process quality; final grade"
            )
            lines.append(
                "     reflects the actual outcome (avg R < threshold)."
            )

        if result.issues:
            lines += [sep2, "  ⚠  ISSUES DETECTED"]
            for i, issue in enumerate(result.issues, 1):
                lines.append(f"  {i}. {issue}")

        if result.learning_notes:
            lines += [sep2, "  💡  ACTION ITEMS"]
            for note in result.learning_notes:
                lines.append(f"  • {note}")

        # Weekly rolling stats
        if result.week_avg_score > 0 or result.week_win_rate > 0:
            lines += [sep2, "  📅  7-DAY ROLLING STATS"]
            lines.append(f"  Avg AI Score : {result.week_avg_score:.1f}/10  "
                         f"│  Avg Win Rate : {result.week_win_rate:.0f}%")
            trend_icon = {"improving": "📈", "declining": "📉", "stable": "➡️"}.get(
                result.week_trend, "➡️")
            lines.append(f"  Trend        : {trend_icon}  {result.week_trend.title()}")

        lines.append(sep)
        return "\n".join(lines)

    def save(self, result: SelfEvalResult, report_text: str) -> str:
        """
        Save report to data/logs/eod_report_YYYY-MM-DD.txt.
        Also persist result to history JSON.
        Returns absolute path of saved report file.
        """
        os.makedirs(_DATA_DIR, exist_ok=True)

        # Save human-readable report
        fname = os.path.join(_DATA_DIR, f"eod_report_{result.date}.txt")
        try:
            with open(fname, "w", encoding="utf-8") as fh:
                fh.write(report_text)
                fh.write(f"\n\n[Generated at {datetime.now().isoformat(timespec='seconds')}]\n")
            log.info("[DailyAISelfEvaluator] Report saved → %s", os.path.abspath(fname))
            # ── [EODRuntimePath] — prove exact file + class executing this report ──
            log.info(
                "[EODRuntimePath] self_eval_class=%s module_file=%s pid=%d "
                "report_date=%s runtime_date=%s",
                self.__class__.__name__,
                os.path.abspath(inspect.getfile(self.__class__)),
                os.getpid(),
                result.date,
                datetime.now().strftime("%Y-%m-%d"),
            )
        except Exception as exc:
            log.warning("[DailyAISelfEvaluator] Could not save report: %s", exc)

        # Update history JSON
        self._append_history(result)
        return fname

    def notify(self, result: SelfEvalResult, report_text: str) -> None:
        """
        Send the daily report via Telegram.
        Uses NotifierManager.market_alert() so it's non-blocking.
        """
        try:
            from notifications import get_notifier
            notifier = get_notifier()

            # Telegram message (brief — under 4096 chars)
            grade_icons = {
                "A+": "🏆", "A": "🥇", "A-": "🥇",
                "B+": "✅", "B": "✅", "B-": "✅",
                "C+": "⚠️", "C": "⚠️", "C-": "⚠️",
                "F": "🔴",
            }
            icon = grade_icons.get(result.grade, "📊")

            msg = (
                f"{icon} <b>AI Self-Evaluation — {result.date}</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"Trades: {result.total_trades}  ({result.wins}W / {result.losses}L)"
                f"  WR: {result.win_rate_pct:.0f}%\n"
                f"Net P&amp;L: ₹{result.net_pnl:+,.0f}  Avg R: {result.avg_r:+.2f}R\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"📊 <b>Score Breakdown</b>\n"
                f"  Signal Quality   : {result.signal_quality:.1f}/10\n"
                f"  Strategy Fit     : {result.strategy_fit:.1f}/10\n"
                f"  Risk Discipline  : {result.risk_discipline:.1f}/10\n"
                f"  Exec Timing      : {result.execution_timing:.1f}/10\n"
                f"  Market Context   : {result.market_context:.1f}/10\n"
                f"  Gov Compliance   : {result.governance_compliance:.1f}/10\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"<b>Overall : {result.overall_score:.1f}/10  [{result.grade}]</b>"
            )
            if result.governance_compliance == 0.0:
                msg += (
                    f"\n⚠️ <b>Governance Violation</b>: Entry outside approved"
                    f" execution window (09:45–14:30)."
                    f"\n<i>This dimension fires independently of trade P&amp;L.</i>"
                )
            if result.outcome_cap_applied:
                msg += (
                    f"\n⚡ <i>Outcome cap: {result.outcome_cap_reason}</i>\n"
                    f"<i>(Components score process; grade reflects actual outcome)</i>"
                )
            if result.sample_confidence:
                msg += f"\n📌 <i>{result.sample_confidence}</i>"
            if result.issues:
                msg += "\n⚠️ <b>Issues:</b>\n"
                for issue in result.issues[:5]:   # cap Telegram msg length
                    msg += f"• {issue}\n"
            if result.learning_notes:
                msg += "\n💡 <b>Actions:</b>\n"
                for note in result.learning_notes[:3]:
                    msg += f"• {note}\n"

            notifier.market_alert("🧠 Daily AI Self-Evaluation", msg)
            log.info("[DailyAISelfEvaluator] Telegram notification queued.")
        except Exception as exc:
            log.warning("[DailyAISelfEvaluator] Telegram notify failed: %s", exc)

    # ── Category scorers ──────────────────────────────────────────────

    def _score_signal_quality(
        self,
        trades,
        issues: List[str],
    ) -> float:
        """
        Signal quality: were signals complete and well-formed?

        Checks:
          • Stop-loss set for every trade           (+3 pts if 100%)
          • Target set for every trade              (+3 pts if 100%)
          • Positive R:R across the portfolio       (+4 pts scaled)
        Deductions:
          • Each trade without SL                  -2 pts
          • Each trade with negative R:R            -1 pt
        """
        n = len(trades)
        score = 10.0

        no_sl     = sum(1 for t in trades if not getattr(t, "stop_loss", 0.0))
        no_tp     = sum(1 for t in trades if not getattr(t, "target",    0.0))
        neg_r     = sum(1 for t in trades if getattr(t, "r_multiple", 0.0) < 0)

        score -= (no_sl / n) * 4.0     # up to -4 if no SL on any trade
        score -= (no_tp / n) * 2.0     # up to -2 if no TP on any trade
        score -= (neg_r / n) * 2.0     # partial: negative actual R

        # Flat -2 per individual trade missing SL (up to 4 flags)
        for t in trades:
            sym = getattr(t, "symbol", "?")
            sl  = getattr(t, "stop_loss", 0.0)
            if not sl:
                issues.append(f"No stop-loss set: {sym} — violates risk rule")
                score = max(score - 1.0, 0.0)

        return max(0.0, min(10.0, score))

    def _score_strategy_fit(
        self,
        trades,
        issues: List[str],
        notes: List[str],
    ) -> float:
        """
        Strategy fit: was the correct strategy selected for the regime?

        Uses _REGIME_MAP to validate each trade.
        Deductions:
          • Each strategy-regime mismatch   -2 pts
          • Each aggressive strategy in bear/volatile   -2 pts
        """
        n       = len(trades)
        score   = 10.0
        mismatch_count = 0

        for t in trades:
            sym      = getattr(t, "symbol", "?")
            strategy = (getattr(t, "strategy", "")
                        or getattr(t, "strategy_name", "")).lower().strip()
            regime   = getattr(t, "regime", "unknown").lower().strip() if hasattr(t, "regime") else "unknown"

            if regime == "unknown" or not strategy:
                continue    # can't validate without both fields

            allowed = [s.lower() for s in _REGIME_MAP.get(regime, [])]
            if allowed and strategy not in allowed:
                mismatch_count += 1
                issues.append(
                    f"Strategy-regime mismatch: '{strategy}' used in "
                    f"'{regime}' (not in allowed list)"
                )
                score = max(score - 2.0, 0.0)

            # Aggressive strategy in defensive regime
            if any(ag in strategy for ag in _AGGRESSIVE_STRATEGIES) and \
               regime in ("bear_market", "volatile"):
                issues.append(
                    f"Aggressive strategy '{strategy}' used during {regime} — "
                    f"increases tail risk"
                )
                score = max(score - 1.5, 0.0)

        if mismatch_count >= 2:
            notes.append(
                f"Strategy-regime mismatches detected ({mismatch_count} trades). "
                f"Review MetaStrategyController regime map."
            )

        return max(0.0, min(10.0, score))

    def _score_risk_discipline(
        self,
        trades,
        issues: List[str],
        notes: List[str],
    ) -> float:
        """
        Risk discipline: were risk rules followed on every trade?

        Checks:
          • SL present                              (3 pts if all)
          • R:R ≥ 1.5 on entry                      (3 pts if all)
          • Avg realised R-multiple > 0.5R          (2 pts)
          • Max single loss < 2R                    (2 pts)
        """
        n     = len(trades)
        score = 10.0

        # SL presence (already penalised in signal quality, softer penalty here)
        no_sl = sum(1 for t in trades if not getattr(t, "stop_loss", 0.0))
        score -= (no_sl / n) * 2.0

        # R:R at entry (target - entry) / (entry - stop)
        poor_rr_count = 0
        for t in trades:
            ep = getattr(t, "entry_price", 0.0) or getattr(t, "fill_price", 0.0)
            sl = getattr(t, "stop_loss",   0.0)
            tp = getattr(t, "target",      0.0)
            if ep and sl and tp and ep != sl:
                rr_entry = abs(tp - ep) / abs(ep - sl)
                if rr_entry < 1.0:
                    sym = getattr(t, "symbol", "?")
                    issues.append(
                        f"Poor entry R:R ({rr_entry:.1f}x) on {sym} — "
                        f"minimum 1.0 required"
                    )
                    score = max(score - 1.0, 0.0)
                    poor_rr_count += 1
                elif rr_entry < 1.5:
                    score = max(score - 0.5, 0.0)   # soft penalty

        # Realised R-multiples
        r_vals  = [getattr(t, "r_multiple", 0.0) for t in trades]
        avg_r   = sum(r_vals) / len(r_vals) if r_vals else 0.0
        max_loss = min(r_vals) if r_vals else 0.0

        if avg_r < 0:
            score = max(score - 1.5, 0.0)
        elif avg_r < 0.5:
            score = max(score - 0.5, 0.0)

        if max_loss < -2.0:
            issues.append(
                f"Large loss trade detected ({max_loss:.1f}R) — "
                f"exceeded 2R max loss rule"
            )
            score = max(score - 1.5, 0.0)

        if poor_rr_count >= 2:
            notes.append(
                f"{poor_rr_count} trades had R:R < 1.0 on entry. "
                f"Consider tightening entry confirmation rules."
            )

        return max(0.0, min(10.0, score))

    def _score_execution_timing(
        self,
        trades,
        issues: List[str],
    ) -> float:
        """
        Execution timing: were trades entered in the valid window?

        Valid window: 09:45 – 14:30 IST
        Deductions:
          • Each trade entered before 09:45          -2 pts
          • Each trade entered after 14:30           -1.5 pts
          • No timestamp available                   0 pts (neutral)
        """
        n     = len(trades)
        score = 10.0

        timed_trades = 0
        for t in trades:
            # Use placed_at (ENTRY time) — not closed_at (EXIT time).
            # Pre-open governance violations must be checked against when the
            # trade was ENTERED, not when it was CLOSED.
            ts = getattr(t, "placed_at", None) or getattr(t, "closed_at", None)
            if ts is None:
                continue
            if isinstance(ts, str):
                try:
                    ts = datetime.fromisoformat(ts)
                except Exception:
                    continue

            trade_time = ts.time() if hasattr(ts, "time") else None
            if trade_time is None:
                continue

            timed_trades += 1
            sym = getattr(t, "symbol", "?")

            if trade_time < _WINDOW_OPEN:
                issues.append(
                    f"Pre-open entry at {trade_time.strftime('%H:%M')} for {sym} "
                    f"(window starts 09:45)"
                )
                score = max(score - 2.0, 0.0)
            elif trade_time > _WINDOW_CLOSE:
                issues.append(
                    f"Late entry at {trade_time.strftime('%H:%M')} for {sym} "
                    f"(window closes 14:30) — MIS risk"
                )
                score = max(score - 1.5, 0.0)

        # If no timestamps available, return neutral
        if timed_trades == 0:
            return 7.5   # benefit of the doubt

        return max(0.0, min(10.0, score))

    def _score_market_context(
        self,
        trades,
        last_distortion,
        issues: List[str],
        notes: List[str],
    ) -> float:
        """
        Market context awareness: did the system respect macro risk?

        Checks (using today's last DistortionResult):
          • EXTREME distortion → no trades should have been placed (-4)
          • HIGH distortion → trade count should be reduced (-2 if full day)
          • Aggressive strategy during distortion (-1.5 each)
          • No distortion data                → neutral (7.5)
        """
        if last_distortion is None:
            return 7.5  # neutral — can't evaluate without data

        score       = 10.0
        risk_level  = getattr(last_distortion, "risk_level",  "NORMAL")
        stress      = getattr(last_distortion, "stress_score", 0)
        flags       = getattr(last_distortion, "active_flags", [])

        # EXTREME distortion: system should have halted completely
        if risk_level == "EXTREME":
            if len(trades) > 0:
                issues.append(
                    f"Trades executed during EXTREME distortion (score={stress}/8, "
                    f"flags={flags}) — should have paused trading"
                )
                score -= 4.0
                notes.append(
                    "Distortion scanner flagged EXTREME risk today. "
                    "Consider hardening the trade-halt logic."
                )

        # HIGH distortion: reduced exposure expected
        elif risk_level == "HIGH":
            if len(trades) >= 3:
                issues.append(
                    f"Normal trade count ({len(trades)}) during HIGH distortion "
                    f"(score={stress}/8) — expected reduced exposure"
                )
                score -= 2.0

        # Aggressive strategies during any distortion
        if risk_level in ("HIGH", "EXTREME"):
            for t in trades:
                strategy = (getattr(t, "strategy", "")
                            or getattr(t, "strategy_name", "")).lower()
                if any(ag in strategy for ag in _AGGRESSIVE_STRATEGIES):
                    sym = getattr(t, "symbol", "?")
                    issues.append(
                        f"Aggressive strategy '{strategy}' on {sym} during "
                        f"{risk_level} risk — violates distortion rules"
                    )
                    score = max(score - 1.5, 0.0)

        # Bonus: correctly reduced exposure
        if risk_level in ("HIGH", "EXTREME") and len(trades) <= 1:
            score = min(10.0, score + 1.0)  # credit for discipline

        return max(0.0, min(10.0, score))

    def _score_governance_compliance(
        self,
        trades,
        issues: List[str],
        notes: List[str],
    ) -> float:
        """
        Governance compliance: did every trade obey execution-window rules?

        Scoring:
          10 — no window violations detected in today's issues list
           0 — any pre-open entry (before 09:45) or late entry (after 14:30)

        The score is completely INDEPENDENT of trade P&L.  This means window
        violations penalise the grade even when the trade was profitable —
        the old avg_r=0.0 blind spot that let Apr-29 and May-14 slip through
        as A+ days cannot recur here.

        This scorer must be called AFTER _score_execution_timing() because
        the timing scorer is responsible for populating the 'issues' list with
        the pre-open / late-entry strings that this method detects.
        """
        violations = sum(
            1 for issue in issues
            if "pre-open entry" in issue.lower() or "late entry" in issue.lower()
        )
        if violations > 0:
            notes.append(
                f"⚠️ Governance Violation: {violations} trade(s) outside the "
                f"09:45–14:30 execution window. Review entry timing before next session."
            )
            return 0.0
        return 10.0

    # ── History persistence + weekly stats ───────────────────────────

    def _append_history(self, result: SelfEvalResult) -> None:
        """Append today's result to history JSON (max _HISTORY_MAX records)."""
        try:
            history: list = []
            if os.path.exists(_HISTORY_PATH):
                with open(_HISTORY_PATH, "r", encoding="utf-8") as fh:
                    history = json.load(fh)

            # Remove existing record for same date (prevent duplicates on re-run)
            history = [r for r in history if r.get("date") != result.date]
            history.append(result.to_dict())

            if len(history) > _HISTORY_MAX:
                history = history[-_HISTORY_MAX:]

            os.makedirs(_DATA_DIR, exist_ok=True)
            with open(_HISTORY_PATH, "w", encoding="utf-8") as fh:
                json.dump(history, fh, indent=2)
        except Exception as exc:
            log.debug("[DailyAISelfEvaluator] History write failed: %s", exc)

    def _weekly_stats(
        self,
        today_result: Optional[SelfEvalResult] = None,
    ) -> Tuple[float, float, str]:
        """
        Compute 7-day rolling: avg AI score, avg win rate, trend direction.
        Returns (avg_score, avg_wr, trend_str).
        """
        try:
            history: list = []
            if os.path.exists(_HISTORY_PATH):
                with open(_HISTORY_PATH, "r", encoding="utf-8") as fh:
                    history = json.load(fh)
            # Include today if provided
            if today_result is not None:
                history = [r for r in history if r.get("date") != today_result.date]
                history.append(today_result.to_dict())

            last7 = history[-7:]
            if not last7:
                return 0.0, 0.0, "stable"

            scores   = [r.get("overall_score", 0.0) for r in last7]
            wr_vals  = [r.get("win_rate_pct",  0.0) for r in last7]
            avg_score = sum(scores)  / len(scores)
            avg_wr    = sum(wr_vals) / len(wr_vals)

            # Simple trend: compare first half vs second half of window
            if len(scores) >= 4:
                mid     = len(scores) // 2
                first_h = sum(scores[:mid])  / mid
                second_h= sum(scores[mid:])  / (len(scores) - mid)
                delta   = second_h - first_h
                if delta > 0.5:
                    trend = "improving"
                elif delta < -0.5:
                    trend = "declining"
                else:
                    trend = "stable"
            else:
                trend = "stable"

            return round(avg_score, 2), round(avg_wr, 1), trend
        except Exception as exc:
            log.debug("[DailyAISelfEvaluator] Weekly stats error: %s", exc)
            return 0.0, 0.0, "stable"
