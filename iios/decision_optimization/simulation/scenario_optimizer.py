"""iios/decision_optimization/simulation/scenario_optimizer.py"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from ..optimization_context import Candidate
from ..objectives.objective import Objective
from ..constraints.constraint_checker import OptimizationConstraint
from ..algorithms.optimization_algorithm import OptimizationAlgorithm, OptimizationSolution
from .simulation_engine import SimulationEngine


@dataclass
class Scenario:
    scenario_id:  str  = field(default_factory=lambda: str(uuid.uuid4()))
    name:         str  = ""
    perturbation: dict = field(default_factory=dict)
    metadata:     dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"scenario_id": self.scenario_id, "name": self.name}


@dataclass
class ScenarioResult:
    scenario:  Scenario
    solution:  OptimizationSolution

    def to_dict(self) -> dict:
        return {
            "scenario": self.scenario.to_dict(),
            "solution": self.solution.to_dict(),
        }


class ScenarioOptimizer:
    """Runs optimization over a named set of scenarios."""

    def __init__(self, simulation_engine: SimulationEngine | None = None) -> None:
        self._engine = simulation_engine or SimulationEngine()

    def optimize_scenarios(
        self,
        base_candidates: list[Candidate],
        objectives:      list[Objective],
        constraints:     list[OptimizationConstraint],
        scenarios:       list[Scenario],
        algorithm:       OptimizationAlgorithm | None = None,
    ) -> list[ScenarioResult]:
        results: list[ScenarioResult] = []
        for sc in scenarios:
            solution = self._engine.run_what_if(
                base_candidates, objectives, constraints, sc.perturbation, algorithm
            )
            results.append(ScenarioResult(scenario=sc, solution=solution))
        return results

    def compare(self, results: list[ScenarioResult]) -> dict:
        """Summarise which scenario yields the best optimal candidate."""
        if not results:
            return {"best_scenario": None}

        best = max(
            results,
            key=lambda r: r.solution.scores.get(r.solution.optimal_id or "", 0.0),
        )
        return {
            "best_scenario":    best.scenario.name or best.scenario.scenario_id,
            "best_optimal_id":  best.solution.optimal_id,
            "scenario_count":   len(results),
        }
