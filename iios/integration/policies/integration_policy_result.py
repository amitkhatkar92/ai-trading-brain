"""
integration_policy_result.py — iios.integration.policies
----------------------------------------------------------
IntegrationPolicyResult — result of evaluating a single policy.
GovernanceDecision      — final aggregated governance decision.

C15 Enterprise Integration & Connectivity — Phase 1, Module 3
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from .constants import ACTION_TO_STATUS, PolicyAction, PolicyResultStatus


@dataclass(frozen=True)
class IntegrationPolicyResult:
    """
    Immutable result of evaluating a single IntegrationPolicy.
    """

    result_id:    str
    policy_id:    str
    policy_name:  str
    action:       PolicyAction
    status:       PolicyResultStatus
    reason:       str
    fired_rules:  Tuple[str, ...]      # rule_ids that fired
    metadata:     Dict[str, Any]
    evaluated_at: str

    # ── factory ───────────────────────────────────────────────────────

    @classmethod
    def create(
        cls,
        policy_id:   str,
        policy_name: str,
        action:      PolicyAction,
        reason:      str                      = "",
        fired_rules: Optional[List[str]]      = None,
        metadata:    Optional[Dict[str, Any]] = None,
    ) -> "IntegrationPolicyResult":
        return cls(
            result_id    = f"prslt-{uuid.uuid4().hex[:12]}",
            policy_id    = policy_id,
            policy_name  = policy_name,
            action       = action,
            status       = ACTION_TO_STATUS[action],
            reason       = reason,
            fired_rules  = tuple(fired_rules or []),
            metadata     = dict(metadata     or {}),
            evaluated_at = datetime.now(timezone.utc).isoformat(),
        )

    # ── properties ────────────────────────────────────────────────────

    @property
    def is_blocking(self) -> bool:
        return self.action in (
            PolicyAction.BLOCK,
            PolicyAction.REJECT,
            PolicyAction.EMERGENCY_STOP,
        )

    @property
    def is_approved(self) -> bool:
        return self.action in (
            PolicyAction.APPROVE,
            PolicyAction.APPROVE_WITH_CONDITIONS,
        )

    # ── serialisation ─────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_id":    self.result_id,
            "policy_id":    self.policy_id,
            "policy_name":  self.policy_name,
            "action":       self.action.value,
            "status":       self.status.value,
            "reason":       self.reason,
            "fired_rules":  list(self.fired_rules),
            "metadata":     self.metadata,
            "evaluated_at": self.evaluated_at,
        }


@dataclass(frozen=True)
class GovernanceDecision:
    """
    Final governance decision aggregated across all evaluated policies.
    """

    decision_id:    str
    request_id:     str
    final_action:   PolicyAction
    final_status:   PolicyResultStatus
    policy_results: Tuple[IntegrationPolicyResult, ...]
    conditions:     Tuple[str, ...]   # conditions imposed on approval
    reasons:        Tuple[str, ...]   # reasons from blocking policies
    approved:       bool
    decided_at:     str
    metadata:       Dict[str, Any]

    # ── factory ───────────────────────────────────────────────────────

    @classmethod
    def create(
        cls,
        request_id:     str,
        final_action:   PolicyAction,
        policy_results: List[IntegrationPolicyResult],
        conditions:     Optional[List[str]]      = None,
        reasons:        Optional[List[str]]      = None,
        metadata:       Optional[Dict[str, Any]] = None,
    ) -> "GovernanceDecision":
        return cls(
            decision_id    = f"gdec-{uuid.uuid4().hex[:12]}",
            request_id     = request_id,
            final_action   = final_action,
            final_status   = ACTION_TO_STATUS[final_action],
            policy_results = tuple(policy_results),
            conditions     = tuple(conditions or []),
            reasons        = tuple(reasons    or []),
            approved       = final_action in (
                PolicyAction.APPROVE,
                PolicyAction.APPROVE_WITH_CONDITIONS,
            ),
            decided_at     = datetime.now(timezone.utc).isoformat(),
            metadata       = dict(metadata or {}),
        )

    # ── serialisation ─────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id":    self.decision_id,
            "request_id":     self.request_id,
            "final_action":   self.final_action.value,
            "final_status":   self.final_status.value,
            "policy_results": [r.to_dict() for r in self.policy_results],
            "conditions":     list(self.conditions),
            "reasons":        list(self.reasons),
            "approved":       self.approved,
            "decided_at":     self.decided_at,
            "metadata":       self.metadata,
        }
