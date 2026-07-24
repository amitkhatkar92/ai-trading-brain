"""
knowledge_policy_result.py — iios.knowledge.policies
------------------------------------------------------
PolicyRuleResult and PolicyEvaluationResult — output value objects.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .constants import GovernanceDecision, PolicyAction, PolicyDomain, PolicyType


@dataclass(frozen=True)
class PolicyRuleResult:
    """Result of evaluating a single governance rule."""
    rule_id:          str
    rule_name:        str
    passed:           bool
    action:           PolicyAction
    conditions_met:   int
    conditions_total: int
    reason:           str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id":          self.rule_id,
            "rule_name":        self.rule_name,
            "passed":           self.passed,
            "action":           self.action.value,
            "conditions_met":   self.conditions_met,
            "conditions_total": self.conditions_total,
            "reason":           self.reason,
        }


@dataclass(frozen=True)
class PolicyEvaluationResult:
    """Aggregate result of evaluating a complete governance policy."""
    policy_id:    str
    policy_name:  str
    policy_type:  PolicyType
    domain:       PolicyDomain
    decision:     GovernanceDecision
    passed:       bool
    rule_results: tuple               # Tuple[PolicyRuleResult]
    reason:       str
    metadata:     Dict[str, Any]
    evaluated_at: str                 # ISO-8601

    @classmethod
    def create(
        cls,
        *,
        policy_id:    str,
        policy_name:  str,
        policy_type:  PolicyType,
        domain:       PolicyDomain,
        decision:     GovernanceDecision,
        passed:       bool,
        rule_results: Optional[List[PolicyRuleResult]] = None,
        reason:       str                              = "",
        metadata:     Optional[Dict[str, Any]]         = None,
    ) -> "PolicyEvaluationResult":
        return cls(
            policy_id    = policy_id,
            policy_name  = policy_name,
            policy_type  = policy_type,
            domain       = domain,
            decision     = decision,
            passed       = passed,
            rule_results = tuple(rule_results or []),
            reason       = reason,
            metadata     = dict(metadata or {}),
            evaluated_at = datetime.now(tz=timezone.utc).isoformat(),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy_id":    self.policy_id,
            "policy_name":  self.policy_name,
            "policy_type":  self.policy_type.value,
            "domain":       self.domain.value,
            "decision":     self.decision.value,
            "passed":       self.passed,
            "rule_results": [r.to_dict() for r in self.rule_results],
            "reason":       self.reason,
            "metadata":     self.metadata,
            "evaluated_at": self.evaluated_at,
        }
