"""iios/investment/strategy/evaluation/robustness_engine.py
RobustnessReport — orchestrates walk-forward, Monte Carlo, and stress tests.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from iios.investment.strategy.evaluation.evaluation_input import EvaluationInput
from iios.investment.strategy.evaluation.walk_forward_analysis import (
    WalkForwardAnalyzer, WalkForwardReport
)
from iios.investment.strategy.evaluation.monte_carlo_analysis import (
    MonteCarloAnalyzer, MonteCarloReport
)
from iios.investment.strategy.evaluation.stress_testing import (
    StressTester, StressTestReport
)
from iios.investment.strategy.evaluation.performance_statistics import safe_mean


@dataclass(frozen=True)
class RobustnessReport:
    walk_forward:    WalkForwardReport
    monte_carlo:     MonteCarloReport
    stress_test:     StressTestReport

    # Composite scores derived from sub-reports (0–1)
    walk_forward_stability: float = 0.0
    mc_robustness:          float = 0.0
    stress_survival:        float = 0.0
    overall_robustness:     float = 0.0   # weighted composite

    def to_dict(self) -> Dict[str, Any]:
        return {
            "walk_forward":          self.walk_forward.to_dict(),
            "monte_carlo":           self.monte_carlo.to_dict(),
            "stress_test":           self.stress_test.to_dict(),
            "walk_forward_stability": self.walk_forward_stability,
            "mc_robustness":          self.mc_robustness,
            "stress_survival":        self.stress_survival,
            "overall_robustness":     self.overall_robustness,
        }


class RobustnessEngine:
    """Composes WalkForward, MonteCarlo, StressTest sub-engines."""

    def __init__(
        self,
        wf_folds: int = 4,
        mc_simulations: int = 1000,
        mc_seed: int = 42,
    ) -> None:
        self._wf = WalkForwardAnalyzer(n_folds=wf_folds)
        self._mc = MonteCarloAnalyzer(n_simulations=mc_simulations, seed=mc_seed)
        self._st = StressTester()

    def evaluate(self, inp: EvaluationInput) -> RobustnessReport:
        wf = self._wf.analyze(
            inp.trades,
            inp.equity_curve,
            inp.rf_per_period,
            inp.periods_per_year,
        )
        mc = self._mc.analyze(
            inp.trades,
            inp.rf_per_period,
            inp.periods_per_year,
        )
        st = self._st.test(inp.trades)

        wf_score = wf.stability_score
        mc_score = mc.robustness_score
        st_score = st.stress_score

        # Weighted composite (WF most important, then MC, then stress)
        overall = 0.45 * wf_score + 0.35 * mc_score + 0.20 * st_score

        return RobustnessReport(
            walk_forward=wf,
            monte_carlo=mc,
            stress_test=st,
            walk_forward_stability=wf_score,
            mc_robustness=mc_score,
            stress_survival=st_score,
            overall_robustness=overall,
        )
