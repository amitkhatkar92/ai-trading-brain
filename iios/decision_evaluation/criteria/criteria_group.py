"""iios/decision_evaluation/criteria/criteria_group.py"""
from __future__ import annotations

import uuid

from ..evaluation_constants import CriterionDirection
from ..evaluation_context import Alternative
from .criterion import Criterion


class CriteriaGroup:
    """A named group of related criteria with a group-level weight."""

    def __init__(
        self,
        group_id:    str | None = None,
        name:        str        = "",
        criteria:    list[Criterion] | None = None,
        *,
        weight:      float = 1.0,
        aggregation: str   = "weighted_average",  # "weighted_average" | "min" | "max"
        tags:        list[str] | None = None,
    ) -> None:
        self._group_id   = group_id or str(uuid.uuid4())
        self._name       = name
        self._criteria   = list(criteria or [])
        self._weight     = weight
        self._aggregation = aggregation
        self._tags       = tags or []

    @property
    def group_id(self) -> str:
        return self._group_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def weight(self) -> float:
        return self._weight

    @property
    def tags(self) -> list[str]:
        return list(self._tags)

    def add(self, criterion: Criterion) -> None:
        self._criteria.append(criterion)

    def remove(self, criterion_id: str) -> bool:
        before = len(self._criteria)
        self._criteria = [c for c in self._criteria if c.criterion_id != criterion_id]
        return len(self._criteria) < before

    def get_criteria(self) -> list[Criterion]:
        return list(self._criteria)

    def criterion_count(self) -> int:
        return len(self._criteria)

    def score_group(self, alternative: Alternative) -> float:
        """Aggregate score for the group against a single alternative."""
        applicable = [c for c in self._criteria if c.is_applicable(alternative)]
        if not applicable:
            return 0.0

        raw_scores = [c.score(alternative) for c in applicable]
        weights    = [c.weight for c in applicable]
        total_w    = sum(weights)

        if self._aggregation == "min":
            return min(raw_scores)
        if self._aggregation == "max":
            return max(raw_scores)

        # weighted_average (default)
        if total_w == 0:
            return sum(raw_scores) / len(raw_scores)
        return sum(s * w for s, w in zip(raw_scores, weights)) / total_w

    def to_dict(self) -> dict:
        return {
            "group_id":       self._group_id,
            "name":           self._name,
            "weight":         self._weight,
            "aggregation":    self._aggregation,
            "criterion_count": len(self._criteria),
            "tags":           self._tags,
        }
