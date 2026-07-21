"""
decision_policy_response.py — iios.decision.policies
======================================================
Public response object returned by :class:`DecisionPolicyEngine.evaluate`.

C9 Decision Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from .constants import VERSION, APPROVAL_ACTIONS, DENY_ACTIONS, PolicyAction
from .decision_policy_audit  import PolicyAuditReport
from .decision_policy_result import PolicyEvaluationSummary


@dataclass(frozen=True)
class DecisionPolicyResponse:
    """
    The public output of a policy engine evaluation.

    Use :meth:`success` and :meth:`failure` to construct instances.

    Parameters
    ----------
    response_id :       Unique response identifier.
    request_id :        ID of the originating :class:`PolicyEvaluationRequest`.
    decision_id :       Decision that was evaluated.
    action :            The resolved final action.
    summary :           Aggregated evaluation summary (None on failure).
    audit_report :      Full audit trail (None on failure).
    error :             Error message if the engine raised (None on success).
    evaluation_time_s : Wall-clock time taken.
    responded_at :      Timestamp.
    framework_version : Framework version string.
    """

    response_id:       str
    request_id:        str
    decision_id:       str
    action:            PolicyAction
    summary:           Optional[PolicyEvaluationSummary] = None
    audit_report:      Optional[PolicyAuditReport]       = None
    error:             Optional[str]                     = None
    evaluation_time_s: float                             = 0.0
    responded_at:      datetime                          = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    framework_version: str                               = VERSION

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_approved(self) -> bool:
        return self.action in APPROVAL_ACTIONS

    @property
    def is_rejected(self) -> bool:
        return self.action == PolicyAction.REJECT

    @property
    def is_blocked(self) -> bool:
        return self.action == PolicyAction.BLOCK

    @property
    def is_success(self) -> bool:
        return self.error is None

    # ------------------------------------------------------------------
    # Classmethods
    # ------------------------------------------------------------------

    @classmethod
    def success(
        cls,
        request_id:        str,
        decision_id:       str,
        action:            PolicyAction,
        summary:           PolicyEvaluationSummary,
        audit_report:      PolicyAuditReport,
        *,
        evaluation_time_s: float           = 0.0,
        response_id:       Optional[str]   = None,
    ) -> "DecisionPolicyResponse":
        return cls(
            response_id       = response_id or str(uuid.uuid4()),
            request_id        = request_id,
            decision_id       = decision_id,
            action            = action,
            summary           = summary,
            audit_report      = audit_report,
            error             = None,
            evaluation_time_s = evaluation_time_s,
        )

    @classmethod
    def failure(
        cls,
        request_id:  str,
        decision_id: str,
        error:       str,
        *,
        response_id: Optional[str] = None,
    ) -> "DecisionPolicyResponse":
        return cls(
            response_id  = response_id or str(uuid.uuid4()),
            request_id   = request_id,
            decision_id  = decision_id,
            action       = PolicyAction.BLOCK,   # safe default on error
            error        = error,
        )

    def to_dict(self) -> dict:
        return {
            "response_id":       self.response_id,
            "request_id":        self.request_id,
            "decision_id":       self.decision_id,
            "action":            self.action.value,
            "is_approved":       self.is_approved,
            "is_rejected":       self.is_rejected,
            "is_blocked":        self.is_blocked,
            "is_success":        self.is_success,
            "error":             self.error,
            "evaluation_time_s": self.evaluation_time_s,
            "responded_at":      self.responded_at.isoformat(),
            "framework_version": self.framework_version,
        }
