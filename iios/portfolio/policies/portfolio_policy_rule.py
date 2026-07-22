"""
portfolio_policy_rule.py — iios.portfolio.policies
===================================================
Policy rule — a named set of conditions with pass/fail actions.

A PolicyRule evaluates its conditions against an inputs dict.
If ALL conditions pass, ``action_on_pass`` is returned.
If ANY condition fails, ``action_on_fail`` is returned.

C10 Portfolio Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .constants import PolicyAction
from .portfolio_policy_condition import PolicyCondition, PolicyConditionResult


@dataclass(frozen=True)
class PolicyRuleResult:
    """
    Immutable result of evaluating one policy rule.

    Fields
    ------
    rule_id :            Identifier of the rule that was evaluated.
    rule_name :          Human-readable rule name.
    action :             The action determined by this rule.
    conditions_passed :  Tuple of condition results that passed.
    conditions_failed :  Tuple of condition results that failed.
    reason :             Human-readable explanation.
    elapsed_s :          Wall-clock seconds consumed by evaluation.
    """
    rule_id:            str
    rule_name:          str
    action:             PolicyAction
    conditions_passed:  tuple   # Tuple[PolicyConditionResult, ...]
    conditions_failed:  tuple   # Tuple[PolicyConditionResult, ...]
    reason:             str     = ""
    elapsed_s:          float   = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id":           self.rule_id,
            "rule_name":         self.rule_name,
            "action":            self.action.value,
            "conditions_passed": [c.to_dict() for c in self.conditions_passed],
            "conditions_failed": [c.to_dict() for c in self.conditions_failed],
            "reason":            self.reason,
            "elapsed_s":         self.elapsed_s,
        }


class PolicyRule:
    """
    Named policy rule that holds conditions and two action outcomes.

    Parameters
    ----------
    rule_id :       Unique identifier (auto-generated UUID if omitted/empty).
    name :          Human-readable rule name.
    conditions :    List of PolicyCondition objects to evaluate.
    action_on_pass: PolicyAction returned when ALL conditions pass.
    action_on_fail: PolicyAction returned when ANY condition fails.
    priority :      Integer sort key (lower = evaluated first).
    metadata :      Supplementary metadata dict.
    """

    def __init__(
        self,
        rule_id:        str,
        name:           str,
        conditions:     List[PolicyCondition],
        action_on_pass: PolicyAction = PolicyAction.APPROVE,
        action_on_fail: PolicyAction = PolicyAction.REJECT,
        *,
        priority: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self._rule_id        = rule_id or str(uuid.uuid4())
        self._name           = name
        self._conditions     = list(conditions)
        self._action_on_pass = action_on_pass
        self._action_on_fail = action_on_fail
        self._priority       = priority
        self._metadata       = dict(metadata or {})

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def rule_id(self) -> str:
        return self._rule_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def priority(self) -> int:
        return self._priority

    @property
    def action_on_pass(self) -> PolicyAction:
        return self._action_on_pass

    @property
    def action_on_fail(self) -> PolicyAction:
        return self._action_on_fail

    @property
    def condition_count(self) -> int:
        return len(self._conditions)

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    def evaluate(self, inputs: Dict[str, Any]) -> PolicyRuleResult:
        """
        Evaluate all conditions against inputs and return a PolicyRuleResult.

        If the rule has no conditions it is considered trivially passing.
        """
        start = time.monotonic()

        if not self._conditions:
            elapsed = time.monotonic() - start
            return PolicyRuleResult(
                rule_id           = self._rule_id,
                rule_name         = self._name,
                action            = self._action_on_pass,
                conditions_passed = (),
                conditions_failed = (),
                reason            = "no conditions — trivially passes",
                elapsed_s         = elapsed,
            )

        passed = []
        failed = []
        for cond in self._conditions:
            result = cond.evaluate(inputs)
            if result.passed:
                passed.append(result)
            else:
                failed.append(result)

        all_passed = len(failed) == 0
        action     = self._action_on_pass if all_passed else self._action_on_fail
        reason     = (
            f"all {len(passed)} condition(s) passed"
            if all_passed
            else f"{len(failed)} of {len(self._conditions)} condition(s) failed"
        )
        elapsed = time.monotonic() - start
        return PolicyRuleResult(
            rule_id           = self._rule_id,
            rule_name         = self._name,
            action            = action,
            conditions_passed = tuple(passed),
            conditions_failed = tuple(failed),
            reason            = reason,
            elapsed_s         = elapsed,
        )

    def __repr__(self) -> str:
        return (
            f"PolicyRule(id={self._rule_id!r}, name={self._name!r}, "
            f"conditions={len(self._conditions)})"
        )
