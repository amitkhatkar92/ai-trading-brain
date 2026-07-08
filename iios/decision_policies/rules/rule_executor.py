"""iios/decision_policies/rules/rule_executor.py — Executes rules with dependency ordering."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed

from ..policy_constants import DEFAULT_MAX_PARALLEL_RULES, RuleStatus
from ..policy_context import EvaluationContext
from ..policy_exceptions import CircularRuleDependencyError, RuleDependencyError
from .rule import Rule
from .rule_result import RuleResult


class RuleExecutor:
    """
    Executes a list of rules, resolving dependency order and optionally
    running in parallel via a thread pool.
    """

    def __init__(
        self,
        max_workers: int  = DEFAULT_MAX_PARALLEL_RULES,
        *,
        parallel:    bool = False,
    ) -> None:
        self._max_workers = max_workers
        self._parallel    = parallel

    def execute(
        self,
        rules:     list[Rule],
        context:   EvaluationContext,
        *,
        available: dict[str, Rule] | None = None,
    ) -> list[RuleResult]:
        ordered = self._resolve_order(rules, available or {})
        if self._parallel and len(ordered) > 1:
            return self._execute_parallel(ordered, context)
        return self._execute_sequential(ordered, context)

    # ── Private helpers ────────────────────────────────────────────────────

    def _execute_sequential(
        self,
        rules:   list[Rule],
        context: EvaluationContext,
    ) -> list[RuleResult]:
        results = []
        for rule in rules:
            if not rule.is_applicable(context):
                results.append(RuleResult(
                    rule_id   = rule.rule_id,
                    rule_name = rule.name,
                    rule_type = rule.rule_type,
                    status    = RuleStatus.SKIP,
                    reason    = "not applicable",
                ))
            else:
                results.append(rule.evaluate(context))
        return results

    def _execute_parallel(
        self,
        rules:   list[Rule],
        context: EvaluationContext,
    ) -> list[RuleResult]:
        results: list[RuleResult | None] = [None] * len(rules)

        applicable = [(idx, rule) for idx, rule in enumerate(rules) if rule.is_applicable(context)]
        skipped    = {idx for idx, rule in enumerate(rules) if not rule.is_applicable(context)}

        with ThreadPoolExecutor(max_workers=self._max_workers) as pool:
            futs = {pool.submit(rule.evaluate, context): idx for idx, rule in applicable}
            for fut in as_completed(futs):
                idx = futs[fut]
                try:
                    results[idx] = fut.result()
                except Exception as exc:  # noqa: BLE001
                    rule = rules[idx]
                    results[idx] = RuleResult(
                        rule_id   = rule.rule_id,
                        rule_name = rule.name,
                        rule_type = rule.rule_type,
                        status    = RuleStatus.ERROR,
                        reason    = str(exc),
                        score     = 0.0,
                    )

        for idx in skipped:
            rule = rules[idx]
            results[idx] = RuleResult(
                rule_id   = rule.rule_id,
                rule_name = rule.name,
                rule_type = rule.rule_type,
                status    = RuleStatus.SKIP,
                reason    = "not applicable",
            )

        return results  # type: ignore[return-value]

    def _resolve_order(
        self,
        rules:     list[Rule],
        available: dict[str, Rule],
    ) -> list[Rule]:
        all_map: dict[str, Rule] = {r.rule_id: r for r in rules}
        all_map.update(available)

        # Validate all dependencies are resolvable
        for rule in rules:
            for dep in rule.dependencies:
                if dep not in all_map:
                    raise RuleDependencyError(rule.rule_id, dep)

        # Cycle detection via DFS
        visited:  set[str] = set()
        in_stack: set[str] = set()

        def _visit(rid: str) -> None:
            if rid in in_stack:
                raise CircularRuleDependencyError(rid)
            if rid in visited:
                return
            in_stack.add(rid)
            rule = all_map.get(rid)
            if rule:
                for dep in rule.dependencies:
                    _visit(dep)
            in_stack.discard(rid)
            visited.add(rid)

        for rule in rules:
            _visit(rule.rule_id)

        # Final ordering: sort by priority
        return sorted(rules, key=lambda r: r.priority)
