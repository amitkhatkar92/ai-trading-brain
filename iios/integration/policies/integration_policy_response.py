"""
integration_policy_response.py — iios.integration.policies
------------------------------------------------------------
IntegrationPolicyResponse — response returned by the policy engine
after governance evaluation.

C15 Enterprise Integration & Connectivity — Phase 1, Module 3
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .integration_policy_result import GovernanceDecision


@dataclass(frozen=True)
class IntegrationPolicyResponse:
    """
    Immutable response returned by the policy engine.

    Wraps the GovernanceDecision and adds evaluation metrics and
    the audit_id that links to the audit trail record.
    """

    response_id:         str
    request_id:          str
    decision:            GovernanceDecision
    policies_evaluated:  int
    policies_approved:   int
    policies_rejected:   int
    evaluation_time_ms:  float
    audit_id:            str
    metadata:            Dict[str, Any]
    created_at:          str

    # ── factories ─────────────────────────────────────────────────────

    @classmethod
    def approved(
        cls,
        request_id:          str,
        decision:            GovernanceDecision,
        policies_evaluated:  int                      = 0,
        policies_approved:   int                      = 0,
        policies_rejected:   int                      = 0,
        evaluation_time_ms:  float                    = 0.0,
        audit_id:            str                      = "",
        metadata:            Optional[Dict[str, Any]] = None,
    ) -> "IntegrationPolicyResponse":
        return cls(
            response_id        = f"prsp-{uuid.uuid4().hex[:12]}",
            request_id         = request_id,
            decision           = decision,
            policies_evaluated = policies_evaluated,
            policies_approved  = policies_approved,
            policies_rejected  = policies_rejected,
            evaluation_time_ms = evaluation_time_ms,
            audit_id           = audit_id,
            metadata           = dict(metadata or {}),
            created_at         = datetime.now(timezone.utc).isoformat(),
        )

    @classmethod
    def rejected(
        cls,
        request_id:          str,
        decision:            GovernanceDecision,
        policies_evaluated:  int                      = 0,
        policies_approved:   int                      = 0,
        policies_rejected:   int                      = 0,
        evaluation_time_ms:  float                    = 0.0,
        audit_id:            str                      = "",
        metadata:            Optional[Dict[str, Any]] = None,
    ) -> "IntegrationPolicyResponse":
        return cls(
            response_id        = f"prsp-{uuid.uuid4().hex[:12]}",
            request_id         = request_id,
            decision           = decision,
            policies_evaluated = policies_evaluated,
            policies_approved  = policies_approved,
            policies_rejected  = policies_rejected,
            evaluation_time_ms = evaluation_time_ms,
            audit_id           = audit_id,
            metadata           = dict(metadata or {}),
            created_at         = datetime.now(timezone.utc).isoformat(),
        )

    # ── properties ────────────────────────────────────────────────────

    @property
    def is_approved(self) -> bool:
        return self.decision.approved

    @property
    def is_rejected(self) -> bool:
        return not self.decision.approved

    # ── serialisation ─────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "response_id":         self.response_id,
            "request_id":          self.request_id,
            "decision":            self.decision.to_dict(),
            "policies_evaluated":  self.policies_evaluated,
            "policies_approved":   self.policies_approved,
            "policies_rejected":   self.policies_rejected,
            "evaluation_time_ms":  self.evaluation_time_ms,
            "audit_id":            self.audit_id,
            "metadata":            self.metadata,
            "created_at":          self.created_at,
        }
