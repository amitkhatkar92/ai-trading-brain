"""
Performance Evaluation Framework — Top-Level Coordinator
=========================================================
Answers the critical question: "Is the AI brain actually making money?"

Aggregates all sub-frameworks:
  • DrawdownAnalyzer           → equity curve health
  • RegimePerformanceTracker   → which regimes generate alpha
  • StrategyAttributionEngine  → which strategies contribute
  • WalkForwardTester          → is the edge real, not curve-fitted

Called during the end-of-day learning cycle.

Produces a PerformanceReport with:
  • Overall return metrics (daily, MTD, total)
  • Sharpe, Sortino, Calmar ratios
  • Max drawdown analysis
  • Regime breakdown
  • Strategy attribution
  • Walk-forward validation result
  • Overall grade: A / B / C / D / F
"""

from __future__ import annotations
import math
import statistics
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from utils import get_logger
from models.trade_expectancy import ExpectancyCalculator
from .drawdown_analyzer         import DrawdownAnalyzer, DrawdownReport
from .regime_performance_tracker import RegimePerformanceTracker
from .strategy_attribution      import StrategyAttributionEngine
from .walk_forward_tester       import WalkForwardTester, WalkForwardReport

log = get_logger(__name__)


@dataclass
class PerformanceRecord:
    """Records a single completed trade for evaluation purposes."""
    strategy:   str
    regime:     str
    pnl:        float
    r_multiple: float
    won:        bool
    timestamp:  datetime = field(default_factory=datetime.now)


@dataclass
class PerformanceReport:
    timestamp:           datetime
    total_trades:        int    = 0
    total_pnl:           float  = 0.0
    total_return_pct:    float  = 0.0
    win_rate_pct:        float  = 0.0
    sharpe_ratio:        float  = 0.0
    sortino_ratio:       float  = 0.0
    profit_factor:       float  = 0.0
    expectancy:          float  = 0.0
    drawdown:            Optional[DrawdownReport] = None
    regime_breakdown:    dict   = field(default_factory=dict)
    strategy_breakdown:  dict   = field(default_factory=dict)
    walk_forward:        Optional[WalkForwardReport] = None
    grade:               str    = "N/A"
    grade_notes:         list   = field(default_factory=list)

    def summary(self) -> str:
        return (
            f"[PerfEvaluator] Grade={self.grade} | "
            f"Trades={self.total_trades} | "
            f"Return={self.total_return_pct:+.2f}% | "
            f"WinRate={self.win_rate_pct:.1f}% | "
            f"Sharpe={self.sharpe_ratio:.2f} | "
            f"MaxDD={self.drawdown.max_drawdown_pct:.1f}%"
            if self.drawdown else
            f"[PerfEvaluator] Grade={self.grade} | "
            f"Trades={self.total_trades} | "
            f"Return={self.total_return_pct:+.2f}%"
        )


class PerformanceEvaluator:
    """
    End-of-cycle / end-of-day performance evaluation framework.

    Usage::
        evaluator = PerformanceEvaluator(capital=1_000_000)

        # After each trade closes:
        evaluator.record_trade(
            strategy="Iron_Condor_Range",
            regime="range_market",
            pnl=2800, r_multiple=1.4, won=True
        )

        # At end of day:
        report = evaluator.evaluate()
        evaluator.print_full_report(report)
    """

    def __init__(self, capital: float = 1_000_000) -> None:
        self._capital       = capital
        self._records:      list[PerformanceRecord] = []
        self._equity_curve: list[float] = [capital]

        self._dd_analyzer   = DrawdownAnalyzer()
        self._regime_tracker= RegimePerformanceTracker()
        self._attribution   = StrategyAttributionEngine()
        self._wf_tester     = WalkForwardTester()

        log.info("[PerformanceEvaluator] Initialised. Capital=₹%.0f", capital)

    # ── Public API ────────────────────────────────────────────────────────
    def record_trade(self, strategy: str, regime: str,
                     pnl: float, r_multiple: float, won: bool) -> None:
        """Record a completed trade for evaluation."""
        record = PerformanceRecord(
            strategy=strategy, regime=regime,
            pnl=pnl, r_multiple=r_multiple, won=won,
        )
        self._records.append(record)

        # Update equity curve
        last_equity = self._equity_curve[-1]
        self._equity_curve.append(last_equity + pnl)

        # Feed sub-frameworks
        self._regime_tracker.record(regime, pnl, r_multiple, won, strategy)
        self._attribution.record(strategy, pnl, won)

    def evaluate(self) -> PerformanceReport:
        """Run all evaluation frameworks and return a PerformanceReport."""
        n = len(self._records)
        if n == 0:
            log.info("[PerformanceEvaluator] No trades to evaluate yet.")
            return PerformanceReport(timestamp=datetime.now())

        pnls        = [r.pnl for r in self._records]
        total_pnl   = sum(pnls)
        wins        = sum(1 for r in self._records if r.won)
        losses      = n - wins
        win_rate    = wins / n * 100
        gross_profit= sum(p for p in pnls if p > 0)
        gross_loss  = sum(p for p in pnls if p < 0)
        pf          = abs(gross_profit / gross_loss) if gross_loss != 0 else float("inf")

        # Returns
        total_ret_pct = total_pnl / self._capital * 100
        daily_rets    = [p / self._capital for p in pnls]

        # Sharpe / Sortino (using per-trade as proxy for daily)
        sharpe  = 0.0
        sortino = 0.0
        if len(daily_rets) > 1:
            mu    = statistics.mean(daily_rets)
            sigma = statistics.stdev(daily_rets)
            if sigma > 0:
                sharpe = (mu / sigma) * math.sqrt(252)
            # Sortino uses downside deviation only
            neg_rets    = [r for r in daily_rets if r < 0]
            down_dev    = math.sqrt(sum(r**2 for r in neg_rets) / n) if neg_rets else 1e-9
            sortino = (mu / down_dev) * math.sqrt(252) if down_dev > 0 else 0.0

        # Expectancy
        avg_win  = statistics.mean([p for p in pnls if p > 0]) if wins   else 0.0
        avg_loss = statistics.mean([p for p in pnls if p < 0]) if losses else 0.0
        expectancy = (wins/n * avg_win) - (losses/n * abs(avg_loss))

        # Drawdown
        dd_report = self._dd_analyzer.analyse(
            self._equity_curve, annualised_return_pct=total_ret_pct
        )

        # Walk-forward
        wf_report   = self._wf_tester.run(pnls, capital=self._capital)

        # Grade
        grade, notes = self._compute_grade(
            total_ret_pct, win_rate, sharpe, dd_report.max_drawdown_pct,
            pf, wf_report.passed
        )

        report = PerformanceReport(
            timestamp          = datetime.now(),
            total_trades       = n,
            total_pnl          = round(total_pnl, 2),
            total_return_pct   = round(total_ret_pct, 3),
            win_rate_pct       = round(win_rate, 1),
            sharpe_ratio       = round(sharpe, 3),
            sortino_ratio      = round(sortino, 3),
            profit_factor      = round(pf, 3),
            expectancy         = round(expectancy, 2),
            drawdown           = dd_report,
            regime_breakdown   = self._regime_tracker.to_dict(),
            strategy_breakdown = self._attribution.to_dict(),
            walk_forward       = wf_report,
            grade              = grade,
            grade_notes        = notes,
        )
        log.info(report.summary())
        return report

    def print_full_report(self, report: PerformanceReport) -> None:
        border = "═" * 70
        log.info(border)
        log.info("  PERFORMANCE EVALUATION REPORT  |  %s",
                 report.timestamp.strftime("%Y-%m-%d %H:%M"))
        log.info("─" * 70)
        log.info("  Total Trades      : %d", report.total_trades)
        log.info("  Total P&L         : ₹%+,.0f", report.total_pnl)
        log.info("  Total Return      : %+.2f%%",  report.total_return_pct)
        log.info("  Win Rate          : %.1f%%",   report.win_rate_pct)
        log.info("  Profit Factor     : %.2f",     report.profit_factor)
        log.info("  Expectancy/Trade  : ₹%+,.0f",  report.expectancy)
        # Expectancy profile in R-multiples (the true profitability measure)
        wins_r  = [r.r_multiple for r in self._records if r.won  and r.r_multiple > 0]
        loss_r  = [r.r_multiple for r in self._records if not r.won]
        prof = ExpectancyCalculator.from_trades(wins_r, loss_r)
        if prof:
            log.info("  Expectancy (R)    : %s", prof.summary())
        log.info("  Sharpe Ratio      : %.3f",     report.sharpe_ratio)
        log.info("  Sortino Ratio     : %.3f",     report.sortino_ratio)
        if report.drawdown:
            log.info("  Max Drawdown      : %.1f%%",
                     report.drawdown.max_drawdown_pct)
            log.info("  Calmar Ratio      : %.3f",
                     report.drawdown.calmar_ratio)
            log.info("  Ulcer Index       : %.4f",
                     report.drawdown.ulcer_index)
        if report.walk_forward:
            log.info("  Walk-Forward      : %s (Pass=%.0f%%)",
                     "✅ PASSED" if report.walk_forward.passed else "❌ FAILED",
                     report.walk_forward.pass_rate_pct)
        log.info("─" * 70)
        log.info("  GRADE: %s", report.grade)
        for note in report.grade_notes:
            log.info("    %s", note)
        log.info(border)

        # Sub-reports
        self._regime_tracker.print_report()
        self._attribution.print_report()

    # ── Private ───────────────────────────────────────────────────────────
    @staticmethod
    def _compute_grade(
        ret_pct: float, win_rate: float, sharpe: float,
        max_dd: float,  pf: float,       wf_passed: bool,
    ) -> tuple[str, list[str]]:
        """
        Score-based grading:
          Each metric awards 0–2 points, max 12 pts.
          A=10+, B=8-9, C=6-7, D=4-5, F=<4
        """
        score = 0
        notes = []

        def check(condition: bool, pts: int, good: str, bad: str) -> None:
            nonlocal score
            score += pts if condition else 0
            notes.append(f"{'✅' if condition else '❌'} {good if condition else bad}")

        # ── Expectancy-first grading (not win-rate-first) ────────────────
        # A 40% win rate + 3R payoff beats a 70% win rate + 0.5R payoff.
        # The grade rewards: positive expectancy + controlled drawdown + fat winners.
        check(ret_pct > 10,   2, f"Return={ret_pct:+.1f}% (excellent)",   f"Return={ret_pct:+.1f}%")
        check(ret_pct > 0,    1, "", f"") if ret_pct <= 10 else None
        check(pf >= 1.5,      2, f"ProfitFactor={pf:.2f}≥1.5 (positive expectancy)",
                                 f"ProfitFactor={pf:.2f}<1.5 (negative expectancy)")
        check(pf >= 1.0,      1, "", "") if pf < 1.5 else None
        check(sharpe >= 1.5,  2, f"Sharpe={sharpe:.2f} (institutional)",  f"Sharpe={sharpe:.2f}<1.5")
        check(sharpe >= 1.0,  1, "", "") if sharpe < 1.5 else None
        check(max_dd < 10,    2, f"MaxDD={max_dd:.1f}%<10% (tight)",      f"MaxDD={max_dd:.1f}%≥10%")
        check(wf_passed,      2, "Walk-Forward PASSED",                    "Walk-Forward FAILED")
        # Win rate is informational — a note, not a gate
        wr_note = (f"WinRate={win_rate:.0f}%" +
                   (" ✅ (high acc)" if win_rate >= 55 else
                    " ✅ (asymmetric — low WR OK)" if win_rate >= 35 else
                    " ⚠️ (very low WR)"))
        notes.append(wr_note)

        notes = [n for n in notes if n.strip("✅❌ ")]
        score = min(score, 12)
        grade = "A" if score >= 10 else \
                "B" if score >= 8  else \
                "C" if score >= 6  else \
                "D" if score >= 4  else "F"
        return grade, notes
