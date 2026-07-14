"""iios/investment/portfolio/optimization/optimization_registry.py

Registry of pluggable optimization algorithms.
"""
from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional

from iios.investment.portfolio.optimization.optimization_engine import (
    BlackLittermanOptimizer,
    EqualRiskContributionOptimizer,
    EqualWeightOptimizer,
    HierarchicalRiskParityOptimizer,
    MaximumCalmarOptimizer,
    MaximumDiversificationOptimizer,
    MaximumSharpeOptimizer,
    MaximumSortinoOptimizer,
    MaximumUtilityOptimizer,
    MeanVarianceOptimizer,
    MinimumTurnoverOptimizer,
    MinimumVarianceOptimizer,
    OptimizationAlgorithm,
    RiskParityOptimizer,
)
from iios.investment.portfolio.optimization.optimization_types import OptimizationMethod


class OptimizationRegistryError(ValueError):
    pass


class OptimizationRegistry:
    """
    Thread-safe registry mapping OptimizationMethod → OptimizationAlgorithm.
    Pre-populated with all built-in algorithms.
    Allows custom algorithms to be registered at runtime.
    """

    def __init__(self) -> None:
        self._lock      = threading.Lock()
        self._registry: Dict[str, OptimizationAlgorithm] = {}
        self._register_builtins()

    def _register_builtins(self) -> None:
        builtins: List[OptimizationAlgorithm] = [
            EqualWeightOptimizer(),
            MinimumVarianceOptimizer(),
            RiskParityOptimizer(),
            EqualRiskContributionOptimizer(),
            MaximumDiversificationOptimizer(),
            MaximumSharpeOptimizer(),
            MaximumSortinoOptimizer(),
            MaximumCalmarOptimizer(),
            MeanVarianceOptimizer(),
            MaximumUtilityOptimizer(),
            MinimumTurnoverOptimizer(),
            BlackLittermanOptimizer(),
            HierarchicalRiskParityOptimizer(),
        ]
        for algo in builtins:
            self._registry[algo.method.value] = algo

    def register(
        self,
        algorithm: OptimizationAlgorithm,
        *,
        overwrite: bool = False,
    ) -> None:
        key = algorithm.method.value
        with self._lock:
            if key in self._registry and not overwrite:
                raise OptimizationRegistryError(
                    f"Algorithm '{key}' already registered. Use overwrite=True to replace."
                )
            self._registry[key] = algorithm

    def get(self, method: OptimizationMethod) -> OptimizationAlgorithm:
        with self._lock:
            algo = self._registry.get(method.value)
        if algo is None:
            raise OptimizationRegistryError(
                f"No algorithm registered for method '{method.value}'. "
                f"Available: {self.all_methods()}"
            )
        return algo

    def is_registered(self, method: OptimizationMethod) -> bool:
        with self._lock:
            return method.value in self._registry

    def all_methods(self) -> List[str]:
        with self._lock:
            return sorted(self._registry)

    def unregister(self, method: OptimizationMethod) -> bool:
        with self._lock:
            return self._registry.pop(method.value, None) is not None


# ---------------------------------------------------------------------------
# Module-level default registry (shared singleton)
# ---------------------------------------------------------------------------

_DEFAULT_REGISTRY: Optional[OptimizationRegistry] = None
_REGISTRY_LOCK = threading.Lock()


def get_default_registry() -> OptimizationRegistry:
    global _DEFAULT_REGISTRY
    if _DEFAULT_REGISTRY is None:
        with _REGISTRY_LOCK:
            if _DEFAULT_REGISTRY is None:
                _DEFAULT_REGISTRY = OptimizationRegistry()
    return _DEFAULT_REGISTRY
