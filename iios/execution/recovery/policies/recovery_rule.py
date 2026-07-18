"""
iios/execution/recovery/policies/recovery_rule.py
=================================================
RecoveryRule — the atomic decision unit of the policy framework.

A RecoveryRule contains a set of conditions (AND logic).  A policy
contains multiple rules (OR logic — any matching rule fires the policy).

C7 Execution Recovery & Resilience — Phase 1, Module 3
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from .constants import RuleConditionOperator, RecoveryStrategyType, VERSION


@dataclass(frozen=True)
class RuleCondition:
    """
    Single atomic condition evaluated against a PolicyEvaluationContext field.

    The *field* names correspond to attributes of PolicyEvaluationContext.
    """

    field:    str
    operator: RuleConditionOperator
    value:    Any                    = None   # unused for IS_TRUE / IS_FALSE

    def evaluate(self, context_value: Any) -> bool:
        """Return True if the condition holds for *context_value*."""
        op = self.operator
        if op == RuleConditionOperator.IS_TRUE:
            return bool(context_value)
        if op == RuleConditionOperator.IS_FALSE:
            return not bool(context_value)
        if context_value is None:
            return False
        if op == RuleConditionOperator.EQUALS:
            return context_value == self.value
        if op == RuleConditionOperator.NOT_EQUALS:
            return context_value != self.value
        if op == RuleConditionOperator.LESS_THAN:
            return context_value < self.value
        if op == RuleConditionOperator.LESS_EQUALS:
            return context_value <= self.value
        if op == RuleConditionOperator.GREATER_THAN:
            return context_value > self.value
        if op == RuleConditionOperator.GREATER_EQUALS:
            return context_value >= self.value
        if op == RuleConditionOperator.IN:
            return context_value in self.value
        if op == RuleConditionOperator.NOT_IN:
            return context_value not in self.value
        if op == RuleConditionOperator.CONTAINS:
            try:
                return self.value in context_value
            except TypeError:
                return False
        return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "field":    self.field,
            "operator": self.operator.value,
            "value":    str(self.value) if self.value is not None else None,
        }


@dataclass(frozen=True)
class RecoveryRule:
    """
    A named rule that evaluates a set of conditions (AND) against the context.

    When all conditions pass the rule is matched and contributes its
    *strategy_type* and *confidence_score* to the policy result.
    """

    rule_id:          str
    name:             str
    description:      str
    conditions:       Tuple[RuleCondition, ...]   # ALL must pass (AND)
    strategy_type:    RecoveryStrategyType
    confidence_score: float                        # 0.0–1.0
    priority:         int                          = 0
    version:          str                          = VERSION

    def evaluate(self, context: "PolicyEvaluationContext") -> bool:  # type: ignore[name-defined]
        """Return True if every condition passes."""
        return all(
            cond.evaluate(context.get_field(cond.field))
            for cond in self.conditions
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id":          self.rule_id,
            "name":             self.name,
            "description":      self.description,
            "conditions":       [c.to_dict() for c in self.conditions],
            "strategy_type":    self.strategy_type.value,
            "confidence_score": self.confidence_score,
            "priority":         self.priority,
        }


def make_rule(
    name: str,
    description: str,
    conditions: Tuple[RuleCondition, ...],
    strategy_type: RecoveryStrategyType,
    confidence_score: float,
    *,
    priority: int = 0,
    rule_id: Optional[str] = None,
) -> RecoveryRule:
    """Factory for RecoveryRule."""
    return RecoveryRule(
        rule_id          = rule_id or str(uuid.uuid4()),
        name             = name,
        description      = description,
        conditions       = conditions,
        strategy_type    = strategy_type,
        confidence_score = confidence_score,
        priority         = priority,
    )
