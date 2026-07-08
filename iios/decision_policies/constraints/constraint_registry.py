"""iios/decision_policies/constraints/constraint_registry.py"""
from __future__ import annotations

import threading

from ..policy_constants import MAX_CONSTRAINTS_PER_EVAL
from ..policy_exceptions import (
    ConstraintAlreadyExistsError,
    ConstraintNotFoundError,
    RegistryOverflowError,
)
from .constraint import Constraint


class ConstraintRegistry:
    """Thread-safe registry for Constraint instances."""

    def __init__(self) -> None:
        self._constraints: dict[str, Constraint] = {}
        self._lock = threading.RLock()

    def register(self, constraint: Constraint, *, overwrite: bool = False) -> None:
        with self._lock:
            if not overwrite and constraint.constraint_id in self._constraints:
                raise ConstraintAlreadyExistsError(constraint.constraint_id)
            if len(self._constraints) >= MAX_CONSTRAINTS_PER_EVAL:
                raise RegistryOverflowError(MAX_CONSTRAINTS_PER_EVAL)
            self._constraints[constraint.constraint_id] = constraint

    def get(self, constraint_id: str) -> Constraint:
        with self._lock:
            if constraint_id not in self._constraints:
                raise ConstraintNotFoundError(constraint_id)
            return self._constraints[constraint_id]

    def has(self, constraint_id: str) -> bool:
        with self._lock:
            return constraint_id in self._constraints

    def remove(self, constraint_id: str) -> bool:
        with self._lock:
            if constraint_id in self._constraints:
                del self._constraints[constraint_id]
                return True
            return False

    def all(self) -> list[Constraint]:
        with self._lock:
            return list(self._constraints.values())

    def by_type(self, constraint_type: str) -> list[Constraint]:
        with self._lock:
            return [c for c in self._constraints.values()
                    if c.constraint_type.value == constraint_type]

    def stats(self) -> dict:
        with self._lock:
            return {"total_constraints": len(self._constraints)}


# ── Module-level singleton ────────────────────────────────────────────────────

_registry: ConstraintRegistry | None = None
_lock = threading.Lock()


def get_constraint_registry() -> ConstraintRegistry:
    global _registry
    if _registry is None:
        with _lock:
            if _registry is None:
                _registry = ConstraintRegistry()
    return _registry


def reset_constraint_registry() -> None:
    global _registry
    with _lock:
        _registry = None
