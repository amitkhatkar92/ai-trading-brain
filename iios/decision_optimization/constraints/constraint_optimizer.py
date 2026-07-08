"""iios/decision_optimization/constraints/constraint_optimizer.py"""
from __future__ import annotations

import threading

from ..optimization_constants import MAX_CONSTRAINTS_IN_REGISTRY
from ..optimization_exceptions import (
    ConstraintAlreadyExistsError,
    ConstraintNotFoundError,
    RegistryOverflowError,
)
from ..optimization_context import Candidate
from .constraint_checker import OptimizationConstraint
from .constraint_report import ConstraintReport, build_constraint_report
from .constraint_solver import ConstraintSolver


class ConstraintOptimizer:
    """
    Combines a constraint registry with feasibility filtering
    and full-report generation.
    """

    def __init__(self, solver: ConstraintSolver | None = None) -> None:
        self._solver      = solver or ConstraintSolver()
        self._constraints: dict[str, OptimizationConstraint] = {}
        self._lock        = threading.RLock()

    # ── Registry ──────────────────────────────────────────────────────────

    def register(
        self, constraint: OptimizationConstraint, *, overwrite: bool = False
    ) -> None:
        with self._lock:
            if not overwrite and constraint.constraint_id in self._constraints:
                raise ConstraintAlreadyExistsError(constraint.constraint_id)
            if len(self._constraints) >= MAX_CONSTRAINTS_IN_REGISTRY:
                raise RegistryOverflowError(MAX_CONSTRAINTS_IN_REGISTRY)
            self._constraints[constraint.constraint_id] = constraint

    def get(self, constraint_id: str) -> OptimizationConstraint:
        with self._lock:
            if constraint_id not in self._constraints:
                raise ConstraintNotFoundError(constraint_id)
            return self._constraints[constraint_id]

    def has(self, constraint_id: str) -> bool:
        with self._lock:
            return constraint_id in self._constraints

    def all(self) -> list[OptimizationConstraint]:
        with self._lock:
            return list(self._constraints.values())

    # ── Filtering ──────────────────────────────────────────────────────────

    def filter_feasible(
        self,
        candidates:  list[Candidate],
        constraints: list[OptimizationConstraint] | None = None,
    ) -> list[Candidate]:
        """Return candidates satisfying all hard constraints."""
        active = constraints if constraints is not None else self.all()
        return [c for c in candidates if self._solver.is_feasible(c, active)]

    def solve_and_report(
        self,
        candidates:  list[Candidate],
        constraints: list[OptimizationConstraint] | None = None,
    ) -> ConstraintReport:
        active     = constraints if constraints is not None else self.all()
        results    = self._solver.solve(candidates, active)
        return build_constraint_report(candidates, active, results)

    def stats(self) -> dict:
        with self._lock:
            return {"total_constraints": len(self._constraints)}


_optimizer: ConstraintOptimizer | None = None
_lock      = threading.Lock()


def get_constraint_optimizer() -> ConstraintOptimizer:
    global _optimizer
    if _optimizer is None:
        with _lock:
            if _optimizer is None:
                _optimizer = ConstraintOptimizer()
    return _optimizer


def reset_constraint_optimizer() -> None:
    global _optimizer
    with _lock:
        _optimizer = None
