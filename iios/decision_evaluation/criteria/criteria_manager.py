"""iios/decision_evaluation/criteria/criteria_manager.py"""
from __future__ import annotations

import threading

from ..evaluation_constants import CriterionType
from .criteria_registry import CriteriaRegistry, get_criteria_registry
from .criteria_validator import CriteriaValidator, ValidationResult
from .criterion import Criterion


class CriteriaManager:
    """Manages criterion lifecycle: registration, retrieval, and validation."""

    def __init__(self, registry: CriteriaRegistry | None = None) -> None:
        self._registry  = registry or get_criteria_registry()
        self._validator = CriteriaValidator()
        self._lock      = threading.RLock()

    def register(self, criterion: Criterion, *, overwrite: bool = False) -> None:
        self._registry.register(criterion, overwrite=overwrite)

    def get(self, criterion_id: str) -> Criterion:
        return self._registry.get(criterion_id)

    def has(self, criterion_id: str) -> bool:
        return self._registry.has(criterion_id)

    def remove(self, criterion_id: str) -> bool:
        return self._registry.remove(criterion_id)

    def all(self) -> list[Criterion]:
        return self._registry.all()

    def by_type(self, criterion_type: CriterionType) -> list[Criterion]:
        return self._registry.by_type(criterion_type)

    def by_tag(self, tag: str) -> list[Criterion]:
        return self._registry.by_tag(tag)

    def validate(self, criteria: list[Criterion]) -> ValidationResult:
        return self._validator.validate_criteria(criteria)

    def stats(self) -> dict:
        return self._registry.stats()
