"""iios/investment/portfolio/risk/stress_testing.py

Stress testing engine: runs all (or selected) scenarios and produces
a consolidated StressTestReport.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from iios.investment.portfolio.risk.risk_types import RiskPosition
from iios.investment.portfolio.risk.scenario_engine import ScenarioEngine, ScenarioResult
from iios.investment.portfolio.risk.scenario_library import SCENARIOS, Scenario


@dataclass(frozen=True)
class StressTestReport:
    """Consolidated output from running multiple stress scenarios."""

    report_id:         str                        = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:      str                        = ""
    n_scenarios_run:   int                        = 0

    scenario_results:  tuple                      = field(default_factory=tuple)  # tuple[ScenarioResult, ...]

    # Summary
    worst_scenario:    str                        = ""
    worst_loss:        float                      = 0.0
    best_scenario:     str                        = ""
    best_outcome:      float                      = 0.0
    avg_loss:          float                      = 0.0
    median_loss:       float                      = 0.0

    # Resilience score [0, 1]: 1.0 = fully resilient (no losses)
    resilience_score:  float                      = 1.0

    # Tail risk: average loss in the worst 20% of scenarios
    tail_avg_loss:     float                      = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id":       self.report_id,
            "portfolio_id":    self.portfolio_id,
            "n_scenarios_run": self.n_scenarios_run,
            "worst_scenario":  self.worst_scenario,
            "worst_loss":      round(self.worst_loss, 4),
            "avg_loss":        round(self.avg_loss, 4),
            "resilience_score":round(self.resilience_score, 4),
            "tail_avg_loss":   round(self.tail_avg_loss, 4),
            "scenarios": [r.to_dict() for r in self.scenario_results],
        }


class StressTestEngine:
    """Runs all or selected stress scenarios against a portfolio."""

    def __init__(self) -> None:
        self._scenario_engine = ScenarioEngine()

    def run_all(
        self,
        positions:    List[RiskPosition],
        scenarios:    Optional[Dict[str, Scenario]] = None,
        portfolio_id: str = "",
    ) -> StressTestReport:
        if scenarios is None:
            scenarios = SCENARIOS

        if not positions:
            return StressTestReport(
                portfolio_id=portfolio_id,
                resilience_score=1.0,
            )

        results: List[ScenarioResult] = []
        for _key, scenario in scenarios.items():
            r = self._scenario_engine.run(positions, scenario, portfolio_id)
            results.append(r)

        impacts = [r.portfolio_impact for r in results]
        impacts_sorted = sorted(impacts)
        n = len(impacts)

        worst_r  = min(results, key=lambda r: r.portfolio_impact)
        best_r   = max(results, key=lambda r: r.portfolio_impact)
        avg_loss = sum(impacts) / n
        med_loss = impacts_sorted[n // 2] if n else 0.0

        tail_cut = max(1, n // 5)
        tail_avg = sum(impacts_sorted[:tail_cut]) / tail_cut if tail_cut else 0.0

        # Resilience: 1 - |worst_loss| (floored to 0)
        resilience = max(0.0, 1.0 + worst_r.portfolio_impact)

        return StressTestReport(
            portfolio_id     = portfolio_id,
            n_scenarios_run  = n,
            scenario_results = tuple(results),
            worst_scenario   = worst_r.scenario_name,
            worst_loss       = round(worst_r.portfolio_impact, 6),
            best_scenario    = best_r.scenario_name,
            best_outcome     = round(best_r.portfolio_impact, 6),
            avg_loss         = round(avg_loss, 6),
            median_loss      = round(med_loss, 6),
            resilience_score = round(resilience, 6),
            tail_avg_loss    = round(tail_avg, 6),
        )
