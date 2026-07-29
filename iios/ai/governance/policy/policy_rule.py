"""
policy_rule.py -- iios.ai.governance.policy
============================================
:class:`PolicyRule`       — individual rule within a policy.
:class:`PolicyEvaluation` — result of evaluating a single policy rule.
:class:`PolicyViolation`  — record of a policy rule violation.

A8 AI Governance Platform — Phase 3, Module 8
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Any, FrozenSet, Optional, Tuple

from ..core.governance_policy import PolicyEffect


class RuleOperator(str, Enum):
    """Comparison operator for condition evaluation."""
    EQUALS     = "equals"
    NOT_EQUALS = "not_equals"
    CONTAINS   = "contains"
    GREATER    = "greater"
    LESS       = "less"
    EXISTS     = "exists"
    NOT_EXISTS = "not_exists"


@dataclass(frozen=True)
class PolicyRule:
    """
    Immutable single rule within a :class:`GovernancePolicy`.

    ``condition_key``   — context environment key to check.
    ``operator``        — comparison operator.
    ``condition_value`` — expected value (None for EXISTS/NOT_EXISTS).
    ``effect``          — outcome when this rule matches.
    ``priority``        — higher = checked first.
    """

    rule_id:         str
    name:            str
    condition_key:   str
    operator:        RuleOperator
    condition_value: Any
    effect:          PolicyEffect
    priority:        int
    description:     str
    metadata:        FrozenSet[Tuple[str, Any]]

    @classmethod
    def create(
        cls,
        name:            str,
        condition_key:   str,
        operator:        RuleOperator,
        condition_value: Any         = None,
        effect:          PolicyEffect = PolicyEffect.DENY,
        priority:        int          = 100,
        description:     str          = "",
        **metadata: Any,
    ) -> "PolicyRule":
        return cls(
            rule_id         = str(uuid.uuid4()),
            name            = name,
            condition_key   = condition_key,
            operator        = operator,
            condition_value = condition_value,
            effect          = effect,
            priority        = priority,
            description     = description,
            metadata        = frozenset(metadata.items()),
        )

    def evaluate(self, context_value: Any) -> bool:
        """Return True if the condition is satisfied."""
        op = self.operator
        cv = self.condition_value
        if op == RuleOperator.EXISTS:
            return context_value is not None
        if op == RuleOperator.NOT_EXISTS:
            return context_value is None
        if op == RuleOperator.EQUALS:
            return context_value == cv
        if op == RuleOperator.NOT_EQUALS:
            return context_value != cv
        if op == RuleOperator.CONTAINS:
            return cv in str(context_value) if context_value is not None else False
        if op == RuleOperator.GREATER:
            return float(context_value) > float(cv)
        if op == RuleOperator.LESS:
            return float(context_value) < float(cv)
        return False


@dataclass(frozen=True)
class PolicyEvaluation:
    """Immutable result of evaluating one policy against a context."""

    evaluation_id: str
    policy_id:     str
    matched:       bool
    effect:        PolicyEffect
    rule_results:  FrozenSet[Tuple[str, bool]]   # (rule_id, matched)
    evaluated_at:  float
    notes:         str

    @classmethod
    def build(
        cls,
        policy_id:    str,
        matched:      bool,
        effect:       PolicyEffect,
        rule_results: FrozenSet[Tuple[str, bool]] = frozenset(),
        notes:        str = "",
    ) -> "PolicyEvaluation":
        return cls(
            evaluation_id = str(uuid.uuid4()),
            policy_id     = policy_id,
            matched       = matched,
            effect        = effect,
            rule_results  = frozenset(rule_results),
            evaluated_at  = time.time(),
            notes         = notes,
        )


@dataclass(frozen=True)
class PolicyViolation:
    """Immutable record of a policy violation."""

    violation_id:  str
    policy_id:     str
    principal_id:  str
    action:        str
    resource:      str
    severity:      str
    description:   str
    occurred_at:   float

    @classmethod
    def create(
        cls,
        policy_id:    str,
        principal_id: str,
        action:       str,
        resource:     str,
        severity:     str = "high",
        description:  str = "",
    ) -> "PolicyViolation":
        return cls(
            violation_id = str(uuid.uuid4()),
            policy_id    = policy_id,
            principal_id = principal_id,
            action       = action,
            resource     = resource,
            severity     = severity,
            description  = description,
            occurred_at  = time.time(),
        )
