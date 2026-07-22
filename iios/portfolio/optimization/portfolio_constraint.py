"""
portfolio_constraint.py — iios.portfolio.optimization
======================================================
Portfolio optimization constraint — named callable that checks whether
a candidate satisfies an institutional constraint.

Hard constraints mark a candidate as infeasible when violated.
Soft constraints apply a score penalty.

C10 Portfolio Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from .constants import ConstraintType


@dataclass(frozen=True)
class ConstraintResult:
    """Immutable result of evaluating one portfolio constraint."""
    constraint_name: str
    constraint_type: ConstraintType
    satisfied:       bool
    is_hard:         bool
    penalty:         float   # 0.0 if satisfied; > 0.0 if soft violation
    message:         str = ""
    value:           Any = None
    threshold:       Any = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "constraint_name": self.constraint_name,
            "constraint_type": self.constraint_type.value,
            "satisfied":       self.satisfied,
            "is_hard":         self.is_hard,
            "penalty":         self.penalty,
            "message":         self.message,
        }


class PortfolioConstraint:
    """
    Named, callable-based portfolio constraint.

    The evaluation function receives ``(candidate, inputs)`` and returns
    a bool (True = constraint satisfied).  Exceptions are caught and
    treated as a violated constraint.

    Parameters
    ----------
    constraint_type : ConstraintType enum value.
    name :            Unique, human-readable constraint name.
    fn :              ``Callable[[candidate, Dict], bool]``
    is_hard :         True → violated constraint marks candidate infeasible.
    penalty :         Score penalty applied for soft (is_hard=False) violations.
    description :     Optional description.
    """

    def __init__(
        self,
        constraint_type: ConstraintType,
        name:            str,
        fn:              Callable,
        *,
        is_hard:     bool  = True,
        penalty:     float = 0.5,
        description: str   = "",
    ) -> None:
        if not name:
            raise ValueError("PortfolioConstraint requires a non-empty name")
        if not callable(fn):
            raise TypeError(f"PortfolioConstraint fn must be callable, got {type(fn)}")
        self._constraint_type = constraint_type
        self._name            = name
        self._fn              = fn
        self._is_hard         = is_hard
        self._penalty         = penalty
        self._description     = description

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        return self._name

    @property
    def constraint_type(self) -> ConstraintType:
        return self._constraint_type

    @property
    def is_hard(self) -> bool:
        return self._is_hard

    @property
    def penalty(self) -> float:
        return self._penalty

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    def evaluate(
        self,
        candidate: Any,
        inputs:    Dict[str, Any],
    ) -> ConstraintResult:
        """
        Evaluate the constraint against the candidate and inputs.

        Exceptions are caught and treated as violated (penalty applied).
        """
        try:
            satisfied = bool(self._fn(candidate, inputs))
            msg       = "satisfied" if satisfied else f"violated — penalty={self._penalty}"
            penalty   = 0.0 if satisfied else (0.0 if self._is_hard else self._penalty)
        except Exception as exc:
            satisfied = False
            msg       = f"constraint raised exception: {exc}"
            penalty   = 0.0 if self._is_hard else self._penalty

        return ConstraintResult(
            constraint_name = self._name,
            constraint_type = self._constraint_type,
            satisfied       = satisfied,
            is_hard         = self._is_hard,
            penalty         = penalty,
            message         = msg,
        )

    def __repr__(self) -> str:
        return (
            f"PortfolioConstraint(type={self._constraint_type.value!r}, "
            f"name={self._name!r}, is_hard={self._is_hard})"
        )
