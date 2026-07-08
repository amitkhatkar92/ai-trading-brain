"""iios/decision_optimization/optimization_registry.py — Master registry."""
from __future__ import annotations

import threading

from .objectives.objective import Objective
from .objectives.objective_registry import ObjectiveRegistry, get_objective_registry
from .constraints.constraint_checker import OptimizationConstraint
from .constraints.constraint_optimizer import ConstraintOptimizer, get_constraint_optimizer
from .algorithms.optimization_algorithm import OptimizationAlgorithm
from .algorithms.algorithm_registry import AlgorithmRegistry, get_algorithm_registry


class OptimizationRegistry:
    """
    Master registry — thin facade over the three sub-registries.
    Use for unified registration in application bootstrap.
    """

    def __init__(
        self,
        objective_registry:   ObjectiveRegistry   | None = None,
        constraint_optimizer: ConstraintOptimizer | None = None,
        algorithm_registry:   AlgorithmRegistry   | None = None,
    ) -> None:
        self._objectives  = objective_registry   or get_objective_registry()
        self._constraints = constraint_optimizer or get_constraint_optimizer()
        self._algorithms  = algorithm_registry   or get_algorithm_registry()

    # ── Objectives ──────────────────────────────────────────────────────────

    def register_objective(
        self, objective: Objective, *, overwrite: bool = False
    ) -> None:
        self._objectives.register(objective, overwrite=overwrite)

    def get_objective(self, objective_id: str) -> Objective:
        return self._objectives.get(objective_id)

    def all_objectives(self) -> list[Objective]:
        return self._objectives.all()

    # ── Constraints ─────────────────────────────────────────────────────────

    def register_constraint(
        self, constraint: OptimizationConstraint, *, overwrite: bool = False
    ) -> None:
        self._constraints.register(constraint, overwrite=overwrite)

    def get_constraint(self, constraint_id: str) -> OptimizationConstraint:
        return self._constraints.get(constraint_id)

    def all_constraints(self) -> list[OptimizationConstraint]:
        return self._constraints.all()

    # ── Algorithms ───────────────────────────────────────────────────────────

    def register_algorithm(
        self, algorithm: OptimizationAlgorithm, *, overwrite: bool = True
    ) -> None:
        self._algorithms.register(algorithm, overwrite=overwrite)

    def get_algorithm(self, algorithm_id: str) -> OptimizationAlgorithm:
        return self._algorithms.get(algorithm_id)

    def all_algorithms(self) -> list[str]:
        return self._algorithms.all_ids()

    def stats(self) -> dict:
        return {
            "objectives":  self._objectives.stats(),
            "constraints": self._constraints.stats(),
            "algorithms":  self._algorithms.stats(),
        }


_registry: OptimizationRegistry | None = None
_lock     = threading.Lock()


def get_optimization_registry() -> OptimizationRegistry:
    global _registry
    if _registry is None:
        with _lock:
            if _registry is None:
                _registry = OptimizationRegistry()
    return _registry


def reset_optimization_registry() -> None:
    global _registry
    with _lock:
        _registry = None
