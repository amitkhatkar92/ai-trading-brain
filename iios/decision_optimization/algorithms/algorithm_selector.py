"""iios/decision_optimization/algorithms/algorithm_selector.py"""
from __future__ import annotations

from ..optimization_constants import AlgorithmType
from ..optimization_exceptions import UnsupportedAlgorithmError
from .algorithm_registry import AlgorithmRegistry, get_algorithm_registry
from .optimization_algorithm import OptimizationAlgorithm

_TYPE_MAP: dict[AlgorithmType, str] = {
    AlgorithmType.GREEDY:          "greedy",
    AlgorithmType.WEIGHTED_SUM:    "weighted_sum",
    AlgorithmType.CONSTRAINT:      "constraint",
    AlgorithmType.MULTI_OBJECTIVE: "multi_objective",
    AlgorithmType.HEURISTIC:       "greedy",       # fallback
    AlgorithmType.EVOLUTIONARY:    "multi_objective",  # fallback
    AlgorithmType.DYNAMIC:         "weighted_sum",     # fallback
    AlgorithmType.CUSTOM:          "greedy",            # fallback
}


class AlgorithmSelector:
    """Picks an OptimizationAlgorithm by type or explicit id."""

    def __init__(self, registry: AlgorithmRegistry | None = None) -> None:
        self._registry = registry or get_algorithm_registry()

    def select(
        self,
        algorithm_type: AlgorithmType = AlgorithmType.GREEDY,
        algorithm_id:   str | None    = None,
    ) -> OptimizationAlgorithm:
        if algorithm_id:
            return self._registry.get(algorithm_id)
        alg_id = _TYPE_MAP.get(algorithm_type)
        if alg_id is None:
            raise UnsupportedAlgorithmError(algorithm_type.value)
        return self._registry.get(alg_id)

    def available_ids(self) -> list[str]:
        return self._registry.all_ids()
