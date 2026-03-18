"""
Validation Engine — Master Validation Report
=============================================
Aggregates all validation-stage results into a final verdict.

Pipeline stages and weights:
  Stage 1  — In-Sample / Out-of-Sample Backtest     (weight: 25%)
  Stage 2  — Walk-Forward Analysis                  (weight: 25%)
  Stage 3  — Cross-Market Validation                (weight: 15%)
  Stage 4  — Monte Carlo Simulation                 (weight: 15%)
  Stage 5  — Parameter Sensitivity Analysis         (weight: 10%)
  Stage 6  — Regime Robustness Test                 (weight: 10%)

Final verdicts:
  APPROVED    — score ≥ 70  AND all critical stages (1+2) passed
  CONDITIONAL — score ≥ 50  OR critical stages passed but minor failures
  REJECTED    — score < 50  OR any critical stage failed

Prints a rich terminal report using box-drawing characters.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional

from utils import get_logger

from .backtest_engine        import BacktestResult
from .walkforward_test       import WalkForwardResult
from .cross_market_test      import CrossMarketResult
from .monte_carlo_simulator  import MonteCarloResult
from .parameter_sensitivity  import SensitivityResult
from .regime_robustness_test import RegimeRobustnessResult

log = get_logger(__name__)

# ── Weights ────────────────────────────────────────────────────────────────
STAGE_WEIGHTS: dict[str, float] = {
    "backtest":    0.25,
    "walkforward": 0.25,
    "cross_market":0.15,
    "monte_carlo": 0.15,
    "sensitivity": 0.10,
    "regime":      0.10,
}

# ── Verdict thresholds ──────────────────────────────────────────────────────
APPROVED_MIN_SCORE    = 70.0
CONDITIONAL_MIN_SCORE = 50.0

# ── Critical stages (must pass for APPROVED) ────────────────────────────────
CRITICAL_STAGES = {"backtest", "walkforward"}


@dataclass
class StageScore:
    stage:   str
    passed:  bool
    score:   float     # 0–100 for this stage
    weight:  float
    detail:  str = ""


@dataclass
class ValidationReport:
    strategy_name:   str
    overall_score:   float  = 0.0
    verdict:         str    = "PENDING"   # APPROVED / CONDITIONAL / REJECTED
    stage_scores:    list[StageScore] = field(default_factory=list)

    # Raw sub-results
    backtest:     Optional[BacktestResult]        = field(default=None, repr=False)
    walkforward:  Optional[WalkForwardResult]     = field(default=None, repr=False)
    cross_market: Optional[CrossMarketResult]     = field(default=None, repr=False)
    monte_carlo:  Optional[MonteCarloResult]      = field(default=None, repr=False)
    sensitivity:  Optional[SensitivityResult]     = field(default=None, repr=False)
    regime:       Optional[RegimeRobustnessResult]= field(default=None, repr=False)

    def print_report(self) -> None:
        _print_validation_report(self)


class ValidationReportBuilder:
    """
    Builds and prints the final ValidationReport from all stage results.

    Usage::
        builder = ValidationReportBuilder()
        report  = builder.build("MyStrategy", bt, wf, cm, mc, ps, rr)
        report.print_report()
    """

    def build(
        self,
        strategy_name: str,
        backtest:     Optional[BacktestResult]         = None,
        walkforward:  Optional[WalkForwardResult]      = None,
        cross_market: Optional[CrossMarketResult]      = None,
        monte_carlo:  Optional[MonteCarloResult]       = None,
        sensitivity:  Optional[SensitivityResult]      = None,
        regime:       Optional[RegimeRobustnessResult] = None,
    ) -> ValidationReport:

        stage_scores = self._compute_stages(
            backtest, walkforward, cross_market,
            monte_carlo, sensitivity, regime,
        )

        weighted_score = sum(s.score * s.weight for s in stage_scores)
        overall        = round(weighted_score, 1)

        critical_passed = all(
            s.passed for s in stage_scores if s.stage in CRITICAL_STAGES
        )
        all_passed = all(s.passed for s in stage_scores)

        if overall >= APPROVED_MIN_SCORE and critical_passed:
            verdict = "APPROVED"
        elif overall >= CONDITIONAL_MIN_SCORE or critical_passed:
            verdict = "CONDITIONAL"
        else:
            verdict = "REJECTED"

        report = ValidationReport(
            strategy_name = strategy_name,
            overall_score = overall,
            verdict       = verdict,
            stage_scores  = stage_scores,
            backtest      = backtest,
            walkforward   = walkforward,
            cross_market  = cross_market,
            monte_carlo   = monte_carlo,
            sensitivity   = sensitivity,
            regime        = regime,
        )
        log.info("[ValidationReport] %s | Score: %.1f/100 | Verdict: %s",
                 strategy_name, overall, verdict)
        return report

    # ── Stage scoring ─────────────────────────────────────────────────────
    @staticmethod
    def _compute_stages(bt, wf, cm, mc, ps, rr) -> list[StageScore]:
        stages: list[StageScore] = []

        # ─ Stage 1: IS/OOS Backtest ─
        if bt is not None:
            s = _score_backtest(bt)
            stages.append(StageScore("backtest", bt.overfitting_flag == "PASS",
                                     s, STAGE_WEIGHTS["backtest"],
                                     f"OOS Sharpe: {bt.oos_stats.sharpe:.2f}  "
                                     f"OOS Return: {bt.oos_stats.return_pct:+.2f}%  "
                                     f"Overfitting: {bt.overfitting_flag}"))
        else:
            stages.append(StageScore("backtest", False, 0.0,
                                     STAGE_WEIGHTS["backtest"], "Not run"))

        # ─ Stage 2: Walk-Forward ─
        if wf is not None:
            s = min(100.0, wf.pass_rate_pct * 1.2)
            stages.append(StageScore("walkforward", wf.passed, round(s, 1),
                                     STAGE_WEIGHTS["walkforward"],
                                     f"Pass rate: {wf.pass_rate_pct:.0f}%  "
                                     f"WF-Eff: {wf.wf_efficiency:.2f}  "
                                     f"Folds: {len(wf.folds)}"))
        else:
            stages.append(StageScore("walkforward", False, 0.0,
                                     STAGE_WEIGHTS["walkforward"], "Not run"))

        # ─ Stage 3: Cross-Market ─
        if cm is not None:
            s = min(100.0, cm.pass_rate_pct * 1.1)
            stages.append(StageScore("cross_market", cm.passed, round(s, 1),
                                     STAGE_WEIGHTS["cross_market"],
                                     f"Markets: {cm.pass_count}/{cm.total_tested}"))
        else:
            stages.append(StageScore("cross_market", False, 0.0,
                                     STAGE_WEIGHTS["cross_market"], "Not run"))

        # ─ Stage 4: Monte Carlo ─
        if mc is not None:
            s = min(100.0, mc.profit_probability)
            stages.append(StageScore("monte_carlo", mc.passed, round(s, 1),
                                     STAGE_WEIGHTS["monte_carlo"],
                                     f"Profit prob: {mc.profit_probability:.1f}%  "
                                     f"Median: {mc.median_return_pct:+.2f}%"))
        else:
            stages.append(StageScore("monte_carlo", False, 0.0,
                                     STAGE_WEIGHTS["monte_carlo"], "Not run"))

        # ─ Stage 5: Parameter Sensitivity ─
        if ps is not None:
            s = ps.stability_score if ps.passed else ps.stability_score * 0.5
            stages.append(StageScore("sensitivity", ps.passed, round(s, 1),
                                     STAGE_WEIGHTS["sensitivity"],
                                     f"Stability: {ps.stability_score:.1f}/100  "
                                     f"Cliff: {'YES' if ps.cliff_detected else 'No'}"))
        else:
            stages.append(StageScore("sensitivity", False, 0.0,
                                     STAGE_WEIGHTS["sensitivity"], "Not run"))

        # ─ Stage 6: Regime Robustness ─
        if rr is not None:
            s = min(100.0, rr.pass_rate_pct)
            if rr.any_catastrophic:
                s *= 0.3
            stages.append(StageScore("regime", rr.passed, round(s, 1),
                                     STAGE_WEIGHTS["regime"],
                                     f"Regimes: {rr.pass_count}/{rr.total_regimes}  "
                                     f"Weakest: {rr.weakest_regime}"))
        else:
            stages.append(StageScore("regime", False, 0.0,
                                     STAGE_WEIGHTS["regime"], "Not run"))

        return stages


def _score_backtest(bt: BacktestResult) -> float:
    score = 0.0
    if bt.is_quality_gate:
        score += 40.0
    if bt.oos_stats.sharpe > 1.0:
        score += 20.0
    elif bt.oos_stats.sharpe > 0.5:
        score += 10.0
    if bt.overfitting_flag == "PASS":
        score += 25.0
    elif bt.overfitting_flag == "WARNING":
        score += 15.0
    if bt.oos_stats.profit_factor > 1.5:
        score += 15.0
    elif bt.oos_stats.profit_factor > 1.0:
        score += 8.0
    return min(100.0, score)


# ── Fancy terminal output ──────────────────────────────────────────────────
def _print_validation_report(r: ValidationReport) -> None:
    w = 72
    verdict_icons = {
        "APPROVED":    "✅  APPROVED",
        "CONDITIONAL": "⚠️   CONDITIONAL",
        "REJECTED":    "❌  REJECTED",
    }
    icon = verdict_icons.get(r.verdict, r.verdict)

    print()
    print("═" * w)
    print(f"{'  STRATEGY VALIDATION REPORT':^{w}}")
    print("═" * w)
    print(f"  Strategy : {r.strategy_name}")
    print(f"  Score    : {r.overall_score:.1f} / 100")
    print(f"  Verdict  : {icon}")
    print("─" * w)
    print(f"  {'STAGE':<22}  {'RESULT':<8}  {'SCORE':>6}  {'WEIGHT':>7}  DETAIL")
    print("─" * w)

    stage_labels = {
        "backtest":    "IS/OOS Backtest",
        "walkforward": "Walk-Forward",
        "cross_market":"Cross-Market",
        "monte_carlo": "Monte Carlo",
        "sensitivity": "Param Sensitivity",
        "regime":      "Regime Robustness",
    }

    for ss in r.stage_scores:
        tick   = "✅ PASS" if ss.passed else "❌ FAIL"
        label  = stage_labels.get(ss.stage, ss.stage)
        detail = ss.detail[:34] if len(ss.detail) > 34 else ss.detail
        print(f"  {label:<22}  {tick:<8}  {ss.score:>5.1f}  "
              f"{ss.weight*100:>6.0f}%  {detail}")

    print("─" * w)
    print(f"  {'WEIGHTED TOTAL':<22}  {'':>8}  {r.overall_score:>5.1f}  "
          f"{'100':>6}%")
    print("═" * w)

    if r.verdict == "APPROVED":
        print("  ✅  This strategy has passed institutional validation.")
        print("      It may proceed to paper trading.")
    elif r.verdict == "CONDITIONAL":
        print("  ⚠️   Conditional approval — review failing stages before")
        print("      deploying live capital.")
    else:
        print("  ❌  REJECTED — redesign required before deployment.")
    print("═" * w)
    print()
