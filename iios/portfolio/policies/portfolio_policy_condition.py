"""
portfolio_policy_condition.py — iios.portfolio.policies
========================================================
Policy condition value objects and evaluation logic.

A PolicyCondition wraps a callable that evaluates against an inputs
dictionary and returns a bool.  All conditions are named so evaluation
results are fully auditable.

C10 Portfolio Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional


@dataclass(frozen=True)
class PolicyConditionResult:
    """
    Immutable result of evaluating one policy condition.

    Fields
    ------
    condition_name : Name of the condition that was evaluated.
    passed :         Whether the condition was satisfied.
    value :          The actual value extracted from the inputs (or None).
    threshold :      The threshold/target the value was compared against.
    message :        Human-readable explanation of the outcome.
    """
    condition_name: str
    passed:         bool
    value:          Any  = None
    threshold:      Any  = None
    message:        str  = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "condition_name": self.condition_name,
            "passed":         self.passed,
            "value":          self.value,
            "threshold":      self.threshold,
            "message":        self.message,
        }


class PolicyCondition:
    """
    Named callable-based policy condition.

    The evaluator function receives the inputs dict and returns a bool
    (True = condition satisfied).  If the function raises an exception
    the condition is treated as failed.

    Parameters
    ----------
    name :        Unique, human-readable condition name.
    fn :          ``Callable[[Dict], bool]`` — the evaluation function.
    threshold :   Optional reference value (stored in the result for audit).
    description : Optional human-readable description.
    """

    def __init__(
        self,
        name:        str,
        fn:          Callable[[Dict[str, Any]], bool],
        *,
        threshold:   Any = None,
        description: str = "",
    ) -> None:
        if not name:
            raise ValueError("PolicyCondition requires a non-empty name")
        if not callable(fn):
            raise TypeError(f"PolicyCondition fn must be callable, got {type(fn)}")
        self._name        = name
        self._fn          = fn
        self._threshold   = threshold
        self._description = description

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def threshold(self) -> Any:
        return self._threshold

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    def evaluate(self, inputs: Dict[str, Any]) -> PolicyConditionResult:
        """
        Evaluate the condition against the supplied inputs dict.

        Exceptions raised by the underlying function are caught and
        recorded as a failed condition so they never propagate to callers.
        """
        try:
            passed = bool(self._fn(inputs))
            msg    = "passed" if passed else "failed"
            return PolicyConditionResult(
                condition_name = self._name,
                passed         = passed,
                threshold      = self._threshold,
                message        = msg,
            )
        except Exception as exc:
            return PolicyConditionResult(
                condition_name = self._name,
                passed         = False,
                threshold      = self._threshold,
                message        = f"condition raised exception: {exc}",
            )

    def __repr__(self) -> str:
        return f"PolicyCondition(name={self._name!r})"
