"""iios/decision_optimization/objectives/objective_function.py — Callable-based objective."""
from __future__ import annotations

from typing import Callable

from ..optimization_constants import DEFAULT_OBJECTIVE_WEIGHT, ObjectiveType
from ..optimization_context import Candidate
from .objective import Objective


class FunctionObjective(Objective):
    """
    Objective driven by a user-supplied callable.
    The callable receives a Candidate and returns a float.
    """

    def __init__(
        self,
        objective_id: str,
        name:         str,
        evaluator:    Callable[[Candidate], float],
        *,
        objective_type: ObjectiveType = ObjectiveType.MAXIMIZE,
        weight:         float = DEFAULT_OBJECTIVE_WEIGHT,
        priority:       int   = 0,
        target_value:   float | None = None,
        tags:           list[str] | None = None,
    ) -> None:
        self._id           = objective_id
        self._name         = name
        self._evaluator    = evaluator
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
            return float(self._evaluator(candidate))
        except Exception:  # noqa: BLE001
            return 0.0
