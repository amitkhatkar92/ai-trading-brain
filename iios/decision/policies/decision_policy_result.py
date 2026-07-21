"""
decision_policy_result.py — iios.decision.policies
====================================================
Result value objects produced by policy evaluation.

  PolicyRuleResult        — outcome of a single rule
  SinglePolicyResult      — outcome of a single policy
  PolicyEvaluationSummary — aggregated outcome of all policies

C9 Decision Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Tuple

from .constants import (
    VERSION,
    APPROVAL_ACTIONS,
    DENY_ACTIONS,
    ESCALATION_ACTIONS,
    ConflictResolutionStrategy,
    PolicyAction,
    PolicyPriority,
    PolicyType,
)


@dataclass(frozen=True)
class PolicyRuleResult:
    """Result of evaluating a single :class:`PolicyRule`."""

    rule_id:             str
    rule_name:           str
    triggered:           bool
    action:              Optional[PolicyAction]
    reason:              str   = ""
    conditions_met:      int   = 0
    conditions_evaluated: int  = 0
    weight:              float = 1.0


@dataclass(frozen=True)
class SinglePolicyResult:
    """
    Outcome of evaluating a single :class:`DecisionPolicy` against a context.
    """

    result_id:         str
    policy_id:         str
    policy_name:       str
    policy_type:       PolicyType
    priority:          PolicyPriority
    action:            PolicyAction
    conditions_met:    int
    conditions_total:  int
    rule_results:      Tuple[PolicyRuleResult, ...]
    reason:            str
    evaluation_time_s: float
    evaluated_at:      datetime
    metadata:          dict     = field(default_factory=dict)
    framework_version: str      = VERSION

    @property
    def is_approved(self) -> bool:
        return self.action in APPROVAL_ACTIONS

    @property
    def is_denied(self) -> bool:
        return self.action in DENY_ACTIONS

    @property
    def is_blocked(self) -> bool:
        return self.action == PolicyAction.BLOCK

    @property
    def is_rejected(self) -> bool:
        return self.action == PolicyAction.REJECT

    @property
    def is_escalated(self) -> bool:
        return self.action in ESCALATION_ACTIONS


@dataclass(frozen=True)
class PolicyEvaluationSummary:
    """
    Aggregated outcome of evaluating all applicable policies.

    This is the primary output of :class:`DecisionPolicyManager.evaluate`.
    """

    summary_id:                    str
    request_id:                    str
    decision_id:                   str
    final_action:                  PolicyAction
    policy_results:                Tuple[SinglePolicyResult, ...]
    total_evaluated:               int
    approved_count:                int
    rejected_count:                int
    blocked_count:                 int
    escalated_count:               int
    deferred_count:                int
    manual_review_count:           int
    conditions:                    Tuple[str, ...]   # for APPROVE_WITH_CONDITIONS
    conflict_resolution_applied:   bool
    conflict_resolution_strategy:  ConflictResolutionStrategy
    evaluation_time_s:             float
    coverage:                      float             # evaluated / registered
    evaluated_at:                  datetime
    framework_version:             str               = VERSION

    # ------------------------------------------------------------------
    # Convenience properties
    # ------------------------------------------------------------------

    @property
    def is_approved(self) -> bool:
        return self.final_action in APPROVAL_ACTIONS

    @property
    def is_rejected(self) -> bool:
        return self.final_action == PolicyAction.REJECT

    @property
    def is_blocked(self) -> bool:
        return self.final_action == PolicyAction.BLOCK

    @property
    def requires_escalation(self) -> bool:
        return self.final_action in ESCALATION_ACTIONS

    @property
    def has_conditions(self) -> bool:
        return bool(self.conditions)

    def to_dict(self) -> dict:
        return {
            "summary_id":                   self.summary_id,
            "request_id":                   self.request_id,
            "decision_id":                  self.decision_id,
            "final_action":                 self.final_action.value,
            "total_evaluated":              self.total_evaluated,
            "approved_count":               self.approved_count,
            "rejected_count":               self.rejected_count,
            "blocked_count":                self.blocked_count,
            "escalated_count":              self.escalated_count,
            "deferred_count":               self.deferred_count,
            "manual_review_count":          self.manual_review_count,
            "conditions":                   list(self.conditions),
            "conflict_resolution_applied":  self.conflict_resolution_applied,
            "conflict_resolution_strategy": self.conflict_resolution_strategy.value,
            "evaluation_time_s":            self.evaluation_time_s,
            "coverage":                     self.coverage,
            "evaluated_at":                 self.evaluated_at.isoformat(),
            "framework_version":            self.framework_version,
        }
