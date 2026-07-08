"""iios/decision_evaluation/criteria/criterion.py — Criterion ABC + concrete implementations."""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Callable

from ..evaluation_constants import (
    DEFAULT_CRITERION_WEIGHT,
    CriterionDirection,
    CriterionType,
)
from ..evaluation_context import Alternative


class Criterion(ABC):
    @property
    @abstractmethod
    def criterion_id(self) -> str: ...

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    def criterion_type(self) -> CriterionType:
        return CriterionType.QUANTITATIVE

    @property
    def direction(self) -> CriterionDirection:
        return CriterionDirection.MAXIMIZE

    @property
    def weight(self) -> float:
        return DEFAULT_CRITERION_WEIGHT

    @property
    def mandatory(self) -> bool:
        return True

    @property
    def tags(self) -> list[str]:
        return []

    def is_applicable(self, alternative: Alternative) -> bool:
        return True

    @abstractmethod
    def score(self, alternative: Alternative) -> float:
        """Return raw score. Range depends on criterion type."""
        ...

    def to_dict(self) -> dict:
        return {
            "criterion_id":   self.criterion_id,
            "name":           self.name,
            "criterion_type": self.criterion_type.value,
            "direction":      self.direction.value,
            "weight":         self.weight,
            "mandatory":      self.mandatory,
            "tags":           self.tags,
        }


# ── QuantitativeCriterion ─────────────────────────────────────────────────────

class QuantitativeCriterion(Criterion):
    """Extracts a numeric value and returns it raw for normalization downstream."""

    def __init__(
        self,
        criterion_id: str,
        name:         str,
        extractor:    Callable[[Alternative], float],
        *,
        direction:    CriterionDirection = CriterionDirection.MAXIMIZE,
        weight:       float = DEFAULT_CRITERION_WEIGHT,
        mandatory:    bool  = True,
        target_val:   float | None = None,
        condition:    Callable[[Alternative], bool] | None = None,
        tags:         list[str] | None = None,
    ) -> None:
        self._id        = criterion_id
        self._name      = name
        self._extractor = extractor
        self._direction = direction
        self._weight    = weight
        self._mandatory = mandatory
        self._target    = target_val
        self._condition = condition
        self._tags      = tags or []

    @property
    def criterion_id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def criterion_type(self) -> CriterionType:
        return CriterionType.QUANTITATIVE

    @property
    def direction(self) -> CriterionDirection:
        return self._direction

    @property
    def weight(self) -> float:
        return self._weight

    @property
    def mandatory(self) -> bool:
        return self._mandatory

    @property
    def tags(self) -> list[str]:
        return list(self._tags)

    @property
    def target_val(self) -> float | None:
        return self._target

    def is_applicable(self, alternative: Alternative) -> bool:
        if self._condition is not None:
            return bool(self._condition(alternative))
        return True

    def score(self, alternative: Alternative) -> float:
        try:
            return float(self._extractor(alternative))
        except Exception:  # noqa: BLE001
            return 0.0


# ── QualitativeCriterion ──────────────────────────────────────────────────────

class QualitativeCriterion(Criterion):
    """Scorer callable returns value in [0.0, 1.0] directly."""

    def __init__(
        self,
        criterion_id: str,
        name:         str,
        scorer:       Callable[[Alternative], float],
        *,
        weight:       float = DEFAULT_CRITERION_WEIGHT,
        mandatory:    bool  = True,
        condition:    Callable[[Alternative], bool] | None = None,
        tags:         list[str] | None = None,
    ) -> None:
        self._id        = criterion_id
        self._name      = name
        self._scorer    = scorer
        self._weight    = weight
        self._mandatory = mandatory
        self._condition = condition
        self._tags      = tags or []

    @property
    def criterion_id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def criterion_type(self) -> CriterionType:
        return CriterionType.QUALITATIVE

    @property
    def direction(self) -> CriterionDirection:
        return CriterionDirection.MAXIMIZE

    @property
    def weight(self) -> float:
        return self._weight

    @property
    def mandatory(self) -> bool:
        return self._mandatory

    @property
    def tags(self) -> list[str]:
        return list(self._tags)

    def is_applicable(self, alternative: Alternative) -> bool:
        if self._condition is not None:
            return bool(self._condition(alternative))
        return True

    def score(self, alternative: Alternative) -> float:
        try:
            return max(0.0, min(1.0, float(self._scorer(alternative))))
        except Exception:  # noqa: BLE001
            return 0.0


# ── BooleanCriterion ──────────────────────────────────────────────────────────

class BooleanCriterion(Criterion):
    """Returns 1.0 if predicate is True, 0.0 otherwise."""

    def __init__(
        self,
        criterion_id: str,
        name:         str,
        predicate:    Callable[[Alternative], bool],
        *,
        weight:       float = DEFAULT_CRITERION_WEIGHT,
        mandatory:    bool  = True,
        tags:         list[str] | None = None,
    ) -> None:
        self._id        = criterion_id
        self._name      = name
        self._predicate = predicate
        self._weight    = weight
        self._mandatory = mandatory
        self._tags      = tags or []

    @property
    def criterion_id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def criterion_type(self) -> CriterionType:
        return CriterionType.BOOLEAN

    @property
    def direction(self) -> CriterionDirection:
        return CriterionDirection.MAXIMIZE

    @property
    def weight(self) -> float:
        return self._weight

    @property
    def mandatory(self) -> bool:
        return self._mandatory

    @property
    def tags(self) -> list[str]:
        return list(self._tags)

    def score(self, alternative: Alternative) -> float:
        try:
            return 1.0 if bool(self._predicate(alternative)) else 0.0
        except Exception:  # noqa: BLE001
            return 0.0


# ── CompositeCriterion ────────────────────────────────────────────────────────

class CompositeCriterion(Criterion):
    """
    Weighted average of sub-criteria scores.
    Best used when all sub-criteria return values in [0, 1].
    """

    def __init__(
        self,
        criterion_id: str,
        name:         str,
        sub_criteria: list[Criterion],
        *,
        sub_weights:  list[float] | None = None,
        weight:       float = DEFAULT_CRITERION_WEIGHT,
        mandatory:    bool  = True,
        tags:         list[str] | None = None,
    ) -> None:
        self._id          = criterion_id
        self._name        = name
        self._sub         = list(sub_criteria)
        self._sub_weights = sub_weights or [1.0] * len(sub_criteria)
        self._weight      = weight
        self._mandatory   = mandatory
        self._tags        = tags or []

    @property
    def criterion_id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def criterion_type(self) -> CriterionType:
        return CriterionType.COMPOSITE

    @property
    def direction(self) -> CriterionDirection:
        return CriterionDirection.MAXIMIZE

    @property
    def weight(self) -> float:
        return self._weight

    @property
    def mandatory(self) -> bool:
        return self._mandatory

    @property
    def tags(self) -> list[str]:
        return list(self._tags)

    def score(self, alternative: Alternative) -> float:
        if not self._sub:
            return 0.0
        total_w = sum(self._sub_weights)
        if total_w == 0:
            return 0.0
        weighted_sum = sum(
            c.score(alternative) * w
            for c, w in zip(self._sub, self._sub_weights)
        )
        return weighted_sum / total_w
