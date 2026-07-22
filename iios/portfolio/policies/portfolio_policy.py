"""
portfolio_policy.py — iios.portfolio.policies
==============================================
Core portfolio policy domain object and PolicyOutcome value object.

A PortfolioPolicy evaluates all its rules against an inputs dict.
The policy action is the most restrictive (lowest ACTION_SEVERITY)
action returned by any rule.  If the policy has no rules it returns
APPROVE (pass-through).

C10 Portfolio Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .constants import (
    ACTION_SEVERITY,
    VERSION,
    PolicyAction,
    PolicyPriority,
    PolicyStatus,
    PolicyType,
)
from .portfolio_policy_rule import PolicyRule, PolicyRuleResult


@dataclass(frozen=True)
class PolicyOutcome:
    """
    Immutable result of evaluating one PortfolioPolicy.

    Fields
    ------
    policy_id :         Identifier of the evaluated policy.
    policy_name :       Human-readable policy name.
    policy_type :       Institutional policy domain.
    action :            The governance outcome determined by this policy.
    priority :          Policy priority at the time of evaluation.
    rules_evaluated :   Number of rules that were evaluated.
    conditions_passed : Total conditions that passed across all rules.
    conditions_failed : Total conditions that failed across all rules.
    reason :            Human-readable explanation of the outcome.
    rule_results :      Tuple of individual rule outcomes.
    elapsed_s :         Wall-clock seconds consumed by evaluation.
    evaluated_at :      Wall-clock time of evaluation.
    framework_version : Framework version string.
    """
    policy_id:          str
    policy_name:        str
    policy_type:        PolicyType
    action:             PolicyAction
    priority:           PolicyPriority
    rules_evaluated:    int
    conditions_passed:  int
    conditions_failed:  int
    reason:             str
    rule_results:       tuple           # Tuple[PolicyRuleResult, ...]
    elapsed_s:          float
    evaluated_at:       float
    framework_version:  str = VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy_id":         self.policy_id,
            "policy_name":       self.policy_name,
            "policy_type":       self.policy_type.value,
            "action":            self.action.value,
            "priority":          self.priority.name,
            "rules_evaluated":   self.rules_evaluated,
            "conditions_passed": self.conditions_passed,
            "conditions_failed": self.conditions_failed,
            "reason":            self.reason,
            "elapsed_s":         self.elapsed_s,
            "evaluated_at":      self.evaluated_at,
        }


class PortfolioPolicy:
    """
    Institutional portfolio governance policy.

    A policy holds a set of rules.  During evaluation, all active rules
    are evaluated against the inputs dict.  The policy returns the most
    restrictive action (BLOCK > REJECT > … > APPROVE) across all rules.

    Parameters
    ----------
    policy_id :   Unique identifier (auto-generated UUID if omitted/empty).
    name :        Human-readable policy name.
    policy_type : Institutional policy domain.
    priority :    Evaluation priority (affects conflict resolution).
    rules :       List of PolicyRule objects.
    status :      Initial PolicyStatus (default: ACTIVE).
    version :     Policy version string.
    description : Optional human-readable description.
    metadata :    Supplementary metadata dict.
    """

    def __init__(
        self,
        policy_id:   str,
        name:        str,
        policy_type: PolicyType,
        priority:    PolicyPriority = PolicyPriority.MEDIUM,
        rules:       Optional[List[PolicyRule]] = None,
        *,
        status:      PolicyStatus = PolicyStatus.ACTIVE,
        version:     str = "1.0.0",
        description: str = "",
        metadata:    Optional[Dict[str, Any]] = None,
    ) -> None:
        self._policy_id   = policy_id or str(uuid.uuid4())
        self._name        = name
        self._policy_type = policy_type
        self._priority    = priority
        self._rules       = list(rules or [])
        self._status      = status
        self._version     = version
        self._description = description
        self._metadata    = dict(metadata or {})

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def policy_id(self) -> str:
        return self._policy_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def policy_type(self) -> PolicyType:
        return self._policy_type

    @property
    def priority(self) -> PolicyPriority:
        return self._priority

    @property
    def status(self) -> PolicyStatus:
        return self._status

    @property
    def version(self) -> str:
        return self._version

    @property
    def description(self) -> str:
        return self._description

    @property
    def is_active(self) -> bool:
        return self._status == PolicyStatus.ACTIVE

    @property
    def rule_count(self) -> int:
        return len(self._rules)

    # ------------------------------------------------------------------
    # Mutators (called by registry)
    # ------------------------------------------------------------------

    def deactivate(self) -> None:
        self._status = PolicyStatus.INACTIVE

    def activate(self) -> None:
        self._status = PolicyStatus.ACTIVE

    def deprecate(self) -> None:
        self._status = PolicyStatus.DEPRECATED

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    def evaluate(self, inputs: Dict[str, Any]) -> PolicyOutcome:
        """
        Evaluate all rules against the supplied inputs dict.

        Returns the most restrictive (lowest ACTION_SEVERITY) action
        from all rule outcomes.  If no rules exist, returns APPROVE.

        Exceptions raised by individual rules are caught; the rule is
        treated as producing a REJECT action.
        """
        start = time.monotonic()

        if not self._rules:
            elapsed = time.monotonic() - start
            return PolicyOutcome(
                policy_id         = self._policy_id,
                policy_name       = self._name,
                policy_type       = self._policy_type,
                action            = PolicyAction.APPROVE,
                priority          = self._priority,
                rules_evaluated   = 0,
                conditions_passed = 0,
                conditions_failed = 0,
                reason            = "no rules — policy trivially approves",
                rule_results      = (),
                elapsed_s         = elapsed,
                evaluated_at      = time.time(),
            )

        # Sort rules by priority (lower int = evaluated first)
        sorted_rules = sorted(self._rules, key=lambda r: r.priority)

        rule_results: List[PolicyRuleResult] = []
        for rule in sorted_rules:
            try:
                result = rule.evaluate(inputs)
                rule_results.append(result)
            except Exception as exc:
                # Treat unexpected errors as REJECT at this rule
                from .portfolio_policy_rule import PolicyRuleResult as _RR
                rule_results.append(_RR(
                    rule_id           = rule.rule_id,
                    rule_name         = rule.name,
                    action            = PolicyAction.REJECT,
                    conditions_passed = (),
                    conditions_failed = (),
                    reason            = f"rule raised exception: {exc}",
                ))

        # Determine most restrictive action
        most_restrictive = min(rule_results, key=lambda r: ACTION_SEVERITY[r.action])
        final_action     = most_restrictive.action

        total_passed = sum(len(r.conditions_passed) for r in rule_results)
        total_failed = sum(len(r.conditions_failed) for r in rule_results)

        reason = (
            f"policy '{self._name}': action={final_action.value} "
            f"from {len(rule_results)} rule(s)"
        )

        elapsed = time.monotonic() - start
        return PolicyOutcome(
            policy_id         = self._policy_id,
            policy_name       = self._name,
            policy_type       = self._policy_type,
            action            = final_action,
            priority          = self._priority,
            rules_evaluated   = len(rule_results),
            conditions_passed = total_passed,
            conditions_failed = total_failed,
            reason            = reason,
            rule_results      = tuple(rule_results),
            elapsed_s         = time.monotonic() - start,
            evaluated_at      = time.time(),
        )

    def __repr__(self) -> str:
        return (
            f"PortfolioPolicy(id={self._policy_id!r}, name={self._name!r}, "
            f"type={self._policy_type.value!r}, priority={self._priority.name}, "
            f"status={self._status.value!r}, rules={len(self._rules)})"
        )
