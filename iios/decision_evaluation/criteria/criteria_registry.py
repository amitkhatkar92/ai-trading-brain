"""iios/decision_evaluation/criteria/criteria_registry.py"""
from __future__ import annotations

import threading

from ..evaluation_constants import CriterionType, MAX_CRITERIA_IN_REGISTRY
from ..evaluation_exceptions import (
    CriterionAlreadyExistsError,
    CriterionNotFoundError,
    RegistryOverflowError,
)
from .criterion import Criterion


class CriteriaRegistry:
    """Thread-safe registry for Criterion instances."""

    def __init__(self) -> None:
        self._criteria: dict[str, Criterion] = {}
        self._lock      = threading.RLock()

    def register(self, criterion: Criterion, *, overwrite: bool = False) -> None:
        with self._lock:
            if not overwrite and criterion.criterion_id in self._criteria:
                raise CriterionAlreadyExistsError(criterion.criterion_id)
            if len(self._criteria) >= MAX_CRITERIA_IN_REGISTRY:
                raise RegistryOverflowError(MAX_CRITERIA_IN_REGISTRY)
            self._criteria[criterion.criterion_id] = criterion

    def get(self, criterion_id: str) -> Criterion:
        with self._lock:
            if criterion_id not in self._criteria:
                raise CriterionNotFoundError(criterion_id)
            return self._criteria[criterion_id]

    def has(self, criterion_id: str) -> bool:
        with self._lock:
            return criterion_id in self._criteria

    def remove(self, criterion_id: str) -> bool:
        with self._lock:
            if criterion_id in self._criteria:
                del self._criteria[criterion_id]
                return True
            return False

    def all(self) -> list[Criterion]:
        with self._lock:
            return list(self._criteria.values())

    def by_type(self, criterion_type: CriterionType) -> list[Criterion]:
        with self._lock:
            return [c for c in self._criteria.values() if c.criterion_type == criterion_type]

    def by_tag(self, tag: str) -> list[Criterion]:
        with self._lock:
            return [c for c in self._criteria.values() if tag in c.tags]

    def stats(self) -> dict:
        with self._lock:
            return {"total_criteria": len(self._criteria)}


_registry: CriteriaRegistry | None = None
_lock = threading.Lock()


def get_criteria_registry() -> CriteriaRegistry:
    global _registry
    if _registry is None:
        with _lock:
            if _registry is None:
                _registry = CriteriaRegistry()
    return _registry


def reset_criteria_registry() -> None:
    global _registry
    with _lock:
        _registry = None
