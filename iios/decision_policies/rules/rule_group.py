"""iios/decision_policies/rules/rule_group.py"""
from __future__ import annotations

import time
import uuid

from ..policy_constants import GroupOperator, RuleStatus
from ..policy_context import EvaluationContext
from .rule import Rule
from .rule_result import RuleGroupResult, RuleResult


class RuleGroup:
    """A named collection of rules evaluated together under a group operator."""

    def __init__(
        self,
        group_id:  str | None = None,
        name:      str = "",
        operator:  GroupOperator = GroupOperator.AND,
        rules:     list[Rule] | None = None,
        *,
        mandatory: bool = True,
        tags:      list[str] | None = None,
    ) -> None:
        self._group_id  = group_id or str(uuid.uuid4())
        self._name      = name
        self._operator  = operator
        self._rules:  list[Rule] = list(rules or [])
        self._mandatory = mandatory
        self._tags      = tags or []

    @property
    def group_id(self) -> str:
        return self._group_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def operator(self) -> GroupOperator:
        return self._operator

    @property
    def mandatory(self) -> bool:
        return self._mandatory

    @property
    def tags(self) -> list[str]:
        return list(self._tags)

    def add_rule(self, rule: Rule) -> None:
        self._rules.append(rule)

    def remove_rule(self, rule_id: str) -> bool:
        before = len(self._rules)
        self._rules = [r for r in self._rules if r.rule_id != rule_id]
        return len(self._rules) < before

    def get_rules(self) -> list[Rule]:
        return list(self._rules)

    def rule_count(self) -> int:
        return len(self._rules)

    def evaluate(self, context: EvaluationContext) -> RuleGroupResult:
        t0      = time.perf_counter()
        results = []
        for rule in sorted(self._rules, key=lambda r: r.priority):
            if rule.is_applicable(context):
                results.append(rule.evaluate(context))
            else:
                results.append(RuleResult(
                    rule_id   = rule.rule_id,
                    rule_name = rule.name,
                    rule_type = rule.rule_type,
                    status    = RuleStatus.SKIP,
                    reason    = "not applicable",
                ))

        status = self._aggregate(results)
        active = [r for r in results if r.status != RuleStatus.SKIP]
        score  = sum(r.score for r in active) / len(active) if active else 1.0

        return RuleGroupResult(
            group_id    = self._group_id,
            group_name  = self._name,
            operator    = self._operator,
            results     = results,
            status      = status,
            score       = score,
            duration_ms = (time.perf_counter() - t0) * 1_000,
        )

    def _aggregate(self, results: list[RuleResult]) -> RuleStatus:
        active = [r for r in results if r.status != RuleStatus.SKIP]
        if not active:
            return RuleStatus.SKIP

        if self._operator == GroupOperator.AND:
            if any(r.failed for r in active):
                return RuleStatus.FAIL
            if any(r.warned for r in active):
                return RuleStatus.WARN
            return RuleStatus.PASS

        if self._operator == GroupOperator.OR:
            if any(r.passed for r in active):
                return RuleStatus.PASS
            if any(r.warned for r in active):
                return RuleStatus.WARN
            return RuleStatus.FAIL

        # MAJORITY
        passed = sum(1 for r in active if r.passed)
        return RuleStatus.PASS if passed > len(active) / 2 else RuleStatus.FAIL

    def to_dict(self) -> dict:
        return {
            "group_id":   self._group_id,
            "name":       self._name,
            "operator":   self._operator.value,
            "rule_count": len(self._rules),
            "mandatory":  self._mandatory,
            "tags":       self._tags,
        }
