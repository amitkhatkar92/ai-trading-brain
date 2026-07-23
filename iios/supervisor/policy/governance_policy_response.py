"""
governance_policy_response.py — iios.supervisor.policy
--------------------------------------------------------
Immutable aggregate governance policy evaluation response.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 3
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from .constants import VERSION, DENY_ACTIONS, PolicyAction
from .governance_policy_result import GovernancePolicyResult


# ---------------------------------------------------------------------------
# GovernanceEvaluationSummary
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class GovernanceEvaluationSummary:
    """
    High-level aggregation of all governance policy evaluation outcomes.

    Fields
    ------
    summary_id :              Unique identifier.
    final_action :            Resolved governance outcome.
    total_policies :          Number of policies evaluated.
    approved :                Count of APPROVE outcomes.
    conditionally_approved :  Count of APPROVE_WITH_CONDITIONS outcomes.
    rejected :                Count of REJECT outcomes.
    blocked :                 Count of BLOCK outcomes.
    escalated :               Count of ESCALATE outcomes.
    deferred :                Count of DEFER outcomes.
    manual_review_required :  Count of REQUIRE_MANUAL_REVIEW outcomes.
    dominant_policy_id :      Policy that determined the final action.
    dominant_policy_name :    Human-readable dominant policy name.
    rationale :               Human-readable explanation.
    created_at :              Wall-clock creation time.
    framework_version :       Framework version string.
    """
    summary_id:             str
    final_action:           PolicyAction
    total_policies:         int
    approved:               int   = 0
    conditionally_approved: int   = 0
    rejected:               int   = 0
    blocked:                int   = 0
    escalated:              int   = 0
    deferred:               int   = 0
    manual_review_required: int   = 0
    dominant_policy_id:     str   = ""
    dominant_policy_name:   str   = ""
    rationale:              str   = ""
    created_at:             float = field(default_factory=time.time)
    framework_version:      str   = VERSION

    @classmethod
    def from_results(
        cls,
        results:              Tuple[GovernancePolicyResult, ...],
        final_action:         PolicyAction,
        dominant_policy_id:   str = "",
        dominant_policy_name: str = "",
        rationale:            str = "",
    ) -> "GovernanceEvaluationSummary":
        counts: Dict[PolicyAction, int] = {a: 0 for a in PolicyAction}
        for r in results:
            counts[r.action] = counts.get(r.action, 0) + 1
        return cls(
            summary_id             = str(uuid.uuid4()),
            final_action           = final_action,
            total_policies         = len(results),
            approved               = counts[PolicyAction.APPROVE],
            conditionally_approved = counts[PolicyAction.APPROVE_WITH_CONDITIONS],
            rejected               = counts[PolicyAction.REJECT],
            blocked                = counts[PolicyAction.BLOCK],
            escalated              = counts[PolicyAction.ESCALATE],
            deferred               = counts[PolicyAction.DEFER],
            manual_review_required = counts[PolicyAction.REQUIRE_MANUAL_REVIEW],
            dominant_policy_id     = dominant_policy_id,
            dominant_policy_name   = dominant_policy_name,
            rationale              = rationale,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary_id":             self.summary_id,
            "final_action":           self.final_action.value,
            "total_policies":         self.total_policies,
            "approved":               self.approved,
            "conditionally_approved": self.conditionally_approved,
            "rejected":               self.rejected,
            "blocked":                self.blocked,
            "escalated":              self.escalated,
            "deferred":               self.deferred,
            "manual_review_required": self.manual_review_required,
            "dominant_policy_id":     self.dominant_policy_id,
            "dominant_policy_name":   self.dominant_policy_name,
            "rationale":              self.rationale,
        }


# ---------------------------------------------------------------------------
# GovernancePolicyResponse
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class GovernancePolicyResponse:
    """
    Immutable aggregate response for a governance policy evaluation.

    Fields
    ------
    response_id :         Unique response identifier.
    request_id :          Original request identifier.
    supervision_id :      Supervision run identifier.
    subsystem_id :        Target subsystem identifier.
    final_action :        Resolved governance outcome.
    results :             Per-policy evaluation results.
    summary :             Aggregated evaluation summary.
    policies_evaluated :  Number of policies that were evaluated.
    policies_skipped :    Number of policies skipped (disabled / type-filtered).
    evaluation_elapsed_s: Total evaluation duration in seconds.
    error_message :       Non-empty when evaluation failed.
    is_success :          True when evaluation completed without error.
    responded_at :        Wall-clock response creation time.
    framework_version :   Framework version string.
    """
    response_id:          str
    request_id:           str
    supervision_id:       str
    subsystem_id:         str
    final_action:         PolicyAction
    results:              Tuple[GovernancePolicyResult, ...]
    summary:              GovernanceEvaluationSummary
    policies_evaluated:   int           = 0
    policies_skipped:     int           = 0
    evaluation_elapsed_s: float         = 0.0
    error_message:        str           = ""
    is_success:           bool          = True
    responded_at:         float         = field(default_factory=time.time)
    framework_version:    str           = VERSION

    @classmethod
    def create_success(
        cls,
        request_id:    str,
        supervision_id: str,
        subsystem_id:  str,
        final_action:  PolicyAction,
        results:       Tuple[GovernancePolicyResult, ...],
        summary:       GovernanceEvaluationSummary,
        *,
        response_id:          Optional[str] = None,
        policies_evaluated:   int          = 0,
        policies_skipped:     int          = 0,
        evaluation_elapsed_s: float        = 0.0,
    ) -> "GovernancePolicyResponse":
        return cls(
            response_id          = response_id or str(uuid.uuid4()),
            request_id           = request_id,
            supervision_id       = supervision_id,
            subsystem_id         = subsystem_id,
            final_action         = final_action,
            results              = results,
            summary              = summary,
            policies_evaluated   = policies_evaluated,
            policies_skipped     = policies_skipped,
            evaluation_elapsed_s = evaluation_elapsed_s,
            is_success           = True,
        )

    @classmethod
    def create_failure(
        cls,
        request_id:     str,
        supervision_id: str,
        subsystem_id:   str,
        error_message:  str,
        *,
        response_id:          Optional[str] = None,
        evaluation_elapsed_s: float         = 0.0,
    ) -> "GovernancePolicyResponse":
        summary = GovernanceEvaluationSummary.from_results(
            (),
            PolicyAction.BLOCK,
            rationale=f"Evaluation failed: {error_message}",
        )
        return cls(
            response_id          = response_id or str(uuid.uuid4()),
            request_id           = request_id,
            supervision_id       = supervision_id,
            subsystem_id         = subsystem_id,
            final_action         = PolicyAction.BLOCK,
            results              = (),
            summary              = summary,
            evaluation_elapsed_s = evaluation_elapsed_s,
            error_message        = error_message,
            is_success           = False,
        )

    @property
    def is_approved(self) -> bool:
        from .constants import PERMISSIVE_ACTIONS
        return self.final_action in PERMISSIVE_ACTIONS

    @property
    def is_denied(self) -> bool:
        return self.final_action in DENY_ACTIONS

    def to_dict(self) -> Dict[str, Any]:
        return {
            "response_id":          self.response_id,
            "request_id":           self.request_id,
            "supervision_id":       self.supervision_id,
            "subsystem_id":         self.subsystem_id,
            "final_action":         self.final_action.value,
            "policies_evaluated":   self.policies_evaluated,
            "policies_skipped":     self.policies_skipped,
            "evaluation_elapsed_s": self.evaluation_elapsed_s,
            "error_message":        self.error_message,
            "is_success":           self.is_success,
            "is_approved":          self.is_approved,
            "is_denied":            self.is_denied,
            "summary":              self.summary.to_dict(),
            "responded_at":         self.responded_at,
            "framework_version":    self.framework_version,
        }
