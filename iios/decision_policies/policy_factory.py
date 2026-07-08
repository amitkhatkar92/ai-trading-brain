"""iios/decision_policies/policy_factory.py — Factory helpers for creating policies inline."""
from __future__ import annotations

from typing import Callable

from .compliance.compliance_policy import StaticCompliancePolicy
from .constraints.constraint import BoundedConstraint, StaticConstraint, ThresholdConstraint
from .policy_constants import (
    ComplianceCategory,
    ConstraintType,
    DEFAULT_RULE_PRIORITY,
    RuleStatus,
)
from .policy_context import EvaluationContext
from .rules.rule import (
    CompositeRule,
    ConditionalRule,
    DynamicRule,
    PriorityRule,
    Rule,
    StaticRule,
)
from .rules.rule_group import RuleGroup
from .policy_constants import GroupOperator


class PolicyFactory:
    """Factory for creating policy artefacts from callables or configuration."""

    # ── Rules ──────────────────────────────────────────────────────────────

    @staticmethod
    def make_rule(
        rule_id:   str,
        name:      str,
        evaluator: Callable[[EvaluationContext], tuple[RuleStatus, str]],
        *,
        priority:     int = DEFAULT_RULE_PRIORITY,
        mandatory:    bool = True,
        tags:         list[str] | None = None,
        condition:    Callable[[EvaluationContext], bool] | None = None,
        dependencies: list[str] | None = None,
    ) -> StaticRule:
        return StaticRule(
            rule_id      = rule_id,
            name         = name,
            evaluator    = evaluator,
            priority     = priority,
            mandatory    = mandatory,
            tags         = tags,
            condition    = condition,
            dependencies = dependencies,
        )

    @staticmethod
    def make_dynamic_rule(
        rule_id:   str,
        name:      str,
        evaluator: Callable[[EvaluationContext], tuple[RuleStatus, str]],
        *,
        priority:  int = DEFAULT_RULE_PRIORITY,
        mandatory: bool = True,
        tags:      list[str] | None = None,
    ) -> DynamicRule:
        return DynamicRule(
            rule_id   = rule_id,
            name      = name,
            evaluator = evaluator,
            priority  = priority,
            mandatory = mandatory,
            tags      = tags,
        )

    @staticmethod
    def make_conditional_rule(
        rule_id:    str,
        name:       str,
        condition:  Callable[[EvaluationContext], bool],
        inner_rule: Rule,
        *,
        priority:   int  = DEFAULT_RULE_PRIORITY,
        mandatory:  bool = True,
    ) -> ConditionalRule:
        return ConditionalRule(
            rule_id    = rule_id,
            name       = name,
            condition  = condition,
            inner_rule = inner_rule,
            priority   = priority,
            mandatory  = mandatory,
        )

    @staticmethod
    def make_composite_rule(
        rule_id:  str,
        name:     str,
        children: list[Rule],
        *,
        operator:  str  = "and",
        priority:  int  = DEFAULT_RULE_PRIORITY,
        mandatory: bool = True,
    ) -> CompositeRule:
        return CompositeRule(
            rule_id   = rule_id,
            name      = name,
            children  = children,
            operator  = operator,
            priority  = priority,
            mandatory = mandatory,
        )

    @staticmethod
    def make_priority_rule(inner: Rule, priority: int) -> PriorityRule:
        return PriorityRule(inner=inner, priority=priority)

    @staticmethod
    def make_rule_group(
        name:      str,
        rules:     list[Rule],
        *,
        operator:  GroupOperator = GroupOperator.AND,
        mandatory: bool = True,
        tags:      list[str] | None = None,
    ) -> RuleGroup:
        return RuleGroup(
            name      = name,
            rules     = rules,
            operator  = operator,
            mandatory = mandatory,
            tags      = tags,
        )

    # ── Constraints ────────────────────────────────────────────────────────

    @staticmethod
    def make_constraint(
        constraint_id:   str,
        name:            str,
        validator:       Callable[[EvaluationContext], tuple[bool, str]],
        *,
        constraint_type: str  = "custom",
        mandatory:       bool = True,
    ) -> StaticConstraint:
        return StaticConstraint(
            constraint_id   = constraint_id,
            name            = name,
            validator       = validator,
            constraint_type = ConstraintType(constraint_type),
            mandatory       = mandatory,
        )

    @staticmethod
    def make_bounded_constraint(
        constraint_id:   str,
        name:            str,
        key:             str,
        min_val:         float | None = None,
        max_val:         float | None = None,
        *,
        constraint_type: str  = "custom",
        mandatory:       bool = True,
    ) -> BoundedConstraint:
        return BoundedConstraint(
            constraint_id   = constraint_id,
            name            = name,
            key             = key,
            min_val         = min_val,
            max_val         = max_val,
            constraint_type = ConstraintType(constraint_type),
            mandatory       = mandatory,
        )

    @staticmethod
    def make_threshold_constraint(
        constraint_id: str,
        name:          str,
        key:           str,
        threshold:     float,
        *,
        above:     bool = True,
        mandatory: bool = True,
    ) -> ThresholdConstraint:
        return ThresholdConstraint(
            constraint_id = constraint_id,
            name          = name,
            key           = key,
            threshold     = threshold,
            above         = above,
            mandatory     = mandatory,
        )

    # ── Compliance ─────────────────────────────────────────────────────────

    @staticmethod
    def make_compliance_policy(
        policy_id:  str,
        name:       str,
        checker:    Callable[[EvaluationContext], tuple[bool, str]],
        *,
        category:   str  = "internal",
        mandatory:  bool = True,
    ) -> StaticCompliancePolicy:
        return StaticCompliancePolicy(
            policy_id = policy_id,
            name      = name,
            checker   = checker,
            category  = ComplianceCategory(category),
            mandatory = mandatory,
        )
