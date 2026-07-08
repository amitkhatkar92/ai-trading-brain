"""iios/decision_optimization/simulation/sensitivity_analyzer.py"""
from __future__ import annotations

from ..optimization_context import Candidate
from ..objectives.objective import Objective
from ..constraints.constraint_checker import OptimizationConstraint
from ..algorithms.optimization_algorithm import GreedyOptimizer, OptimizationAlgorithm
from ..optimization_constants import DEFAULT_SENSITIVITY_STEPS


class SensitivityAnalyzer:
    """
    Varies a single objective's weight across a range and observes
    how the optimal candidate changes.
    """

    def analyze_objective_weight(
        self,
        candidates:   list[Candidate],
        objectives:   list[Objective],
        constraints:  list[OptimizationConstraint],
        objective_id: str,
        weight_range: tuple[float, float] = (0.0, 1.0),
        steps:        int                 = DEFAULT_SENSITIVITY_STEPS,
        algorithm:    OptimizationAlgorithm | None = None,
    ) -> dict:
        alg   = algorithm or GreedyOptimizer()
        low, high = weight_range
        if steps < 2:
            steps = 2
        step_size = (high - low) / max(steps - 1, 1)

        weights_tested: list[float] = []
        top_candidates: list[str]   = []
        rank_changes:   list[dict]  = []

        for i in range(steps):
            w = low + i * step_size
            # Build modified objective list
            modified_objs: list[Objective] = []
            for obj in objectives:
                if obj.objective_id == objective_id:
                    from ..objectives.objective_function import FunctionObjective
                    proxy = FunctionObjective(
                        objective_id   = obj.objective_id,
                        name           = obj.name,
                        evaluator      = obj.evaluate,
                        objective_type = obj.objective_type,
                        weight         = w,
                        target_value   = obj.target_value,
                    )
                    modified_objs.append(proxy)
                else:
                    modified_objs.append(obj)

            solution = alg.optimize(candidates, modified_objs, constraints)
            top      = solution.optimal_id or ""
            weights_tested.append(w)
            top_candidates.append(top)

            if i > 0 and top != top_candidates[i - 1]:
                rank_changes.append({
                    "at_weight": w,
                    "from":      top_candidates[i - 1],
                    "to":        top,
                })

        return {
            "objective_id":  objective_id,
            "weights":       weights_tested,
            "top_candidate": top_candidates,
            "rank_changes":  rank_changes,
        }
