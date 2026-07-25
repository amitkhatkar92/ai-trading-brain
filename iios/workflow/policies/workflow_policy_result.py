"""
workflow_policy_result.py — iios.workflow.policies
---------------------------------------------------
WorkflowPolicyResult — immutable outcome of evaluating a single
WorkflowPolicy against a WorkflowPolicyContext.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 3
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .constants import PolicyAction, PolicyDomain, PolicyPriorityLevel, PolicyType


@dataclass(frozen=True)
class WorkflowPolicyResult:
    """
    Immutable result of evaluating a single governance policy.

    Captured by the PolicyEngine for each policy in the chain.
    Aggregated into the final WorkflowPolicyResponse.
    """
    result_id:       str
    policy_id:       str
    policy_name:     str
    policy_type:     PolicyType
    domain:          PolicyDomain
    priority:        PolicyPriorityLevel
    action:          PolicyAction
    matched_rule_id: Optional[str]     # None if no rule matched (default action used)
    reasoning:       str
    conditions_met:  bool              # True if any rule matched
    metadata:        Dict[str, Any]
    evaluated_at:    str

    @classmethod
    def create(
        cls,
        policy_id:       str,
        policy_name:     str,
        policy_type:     PolicyType,
        domain:          PolicyDomain,
        priority:        PolicyPriorityLevel,
        action:          PolicyAction,
        reasoning:       str,
        *,
        matched_rule_id: Optional[str]            = None,
        conditions_met:  bool                     = True,
        metadata:        Optional[Dict[str, Any]] = None,
    ) -> "WorkflowPolicyResult":
        return cls(
            result_id       = f"pres-{uuid.uuid4().hex[:10]}",
            policy_id       = policy_id,
            policy_name     = policy_name,
            policy_type     = policy_type,
            domain          = domain,
            priority        = priority,
            action          = action,
            matched_rule_id = matched_rule_id,
            reasoning       = reasoning,
            conditions_met  = conditions_met,
            metadata        = dict(metadata or {}),
            evaluated_at    = datetime.now(tz=timezone.utc).isoformat(),
        )

    @property
    def is_approval(self) -> bool:
        return self.action in (
            PolicyAction.APPROVE,
            PolicyAction.APPROVE_WITH_CONDITIONS,
        )

    @property
    def is_rejection(self) -> bool:
        return self.action in (
            PolicyAction.REJECT,
            PolicyAction.BLOCK,
            PolicyAction.EMERGENCY_STOP,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_id":       self.result_id,
            "policy_id":       self.policy_id,
            "policy_name":     self.policy_name,
            "policy_type":     self.policy_type.value,
            "domain":          self.domain.value,
            "priority":        self.priority.name,
            "action":          self.action.value,
            "matched_rule_id": self.matched_rule_id,
            "reasoning":       self.reasoning,
            "conditions_met":  self.conditions_met,
            "is_approval":     self.is_approval,
            "is_rejection":    self.is_rejection,
            "evaluated_at":    self.evaluated_at,
        }
