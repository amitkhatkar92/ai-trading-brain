"""
portfolio_objective.py — iios.portfolio.optimization
=====================================================
Portfolio optimization objective — named callable that scores a
candidate from 0.0 (worst) to 1.0 (best) against an objective.

C10 Portfolio Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from .constants import OptimizationObjective


@dataclass(frozen=True)
class ObjectiveResult:
    """Immutable result of evaluating one optimization objective."""
    objective_name: str
    objective_type: OptimizationObjective
    score:          float   # 0.0 to 1.0
    weight:         float
    message:        str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "objective_name": self.objective_name,
            "objective_type": self.objective_type.value,
            "score":          self.score,
            "weight":         self.weight,
            "message":        self.message,
        }


class PortfolioObjective:
    """
    Named, weighted, callable-based portfolio optimization objective.

    The scoring function receives ``(candidate, inputs)`` and returns a
    float in [0.0, 1.0].  Exceptions in the function are caught and
    scored as 0.0.

    Parameters
    ----------
    objective_type : OptimizationObjective enum value.
    name :           Unique, human-readable objective name.
    fn :             ``Callable[[candidate, Dict], float]``
    weight :         Relative importance (default 1.0).
    description :    Optional description.
    """

    def __init__(
        self,
        objective_type: OptimizationObjective,
        name:           str,
        fn:             Callable,
        *,
        weight:      float = 1.0,
        description: str   = "",
    ) -> None:
        if not name:
            raise ValueError("PortfolioObjective requires a non-empty name")
        if not callable(fn):
            raise TypeError(f"PortfolioObjective fn must be callable, got {type(fn)}")
        if weight < 0:
            raise ValueError(f"weight must be >= 0, got {weight}")
        self._objective_type = objective_type
        self._name           = name
        self._fn             = fn
        self._weight         = weight
        self._description    = description

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        return self._name

    @property
    def objective_type(self) -> OptimizationObjective:
        return self._objective_type

    @property
    def weight(self) -> float:
        return self._weight

    @property
    def description(self) -> str:
        return self._description

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    def score(self, candidate: Any, inputs: Dict[str, Any]) -> ObjectiveResult:
        """
        Score the candidate against this objective.

        Returns an ObjectiveResult with score clamped to [0.0, 1.0].
        Exceptions are caught and scored as 0.0.
        """
        try:
            raw = float(self._fn(candidate, inputs))
            s   = max(0.0, min(1.0, raw))
            msg = f"score={s:.4f}"
        except Exception as exc:
            s   = 0.0
            msg = f"objective raised exception: {exc}"

        return ObjectiveResult(
            objective_name = self._name,
            objective_type = self._objective_type,
            score          = s,
            weight         = self._weight,
            message        = msg,
        )

    def __repr__(self) -> str:
        return (
            f"PortfolioObjective(type={self._objective_type.value!r}, "
            f"name={self._name!r}, weight={self._weight})"
        )
