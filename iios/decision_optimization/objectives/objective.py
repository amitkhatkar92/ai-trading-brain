"""iios/decision_optimization/objectives/objective.py — Objective ABC + concrete types."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable

from ..optimization_constants import DEFAULT_OBJECTIVE_WEIGHT, ObjectiveType
from ..optimization_context import Candidate


class Objective(ABC):
    @property
    @abstractmethod
    def objective_id(self) -> str: ...

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    def objective_type(self) -> ObjectiveType:
        return ObjectiveType.MAXIMIZE

    @property
    def weight(self) -> float:
        return DEFAULT_OBJECTIVE_WEIGHT

    @property
    def priority(self) -> int:
        """Higher priority objectives are considered first (hierarchical mode)."""
        return 0

    @property
    def tags(self) -> list[str]:
        return []

    @property
    def target_value(self) -> float | None:
        return None

    @abstractmethod
    def evaluate(self, candidate: Candidate) -> float:
        """Return raw score. Direction interpretation is the caller's responsibility."""
        ...

    def effective_score(self, candidate: Candidate) -> float:
        """
        Adjusted score where higher always means better.
        MAXIMIZE → raw; MINIMIZE → -raw; TARGET → -|raw - target|
        """
        raw = self.evaluate(candidate)
        if self.objective_type == ObjectiveType.MINIMIZE:
            return -raw
        if self.objective_type == ObjectiveType.TARGET:
            target = self.target_value or 0.0
            return -abs(raw - target)
        return raw

    def to_dict(self) -> dict:
        return {
            "objective_id":   self.objective_id,
            "name":           self.name,
            "objective_type": self.objective_type.value,
            "weight":         self.weight,
            "priority":       self.priority,
            "tags":           self.tags,
        }


# ── ScoreObjective ────────────────────────────────────────────────────────────

class ScoreObjective(Objective):
    """Maximize (or minimize) the candidate's pre-computed evaluation_score."""

    def __init__(
        self,
        objective_id: str,
        name:         str = "score",
        *,
        objective_type: ObjectiveType = ObjectiveType.MAXIMIZE,
        weight:         float = DEFAULT_OBJECTIVE_WEIGHT,
        priority:       int   = 0,
        tags:           list[str] | None = None,
    ) -> None:
        self._id    = objective_id
        self._name  = name
        self._type  = objective_type
        self._weight = weight
        self._priority = priority
        self._tags  = tags or []

    @property
    def objective_id(self) -> str:  return self._id
    @property
    def name(self) -> str:          return self._name
    @property
    def objective_type(self) -> ObjectiveType: return self._type
    @property
    def weight(self) -> float:      return self._weight
    @property
    def priority(self) -> int:      return self._priority
    @property
    def tags(self) -> list[str]:    return list(self._tags)

    def evaluate(self, candidate: Candidate) -> float:
        return candidate.evaluation_score


# ── PayloadObjective ──────────────────────────────────────────────────────────

class PayloadObjective(Objective):
    """Extract a numeric field from candidate.payload."""

    def __init__(
        self,
        objective_id: str,
        name:         str,
        key:          str,
        *,
        objective_type: ObjectiveType = ObjectiveType.MAXIMIZE,
        weight:         float = DEFAULT_OBJECTIVE_WEIGHT,
        priority:       int   = 0,
        target_value:   float | None = None,
        tags:           list[str] | None = None,
    ) -> None:
        self._id           = objective_id
        self._name         = name
        self._key          = key
        self._type         = objective_type
        self._weight       = weight
        self._priority     = priority
        self._target_value = target_value
        self._tags         = tags or []

    @property
    def objective_id(self) -> str:    return self._id
    @property
    def name(self) -> str:            return self._name
    @property
    def objective_type(self) -> ObjectiveType: return self._type
    @property
    def weight(self) -> float:        return self._weight
    @property
    def priority(self) -> int:        return self._priority
    @property
    def target_value(self) -> float | None: return self._target_value
    @property
    def tags(self) -> list[str]:      return list(self._tags)

    def evaluate(self, candidate: Candidate) -> float:
        try:
            return float(candidate.get(self._key, 0.0))
        except Exception:  # noqa: BLE001
            return 0.0


# ── CompositeObjective ────────────────────────────────────────────────────────

class CompositeObjective(Objective):
    """Weighted average of sub-objectives (higher-level objective)."""

    def __init__(
        self,
        objective_id: str,
        name:         str,
        sub_objectives: list[Objective],
        *,
        sub_weights:  list[float] | None = None,
        weight:       float = DEFAULT_OBJECTIVE_WEIGHT,
        priority:     int   = 0,
        tags:         list[str] | None = None,
    ) -> None:
        self._id          = objective_id
        self._name        = name
        self._sub         = list(sub_objectives)
        self._sub_weights = sub_weights or [1.0] * len(sub_objectives)
        self._weight      = weight
        self._priority    = priority
        self._tags        = tags or []

    @property
    def objective_id(self) -> str:  return self._id
    @property
    def name(self) -> str:          return self._name
    @property
    def objective_type(self) -> ObjectiveType: return ObjectiveType.MAXIMIZE
    @property
    def weight(self) -> float:      return self._weight
    @property
    def priority(self) -> int:      return self._priority
    @property
    def tags(self) -> list[str]:    return list(self._tags)

    def evaluate(self, candidate: Candidate) -> float:
        if not self._sub:
            return 0.0
        total_w = sum(self._sub_weights)
        if total_w == 0:
            return 0.0
        return sum(
            o.effective_score(candidate) * w
            for o, w in zip(self._sub, self._sub_weights)
        ) / total_w
