"""
workflow_policy_response.py — iios.workflow.policies
-----------------------------------------------------
WorkflowPolicyResponse — the final governance output of the
Governance Policy Framework evaluation.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 3
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .constants import GovernanceDecision, PolicyAction, action_to_decision
from .workflow_policy_request import WorkflowPolicyRequest
from .workflow_policy_result import WorkflowPolicyResult


@dataclass(frozen=True)
class WorkflowPolicyResponse:
    """
    Immutable governance policy evaluation response.

    The engine always returns a WorkflowPolicyResponse — never raises
    for governance-level decisions.  A rejection or block is expressed
    as a decision, not an exception.

    Fields:
        decision           — final governance decision
        winning_action     — the PolicyAction that determined the decision
        policy_results     — results from every policy evaluated
        conditions_applied — human-readable conditions attached to decision
        audit_id           — ID of the generated audit record
        reasoning          — explanation of the final decision
        policies_evaluated — number of policies evaluated
        evaluation_time_ms — total evaluation time
    """
    response_id:        str
    request_id:         str
    workflow_id:        str
    decision:           GovernanceDecision
    winning_action:     PolicyAction
    policy_results:     tuple                     # Tuple[WorkflowPolicyResult, ...]
    conditions_applied: List[str]
    audit_id:           str
    reasoning:          str
    policies_evaluated: int
    evaluation_time_ms: float
    metadata:           Dict[str, Any]
    created_at:         str

    # ----------------------------------------------------------------
    # Factories
    # ----------------------------------------------------------------

    @classmethod
    def approved(
        cls,
        request:    WorkflowPolicyRequest,
        results:    List[WorkflowPolicyResult],
        *,
        reasoning:          str               = "All governance policies approved",
        audit_id:           str               = "",
        conditions_applied: List[str]         = None,
        evaluation_time_ms: float             = 0.0,
        metadata:           Optional[Dict[str, Any]] = None,
    ) -> "WorkflowPolicyResponse":
        return cls._make(
            request, results,
            action             = PolicyAction.APPROVE,
            reasoning          = reasoning,
            audit_id           = audit_id,
            conditions_applied = conditions_applied or [],
            evaluation_time_ms = evaluation_time_ms,
            metadata           = metadata,
        )

    @classmethod
    def approved_with_conditions(
        cls,
        request:    WorkflowPolicyRequest,
        results:    List[WorkflowPolicyResult],
        conditions: List[str],
        *,
        reasoning:          str               = "Approved with governance conditions",
        audit_id:           str               = "",
        evaluation_time_ms: float             = 0.0,
        metadata:           Optional[Dict[str, Any]] = None,
    ) -> "WorkflowPolicyResponse":
        return cls._make(
            request, results,
            action             = PolicyAction.APPROVE_WITH_CONDITIONS,
            reasoning          = reasoning,
            audit_id           = audit_id,
            conditions_applied = conditions,
            evaluation_time_ms = evaluation_time_ms,
            metadata           = metadata,
        )

    @classmethod
    def rejected(
        cls,
        request:    WorkflowPolicyRequest,
        results:    List[WorkflowPolicyResult],
        reason:     str,
        *,
        audit_id:           str               = "",
        evaluation_time_ms: float             = 0.0,
        metadata:           Optional[Dict[str, Any]] = None,
    ) -> "WorkflowPolicyResponse":
        return cls._make(
            request, results,
            action             = PolicyAction.REJECT,
            reasoning          = reason,
            audit_id           = audit_id,
            conditions_applied = [],
            evaluation_time_ms = evaluation_time_ms,
            metadata           = metadata,
        )

    @classmethod
    def blocked(
        cls,
        request:    WorkflowPolicyRequest,
        results:    List[WorkflowPolicyResult],
        reason:     str,
        *,
        audit_id:           str               = "",
        evaluation_time_ms: float             = 0.0,
        metadata:           Optional[Dict[str, Any]] = None,
    ) -> "WorkflowPolicyResponse":
        return cls._make(
            request, results,
            action             = PolicyAction.BLOCK,
            reasoning          = reason,
            audit_id           = audit_id,
            conditions_applied = [],
            evaluation_time_ms = evaluation_time_ms,
            metadata           = metadata,
        )

    @classmethod
    def emergency_stopped(
        cls,
        request:    WorkflowPolicyRequest,
        results:    List[WorkflowPolicyResult],
        reason:     str,
        *,
        audit_id:           str               = "",
        evaluation_time_ms: float             = 0.0,
        metadata:           Optional[Dict[str, Any]] = None,
    ) -> "WorkflowPolicyResponse":
        return cls._make(
            request, results,
            action             = PolicyAction.EMERGENCY_STOP,
            reasoning          = reason,
            audit_id           = audit_id,
            conditions_applied = [],
            evaluation_time_ms = evaluation_time_ms,
            metadata           = metadata,
        )

    @classmethod
    def _make(
        cls,
        request:    WorkflowPolicyRequest,
        results:    List[WorkflowPolicyResult],
        *,
        action:             PolicyAction,
        reasoning:          str,
        audit_id:           str,
        conditions_applied: List[str],
        evaluation_time_ms: float,
        metadata:           Optional[Dict[str, Any]],
    ) -> "WorkflowPolicyResponse":
        return cls(
            response_id        = f"presp-{uuid.uuid4().hex[:12]}",
            request_id         = request.request_id,
            workflow_id        = request.workflow_id,
            decision           = action_to_decision(action),
            winning_action     = action,
            policy_results     = tuple(results),
            conditions_applied = list(conditions_applied),
            audit_id           = audit_id,
            reasoning          = reasoning,
            policies_evaluated = len(results),
            evaluation_time_ms = round(evaluation_time_ms, 3),
            metadata           = dict(metadata or {}),
            created_at         = datetime.now(tz=timezone.utc).isoformat(),
        )

    # ----------------------------------------------------------------
    # Properties
    # ----------------------------------------------------------------

    @property
    def is_approved(self) -> bool:
        return self.decision in (
            GovernanceDecision.APPROVED,
            GovernanceDecision.APPROVED_WITH_CONDITIONS,
        )

    @property
    def is_rejected(self) -> bool:
        return self.decision == GovernanceDecision.REJECTED

    @property
    def is_blocked(self) -> bool:
        return self.decision == GovernanceDecision.BLOCKED

    @property
    def requires_approval(self) -> bool:
        return self.decision in (
            GovernanceDecision.REQUIRES_MANUAL_APPROVAL,
            GovernanceDecision.REQUIRES_EXECUTIVE_APPROVAL,
        )

    @property
    def is_emergency_stop(self) -> bool:
        return self.decision == GovernanceDecision.EMERGENCY_STOPPED

    @property
    def is_escalated(self) -> bool:
        return self.decision == GovernanceDecision.ESCALATED

    @property
    def can_proceed(self) -> bool:
        """True if workflow MAY proceed (approved or approved with conditions)."""
        return self.is_approved

    # ----------------------------------------------------------------
    # Serialization
    # ----------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "response_id":        self.response_id,
            "request_id":         self.request_id,
            "workflow_id":        self.workflow_id,
            "decision":           self.decision.value,
            "winning_action":     self.winning_action.value,
            "policies_evaluated": self.policies_evaluated,
            "conditions_applied": self.conditions_applied,
            "audit_id":           self.audit_id,
            "reasoning":          self.reasoning,
            "evaluation_time_ms": self.evaluation_time_ms,
            "is_approved":        self.is_approved,
            "is_rejected":        self.is_rejected,
            "is_blocked":         self.is_blocked,
            "is_emergency_stop":  self.is_emergency_stop,
            "requires_approval":  self.requires_approval,
            "can_proceed":        self.can_proceed,
            "created_at":         self.created_at,
            "policy_results":     [r.to_dict() for r in self.policy_results],
        }
