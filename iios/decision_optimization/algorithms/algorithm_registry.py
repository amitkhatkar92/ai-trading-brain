"""iios/decision_optimization/algorithms/algorithm_registry.py"""
from __future__ import annotations

import threading

from ..optimization_constants import MAX_ALGORITHMS_IN_REGISTRY
from ..optimization_exceptions import AlgorithmNotFoundError, RegistryOverflowError
from .optimization_algorithm import (
    ConstraintSatisfactionOptimizer,
    GreedyOptimizer,
    MultiObjectiveOptimizer,
    OptimizationAlgorithm,
    WeightedSumOptimizer,
)


class AlgorithmRegistry:
    """Thread-safe registry for OptimizationAlgorithm instances."""

    def __init__(self) -> None:
        self._algorithms: dict[str, OptimizationAlgorithm] = {}
        self._lock = threading.RLock()
        # Pre-register built-ins
        for alg in [
            GreedyOptimizer(),
            WeightedSumOptimizer(),
            ConstraintSatisfactionOptimizer(),
            MultiObjectiveOptimizer(),
        ]:
            self._algorithms[alg.algorithm_id] = alg

    def register(
        self, algorithm: OptimizationAlgorithm, *, overwrite: bool = True
    ) -> None:
        with self._lock:
            if len(self._algorithms) >= MAX_ALGORITHMS_IN_REGISTRY:
                raise RegistryOverflowError(MAX_ALGORITHMS_IN_REGISTRY)
            self._algorithms[algorithm.algorithm_id] = algorithm

    def get(self, algorithm_id: str) -> OptimizationAlgorithm:
        with self._lock:
            if algorithm_id not in self._algorithms:
                raise AlgorithmNotFoundError(algorithm_id)
            return self._algorithms[algorithm_id]

    def has(self, algorithm_id: str) -> bool:
        with self._lock:
            return algorithm_id in self._algorithms

    def all_ids(self) -> list[str]:
        with self._lock:
            return list(self._algorithms.keys())

    def stats(self) -> dict:
        with self._lock:
            return {"total_algorithms": len(self._algorithms)}


_registry: AlgorithmRegistry | None = None
_lock     = threading.Lock()


def get_algorithm_registry() -> AlgorithmRegistry:
    global _registry
    if _registry is None:
        with _lock:
            if _registry is None:
                _registry = AlgorithmRegistry()
    return _registry


def reset_algorithm_registry() -> None:
    global _registry
    with _lock:
        _registry = None
