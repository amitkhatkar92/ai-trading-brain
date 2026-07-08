"""iios/decision_policies/rules/rule_engine.py — Top-level rule evaluation orchestrator."""
from __future__ import annotations

from ..policy_constants import DEFAULT_MAX_PARALLEL_RULES, RuleStatus
from ..policy_context import EvaluationContext
from .rule import Rule
from .rule_executor import RuleExecutor
from .rule_group import RuleGroup
from .rule_registry import RuleRegistry, get_rule_registry
from .rule_result import RuleGroupResult, RuleResult


class RuleEngine:
    """Orchestrates rule and rule-group evaluation against an EvaluationContext."""

    def __init__(
        self,
        registry:    RuleRegistry | None = None,
        *,
        parallel:    bool = False,
        max_workers: int  = DEFAULT_MAX_PARALLEL_RULES,
    ) -> None:
        self._registry = registry or get_rule_registry()
        self._executor = RuleExecutor(max_workers=max_workers, parallel=parallel)

    # ── Core evaluation ────────────────────────────────────────────────────

    def evaluate_rules(
        self,
        rules:   list[Rule],
        context: EvaluationContext,
    ) -> list[RuleResult]:
        available = {r.rule_id: r for r in self._registry.all_rules()}
        return self._executor.execute(rules, context, available=available)

    def evaluate_group(
        self,
        group:   RuleGroup,
        context: EvaluationContext,
    ) -> RuleGroupResult:
        return group.evaluate(context)

    def evaluate_all_registered(
        self,
        context: EvaluationContext,
    ) -> list[RuleResult]:
        return self.evaluate_rules(self._registry.all_rules(), context)

    def evaluate_all_groups(
        self,
        context: EvaluationContext,
    ) -> list[RuleGroupResult]:
        return [self.evaluate_group(g, context) for g in self._registry.all_groups()]

    def evaluate_by_tags(
        self,
        tags:    list[str],
        context: EvaluationContext,
    ) -> list[RuleResult]:
        seen:   set[str]  = set()
        unique: list[Rule] = []
        for tag in tags:
            for rule in self._registry.rules_by_tag(tag):
                if rule.rule_id not in seen:
                    seen.add(rule.rule_id)
                    unique.append(rule)
        return self.evaluate_rules(unique, context)

    # ── Summary ────────────────────────────────────────────────────────────

    def summary(self, results: list[RuleResult]) -> dict:
        total   = len(results)
        passed  = sum(1 for r in results if r.passed)
        failed  = sum(1 for r in results if r.failed)
        warned  = sum(1 for r in results if r.warned)
        skipped = sum(1 for r in results if r.status == RuleStatus.SKIP)
        errored = sum(1 for r in results if r.status == RuleStatus.ERROR)
        avg     = sum(r.score for r in results) / total if total > 0 else 1.0
        return {
            "total":     total,
            "passed":    passed,
            "failed":    failed,
            "warned":    warned,
            "skipped":   skipped,
            "errored":   errored,
            "avg_score": avg,
        }
