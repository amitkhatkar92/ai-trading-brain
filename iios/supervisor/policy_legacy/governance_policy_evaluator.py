"""
governance_policy_evaluator.py — iios.supervisor.policy
---------------------------------------------------------
Pure structural governance policy evaluator.

Evaluates conditions and rules against the flat ``inputs`` dict.

No AI reasoning, no optimization, no execution.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 3
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Tuple

from .constants import (
    ACTION_SEVERITY,
    VERSION,
    ConditionOperator,
    EvaluationMode,
    LogicalOperator,
)
from .governance_policy import GovernancePolicy
from .governance_policy_condition import GovernancePolicyCondition
from .governance_policy_result import GovernancePolicyResult
from .governance_policy_rule import GovernancePolicyRule


class GovernancePolicyEvaluator:
    """
    Stateless evaluator for conditions, rules, and complete governance policies.

    Field paths are resolved against a flat ``inputs`` dict. Nested values
    are accessed via dot-separated ``field_path`` strings.
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def evaluate_condition(
        self,
        condition: GovernancePolicyCondition,
        inputs:    Dict[str, Any],
    ) -> bool:
        """Return True when the condition is satisfied by *inputs*."""
        value = self._resolve_field(condition.field_path, inputs)
        return self._apply_operator(
            condition.operator, value, condition.threshold,
            condition.field_path, inputs,
        )

    def evaluate_rule(
        self,
        rule:   GovernancePolicyRule,
        inputs: Dict[str, Any],
    ) -> Tuple[bool, List[str], List[str]]:
        """
        Evaluate all conditions in a rule.

        Returns
        -------
        (matched, conditions_met_ids, conditions_failed_ids)
        """
        met:    List[str] = []
        failed: List[str] = []

        for cond in rule.conditions:
            if self.evaluate_condition(cond, inputs):
                met.append(cond.condition_id)
            else:
                failed.append(cond.condition_id)

        if rule.logical_operator == LogicalOperator.ALL:
            matched = len(failed) == 0 and len(met) > 0
        else:  # ANY
            matched = len(met) > 0

        return matched, met, failed

    def evaluate_policy(
        self,
        policy: GovernancePolicy,
        inputs: Dict[str, Any],
    ) -> GovernancePolicyResult:
        """
        Evaluate all rules in a policy and return the governing result.

        For SEQUENTIAL mode: first matching rule wins.
        For all other modes: most-severe matching rule wins.
        """
        start = time.perf_counter()
        candidate_results: List[Tuple[int, str, str, List[str], List[str]]] = []

        for rule in policy.rules:
            matched, met, failed = self.evaluate_rule(rule, inputs)
            if matched:
                sev = ACTION_SEVERITY.get(rule.action, 0)
                candidate_results.append((sev, rule.rule_id, rule.name, met, failed))

                if policy.evaluation_mode == EvaluationMode.SEQUENTIAL:
                    elapsed = time.perf_counter() - start
                    return GovernancePolicyResult.create(
                        policy_id            = policy.policy_id,
                        policy_name          = policy.name,
                        policy_type          = policy.policy_type,
                        priority             = policy.priority,
                        action               = rule.action,
                        triggered_rule_id    = rule.rule_id,
                        triggered_rule_name  = rule.name,
                        conditions_met       = tuple(met),
                        conditions_failed    = tuple(failed),
                        rationale            = f"Rule '{rule.name}' matched (SEQUENTIAL)",
                        evaluation_elapsed_s = elapsed,
                    )

        elapsed = time.perf_counter() - start

        if not candidate_results:
            return GovernancePolicyResult.create(
                policy_id            = policy.policy_id,
                policy_name          = policy.name,
                policy_type          = policy.policy_type,
                priority             = policy.priority,
                action               = policy.default_action,
                rationale            = "No rule matched — default action applied",
                evaluation_elapsed_s = elapsed,
            )

        # Non-SEQUENTIAL: most severe matching rule wins
        candidate_results.sort(key=lambda x: x[0], reverse=True)
        best_sev, best_rule_id, best_rule_name, best_met, best_failed = candidate_results[0]
        action = policy.default_action
        for rule in policy.rules:
            if rule.rule_id == best_rule_id:
                action = rule.action
                break

        return GovernancePolicyResult.create(
            policy_id            = policy.policy_id,
            policy_name          = policy.name,
            policy_type          = policy.policy_type,
            priority             = policy.priority,
            action               = action,
            triggered_rule_id    = best_rule_id,
            triggered_rule_name  = best_rule_name,
            conditions_met       = tuple(best_met),
            conditions_failed    = tuple(best_failed),
            rationale            = f"Rule '{best_rule_name}' matched (PARALLEL/highest severity)",
            evaluation_elapsed_s = elapsed,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_field(field_path: str, inputs: Dict[str, Any]) -> Any:
        """Resolve a dot-separated *field_path* against *inputs*."""
        if field_path in inputs:
            return inputs[field_path]
        parts = field_path.split(".")
        node: Any = inputs
        for part in parts:
            if isinstance(node, dict) and part in node:
                node = node[part]
            else:
                return None
        return node

    @staticmethod
    def _apply_operator(
        operator:   ConditionOperator,
        value:      Any,
        threshold:  Any,
        field_path: str,
        inputs:     Dict[str, Any],
    ) -> bool:
        """Apply *operator* to (*value*, *threshold*) and return bool."""
        try:
            if operator == ConditionOperator.GT:
                return value is not None and value > threshold
            if operator == ConditionOperator.GTE:
                return value is not None and value >= threshold
            if operator == ConditionOperator.LT:
                return value is not None and value < threshold
            if operator == ConditionOperator.LTE:
                return value is not None and value <= threshold
            if operator == ConditionOperator.EQ:
                return value == threshold
            if operator == ConditionOperator.NEQ:
                return value != threshold
            if operator == ConditionOperator.IN:
                return threshold is not None and value in threshold
            if operator == ConditionOperator.NOT_IN:
                return threshold is not None and value not in threshold
            if operator == ConditionOperator.EXISTS:
                return value is not None
            if operator == ConditionOperator.NOT_EXISTS:
                return value is None
            if operator == ConditionOperator.IS_TRUE:
                return bool(value) is True
            if operator == ConditionOperator.IS_FALSE:
                return bool(value) is False
        except (TypeError, ValueError):
            return False
        return False
