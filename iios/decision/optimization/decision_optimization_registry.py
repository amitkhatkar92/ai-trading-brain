"""
decision_optimization_registry.py — iios.decision.optimization
================================================================
Thread-safe registry for objectives and constraints.

C9 Decision Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from .constants import DEFAULT_MAX_CONSTRAINTS, DEFAULT_MAX_OBJECTIVES
from .decision_constraint import DecisionConstraint
from .decision_objective  import DecisionObjective
from .exceptions import ConstraintNotFoundError, ObjectiveNotFoundError


class DecisionOptimizationRegistry:
    """
    Thread-safe registry for :class:`DecisionObjective` and
    :class:`DecisionConstraint` objects.

    Parameters
    ----------
    max_objectives :  Maximum objectives the registry accepts.
    max_constraints : Maximum constraints the registry accepts.
    """

    def __init__(
        self,
        max_objectives:  int = DEFAULT_MAX_OBJECTIVES,
        max_constraints: int = DEFAULT_MAX_CONSTRAINTS,
    ) -> None:
        self._lock        = threading.RLock()
        self._objectives:  Dict[str, DecisionObjective]  = {}
        self._constraints: Dict[str, DecisionConstraint] = {}
        self._max_obj     = max_objectives
        self._max_con     = max_constraints

    # ------------------------------------------------------------------
    # Objectives
    # ------------------------------------------------------------------

    def register_objective(self, objective: DecisionObjective) -> None:
        with self._lock:
            if (len(self._objectives) >= self._max_obj
                    and objective.objective_id not in self._objectives):
                raise ObjectiveNotFoundError(
                    f"Objective registry full (max {self._max_obj})"
                )
            self._objectives[objective.objective_id] = objective

    def get_objective(self, objective_id: str) -> DecisionObjective:
        with self._lock:
            if objective_id not in self._objectives:
                raise ObjectiveNotFoundError(objective_id)
            return self._objectives[objective_id]

    def find_objective(self, objective_id: str) -> Optional[DecisionObjective]:
        with self._lock:
            return self._objectives.get(objective_id)

    def deregister_objective(self, objective_id: str) -> Optional[DecisionObjective]:
        with self._lock:
            return self._objectives.pop(objective_id, None)

    def all_objectives(self) -> List[DecisionObjective]:
        with self._lock:
            return list(self._objectives.values())

    def objective_count(self) -> int:
        with self._lock:
            return len(self._objectives)

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------

    def register_constraint(self, constraint: DecisionConstraint) -> None:
        with self._lock:
            if (len(self._constraints) >= self._max_con
                    and constraint.constraint_id not in self._constraints):
                raise ConstraintNotFoundError(
                    f"Constraint registry full (max {self._max_con})"
                )
            self._constraints[constraint.constraint_id] = constraint

    def get_constraint(self, constraint_id: str) -> DecisionConstraint:
        with self._lock:
            if constraint_id not in self._constraints:
                raise ConstraintNotFoundError(constraint_id)
            return self._constraints[constraint_id]

    def find_constraint(self, constraint_id: str) -> Optional[DecisionConstraint]:
        with self._lock:
            return self._constraints.get(constraint_id)

    def deregister_constraint(self, constraint_id: str) -> Optional[DecisionConstraint]:
        with self._lock:
            return self._constraints.pop(constraint_id, None)

    def all_constraints(self) -> List[DecisionConstraint]:
        with self._lock:
            return list(self._constraints.values())

    def constraint_count(self) -> int:
        with self._lock:
            return len(self._constraints)

    # ------------------------------------------------------------------
    # Batch access
    # ------------------------------------------------------------------

    def get_objectives(self, ids: Optional[List[str]]) -> List[DecisionObjective]:
        """Return objectives filtered by *ids*, or all when *ids* is None."""
        if ids is None:
            return self.all_objectives()
        return [obj for oid in ids if (obj := self.find_objective(oid)) is not None]

    def get_constraints(self, ids: Optional[List[str]]) -> List[DecisionConstraint]:
        """Return constraints filtered by *ids*, or all when *ids* is None."""
        if ids is None:
            return self.all_constraints()
        return [c for cid in ids if (c := self.find_constraint(cid)) is not None]

    def clear(self) -> None:
        with self._lock:
            self._objectives.clear()
            self._constraints.clear()
