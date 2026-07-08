"""iios/decision_optimization/objectives/objective_registry.py"""
from __future__ import annotations

import threading

from ..optimization_constants import MAX_OBJECTIVES_IN_REGISTRY
from ..optimization_exceptions import (
    ObjectiveAlreadyExistsError,
    ObjectiveNotFoundError,
    RegistryOverflowError,
)
from .objective import Objective


class ObjectiveRegistry:
    """Thread-safe registry for Objective instances."""

    def __init__(self) -> None:
        self._objectives: dict[str, Objective] = {}
        self._lock        = threading.RLock()

    def register(self, objective: Objective, *, overwrite: bool = False) -> None:
        with self._lock:
            if not overwrite and objective.objective_id in self._objectives:
                raise ObjectiveAlreadyExistsError(objective.objective_id)
            if len(self._objectives) >= MAX_OBJECTIVES_IN_REGISTRY:
                raise RegistryOverflowError(MAX_OBJECTIVES_IN_REGISTRY)
            self._objectives[objective.objective_id] = objective

    def get(self, objective_id: str) -> Objective:
        with self._lock:
            if objective_id not in self._objectives:
                raise ObjectiveNotFoundError(objective_id)
            return self._objectives[objective_id]

    def has(self, objective_id: str) -> bool:
        with self._lock:
            return objective_id in self._objectives

    def remove(self, objective_id: str) -> bool:
        with self._lock:
            if objective_id in self._objectives:
                del self._objectives[objective_id]
                return True
            return False

    def all(self) -> list[Objective]:
        with self._lock:
            return list(self._objectives.values())

    def by_tag(self, tag: str) -> list[Objective]:
        with self._lock:
            return [o for o in self._objectives.values() if tag in o.tags]

    def stats(self) -> dict:
        with self._lock:
            return {"total_objectives": len(self._objectives)}


_registry: ObjectiveRegistry | None = None
_lock     = threading.Lock()


def get_objective_registry() -> ObjectiveRegistry:
    global _registry
    if _registry is None:
        with _lock:
            if _registry is None:
                _registry = ObjectiveRegistry()
    return _registry


def reset_objective_registry() -> None:
    global _registry
    with _lock:
        _registry = None
