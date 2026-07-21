"""
decision_policy_condition.py — iios.decision.policies
=======================================================
A single evaluable policy condition.

Conditions compare a value extracted from a PolicyEvaluationContext
against a threshold using a built-in operator, or delegate to a
custom callable.

C9 Decision Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from .constants import PolicyConditionOperator


def _navigate(data: dict, path: str, default: Any = None) -> Any:
    """Navigate a dotted path through nested dicts.

    Example: _navigate({"a": {"b": 3}}, "a.b") == 3
    """
    current: Any = data
    for key in path.split("."):
        if not isinstance(current, dict):
            return default
        current = current.get(key)
        if current is None:
            return default
    return current


@dataclass
class PolicyCondition:
    """
    A single policy condition that maps a context field to a comparison.

    Parameters
    ----------
    condition_id : Unique identifier.
    name :         Human-readable name.
    field_path :   Dotted path into the evaluation context data dict,
                   e.g. ``"inputs.risk_score"`` or
                   ``"snapshots.execution_risk.var_pct"``.
    operator :     Comparison operator.
    threshold :    Value to compare against (ignored for EXISTS/NOT_EXISTS).
    description :  Optional human-readable description.
    weight :       Relative importance (used by WEIGHTED chains).
    """

    condition_id: str
    name:         str
    field_path:   str
    operator:     PolicyConditionOperator
    threshold:    Any                                   = None
    description:  str                                   = ""
    weight:       float                                 = 1.0
    # Optional callable override — excluded from equality/hash
    _custom_evaluator: Optional[Callable[[dict], bool]] = field(
        default=None, repr=False, compare=False
    )

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    def evaluate(self, context_data: dict) -> bool:
        """Return ``True`` when the condition is satisfied.

        Parameters
        ----------
        context_data : Flat/nested dict returned by
                       ``PolicyEvaluationContext.to_dict()``.
        """
        if self._custom_evaluator is not None:
            try:
                return bool(self._custom_evaluator(context_data))
            except Exception:
                return False

        op = self.operator

        # Existence checks — no value extraction needed
        if op == PolicyConditionOperator.EXISTS:
            return _navigate(context_data, self.field_path) is not None
        if op == PolicyConditionOperator.NOT_EXISTS:
            return _navigate(context_data, self.field_path) is None

        value = _navigate(context_data, self.field_path)
        if value is None:
            return False

        try:
            if op == PolicyConditionOperator.EQ:
                return value == self.threshold
            if op == PolicyConditionOperator.NE:
                return value != self.threshold
            if op == PolicyConditionOperator.IN:
                return value in self.threshold
            if op == PolicyConditionOperator.NOT_IN:
                return value not in self.threshold
            # Numeric comparisons
            v = float(value)
            t = float(self.threshold)
            if op == PolicyConditionOperator.LT:
                return v < t
            if op == PolicyConditionOperator.LTE:
                return v <= t
            if op == PolicyConditionOperator.GT:
                return v > t
            if op == PolicyConditionOperator.GTE:
                return v >= t
        except (TypeError, ValueError):
            return False

        return False

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        name:         str,
        field_path:   str,
        operator:     PolicyConditionOperator,
        threshold:    Any                              = None,
        *,
        condition_id: Optional[str]                   = None,
        description:  str                              = "",
        weight:       float                            = 1.0,
        custom_evaluator: Optional[Callable[[dict], bool]] = None,
    ) -> "PolicyCondition":
        """Create a new :class:`PolicyCondition`."""
        return cls(
            condition_id      = condition_id or str(uuid.uuid4()),
            name              = name,
            field_path        = field_path,
            operator          = operator,
            threshold         = threshold,
            description       = description,
            weight            = weight,
            _custom_evaluator = custom_evaluator,
        )
