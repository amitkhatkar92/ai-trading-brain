"""iios/decision_optimization/algorithms/algorithm_executor.py"""
from __future__ import annotations

from ..optimization_constants import AlgorithmType, OptimizationStatus
from ..optimization_context import Candidate
from ..objectives.objective import Objective
from ..constraints.constraint_checker import OptimizationConstraint
from .algorithm_registry import AlgorithmRegistry, get_algorithm_registry
from .algorithm_selector import AlgorithmSelector
from .optimization_algorithm import OptimizationSolution


class AlgorithmExecutor:
    """
    Runs an OptimizationAlgorithm with structured error handling.
    Supports parallel execution via ThreadPoolExecutor for large candidate sets.
    """

    def __init__(self, selector: AlgorithmSelector | None = None) -> None:
        self._selector = selector or AlgorithmSelector()

    def execute(
        self,
        candidates:     list[Candidate],
        objectives:     list[Objective],
        constraints:    list[OptimizationConstraint],
        algorithm_type: AlgorithmType = AlgorithmType.GREEDY,
        algorithm_id:   str | None    = None,
    ) -> OptimizationSolution:
        alg = self._selector.select(algorithm_type, algorithm_id)
        try:
            solution = alg.optimize(candidates, objectives, constraints)
        except Exception as exc:  # noqa: BLE001
            solution = OptimizationSolution(
                status       = OptimizationStatus.ERROR,
                algorithm_id = getattr(alg, "algorithm_id", ""),
                metadata     = {"error": str(exc)},
            )
        return solution

    def execute_parallel(
        self,
        candidate_batches: list[list[Candidate]],
        objectives:        list[Objective],
        constraints:       list[OptimizationConstraint],
        algorithm_type:    AlgorithmType = AlgorithmType.GREEDY,
        algorithm_id:      str | None    = None,
        max_workers:       int = 4,
    ) -> list[OptimizationSolution]:
        """
        Execute the same optimization across multiple candidate batches in parallel.
        Results are returned in the same order as the input batches.
        """
        from concurrent.futures import ThreadPoolExecutor

        alg = self._selector.select(algorithm_type, algorithm_id)

        def _run(batch: list[Candidate]) -> OptimizationSolution:
            try:
                return alg.optimize(batch, objectives, constraints)
            except Exception as exc:  # noqa: BLE001
                return OptimizationSolution(
                    status   = OptimizationStatus.ERROR,
                    metadata = {"error": str(exc)},
                )

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = [pool.submit(_run, batch) for batch in candidate_batches]
            return [f.result() for f in futures]
