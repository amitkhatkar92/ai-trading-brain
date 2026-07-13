"""iios/investment/strategy/risk/stress_testing.py
StressTestingEngine — runs all (or selected) stress scenarios against a strategy.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.investment.strategy.risk.risk_input import StrategyRiskInput
from iios.investment.strategy.risk.stress_scenarios import (
    StressScenario, BUILTIN_SCENARIOS
)
from iios.investment.strategy.risk.scenario_engine import (
    ScenarioEngine, ScenarioResult
)
from iios.investment.strategy.risk.risk_analysis import RiskAnalysis, RiskAnalysisResult
from iios.investment.strategy.risk.stress_statistics import aggregate_stress_score
from iios.investment.strategy.risk.risk_statistics import clamp


@dataclass(frozen=True)
class StressTestReport:
    """Complete stress test results for a strategy across all scenarios."""
    strategy_id:           str
    base_risk_score:       float
    aggregate_stress_score: float   # probability-weighted average stressed score
    worst_scenario:        str      # name of the most damaging scenario
    worst_stressed_score:  float
    scenarios_passed:      int
    scenarios_failed:      int
    scenario_results:      List[ScenarioResult]
    overall_stress_rating: str      # "ROBUST" | "MODERATE" | "VULNERABLE" | "FRAGILE"
    generated_at:          datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def pass_rate(self) -> float:
        total = self.scenarios_passed + self.scenarios_failed
        return self.scenarios_passed / total if total > 0 else 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id":            self.strategy_id,
            "base_risk_score":        round(self.base_risk_score, 2),
            "aggregate_stress_score": round(self.aggregate_stress_score, 2),
            "worst_scenario":         self.worst_scenario,
            "worst_stressed_score":   round(self.worst_stressed_score, 2),
            "scenarios_passed":       self.scenarios_passed,
            "scenarios_failed":       self.scenarios_failed,
            "pass_rate":              round(self.pass_rate, 4),
            "overall_stress_rating":  self.overall_stress_rating,
            "scenario_results":       [r.to_dict() for r in self.scenario_results],
            "generated_at":           self.generated_at.isoformat(),
        }


def _stress_rating(pass_rate: float, aggregate_score: float) -> str:
    if pass_rate >= 0.90 and aggregate_score <= 40.0:
        return "ROBUST"
    if pass_rate >= 0.70 and aggregate_score <= 60.0:
        return "MODERATE"
    if pass_rate >= 0.50:
        return "VULNERABLE"
    return "FRAGILE"


class StressTestingEngine:
    """
    Runs multiple StressScenarios against a StrategyRiskInput.
    Supports pluggable scenario libraries and parallel evaluation.
    """

    def __init__(
        self,
        scenarios:        Optional[List[StressScenario]] = None,
        scenario_engine:  Optional[ScenarioEngine]       = None,
        risk_analysis:    Optional[RiskAnalysis]         = None,
        max_workers:      int = 4,
    ) -> None:
        self._scenarios = scenarios if scenarios is not None else BUILTIN_SCENARIOS
        self._engine    = scenario_engine or ScenarioEngine(risk_analysis or RiskAnalysis())
        self._analysis  = risk_analysis or RiskAnalysis()
        self._workers   = max_workers

    def add_scenario(self, scenario: StressScenario) -> None:
        """Append a custom scenario to the active scenario library."""
        self._scenarios = list(self._scenarios) + [scenario]

    def run(
        self,
        inp:       StrategyRiskInput,
        scenarios: Optional[List[StressScenario]] = None,
    ) -> StressTestReport:
        """
        Run all (or specified) stress scenarios.
        Base risk is computed once and reused across scenarios.
        """
        active_scenarios = scenarios if scenarios is not None else self._scenarios
        base = self._analysis.analyse(inp)

        results: List[ScenarioResult] = []
        with ThreadPoolExecutor(max_workers=self._workers) as pool:
            futures = {
                pool.submit(self._engine.evaluate, inp, sc, base): sc
                for sc in active_scenarios
            }
            for fut in as_completed(futures):
                try:
                    results.append(fut.result())
                except Exception:
                    pass

        if not results:
            return StressTestReport(
                strategy_id=inp.strategy_id,
                base_risk_score=base.composite_risk_score,
                aggregate_stress_score=base.composite_risk_score,
                worst_scenario="",
                worst_stressed_score=base.composite_risk_score,
                scenarios_passed=0,
                scenarios_failed=0,
                scenario_results=[],
                overall_stress_rating="ROBUST",
            )

        # Sort results for deterministic reporting
        results.sort(key=lambda r: r.scenario_name)

        scores  = [r.stressed_risk_score for r in results]
        weights = [r.scenario_probability for r in results]
        agg     = aggregate_stress_score(scores, weights)

        worst   = max(results, key=lambda r: r.stressed_risk_score)
        passed  = sum(1 for r in results if r.passes)
        failed  = len(results) - passed
        rating  = _stress_rating(passed / max(len(results), 1), agg)

        return StressTestReport(
            strategy_id=inp.strategy_id,
            base_risk_score=base.composite_risk_score,
            aggregate_stress_score=agg,
            worst_scenario=worst.scenario_name,
            worst_stressed_score=worst.stressed_risk_score,
            scenarios_passed=passed,
            scenarios_failed=failed,
            scenario_results=results,
            overall_stress_rating=rating,
        )
