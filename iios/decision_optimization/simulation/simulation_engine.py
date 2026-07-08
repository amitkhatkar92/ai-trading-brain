"""iios/decision_optimization/simulation/simulation_engine.py — What-if & scenario."""
from __future__ import annotations

import copy

from ..optimization_context import Candidate
from ..objectives.objective import Objective
from ..constraints.constraint_checker import OptimizationConstraint
from ..algorithms.optimization_algorithm import OptimizationAlgorithm, OptimizationSolution
from ..algorithms.optimization_algorithm import GreedyOptimizer


class SimulationEngine:
    """
    Runs hypothetical optimizations with modified candidate payloads.

    ``perturbation`` is a dict ``{candidate_id: {field: value}}``.
    If a candidate_id key is absent, that candidate is left unchanged.
    The special key ``"*"`` applies to all candidates.
    """

    def run_what_if(
        self,
        candidates:   list[Candidate],
        objectives:   list[Objective],
        constraints:  list[OptimizationConstraint],
        perturbation: dict,
        algorithm:    OptimizationAlgorithm | None = None,
    ) -> OptimizationSolution:
        alg     = algorithm or GreedyOptimizer()
        mutated = self._apply_perturbation(candidates, perturbation)
        return alg.optimize(mutated, objectives, constraints)

    def run_scenario(
        self,
        base_candidates: list[Candidate],
        objectives:      list[Objective],
        constraints:     list[OptimizationConstraint],
        scenarios:       list[dict],      # each dict is a perturbation
        algorithm:       OptimizationAlgorithm | None = None,
    ) -> list[OptimizationSolution]:
        return [
            self.run_what_if(base_candidates, objectives, constraints, sc, algorithm)
            for sc in scenarios
        ]

    @staticmethod
    def _apply_perturbation(
        candidates:  list[Candidate],
        perturbation: dict,
    ) -> list[Candidate]:
        result: list[Candidate] = []
        global_updates = perturbation.get("*", {})
        for cand in candidates:
            c = copy.copy(cand)
            c.payload = dict(cand.payload)
            # Apply global patch
            for k, v in global_updates.items():
                c.payload[k] = v
            # Apply per-candidate patch
            for k, v in perturbation.get(cand.candidate_id, {}).items():
                if k == "evaluation_score":
                    c.evaluation_score = float(v)
                else:
                    c.payload[k] = v
            result.append(c)
        return result
