"""iios/decision_optimization/objectives/objective_manager.py"""
from __future__ import annotations

import threading

from ..optimization_context import Candidate
from ..optimization_constants import ObjectiveAggregation
from .objective import Objective
from .objective_registry import ObjectiveRegistry, get_objective_registry
from .objective_result import ObjectiveResult, build_objective_result


class ObjectiveManager:
    """Manages objective lifecycle and bulk evaluation."""

    def __init__(self, registry: ObjectiveRegistry | None = None) -> None:
        self._registry = registry or get_objective_registry()
        self._lock     = threading.RLock()

    def register(self, objective: Objective, *, overwrite: bool = False) -> None:
        self._registry.register(objective, overwrite=overwrite)

    def get(self, objective_id: str) -> Objective:
        return self._registry.get(objective_id)

    def has(self, objective_id: str) -> bool:
        return self._registry.has(objective_id)

    def remove(self, objective_id: str) -> bool:
        return self._registry.remove(objective_id)

    def all(self) -> list[Objective]:
        return self._registry.all()

    def by_tag(self, tag: str) -> list[Objective]:
        return self._registry.by_tag(tag)

    def evaluate_all(
        self,
        candidates:  list[Candidate],
        objectives:  list[Objective] | None = None,
        aggregation: ObjectiveAggregation = ObjectiveAggregation.WEIGHTED_SUM,
    ) -> ObjectiveResult:
        objs = objectives if objectives is not None else self._registry.all()
        return build_objective_result(candidates, objs, aggregation)

    def stats(self) -> dict:
        return self._registry.stats()
