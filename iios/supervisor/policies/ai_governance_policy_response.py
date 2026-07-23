"""
ai_governance_policy_response.py — iios.supervisor.policies
-------------------------------------------------------------
Immutable aggregate governance evaluation response value objects.

Exports
-------
GovernanceDecisionSummary  — aggregated counts and dominant-policy metadata
AIGovernancePolicyResponse — full evaluation result with per-policy results

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 3
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from .constants import (
    VERSION,
    AIGovernancePolicyAction,
    DENY_ACTIONS,
    HUMAN_REVIEW_ACTIONS,
    PERMISSIVE_ACTIONS,
    STOP_ACTIONS,
)
from .ai_governance_policy_result import AIGovernancePolicyResult


# ---------------------------------------------------------------------------
# GovernanceDecisionSummary
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class GovernanceDecisionSummary:
    """
    High-level aggregation of all governance policy evaluation outcomes.

    Fields
    ------
    summary_id :                  Unique identifier.
    final_action :                Resolved governance outcome.
    total_policies :              Number of policies evaluated.
    approved :                    Count of APPROVE outcomes.
    conditionally_approved :      Count of APPROVE_WITH_CONDITIONS outcomes.
    rejected :                    Count of REJECT outcomes.
    blocked :                     Count of BLOCK outcomes.
    escalated :                   Count of ESCALATE outcomes.
    human_approval_required :     Count of REQUIRE_HUMAN_APPROVAL outcomes.
    manual_review_required :      Count of REQUIRE_MANUAL_REVIEW outcomes.
    emergency_stops :             Count of EMERGENCY_STOP outcomes.
    dominant_policy_id :          Policy that determined the final action.
    dominant_policy_name :        Human-readable dominant policy name.
    rationale :                   Human-readable explanation.
    human_oversight_required :    True when any result requires human review.
    emergency_stop_triggered :    True when any result is an emergency stop.
    created_at :                  Wall-clock creation time.
    framework_version :           Framework version string.
    """
    summary_id:               str
    final_action:             AIGovernancePolicyAction
    total_policies:           int
    approved:                 int   = 0
    conditionally_approved:   int   = 0
    rejected:                 int   = 0
    blocked:                  int   = 0
    escalated:                int   = 0
    human_approval_required:  int   = 0
    manual_review_required:   int   = 0
    emergency_stops:          int   = 0
    dominant_policy_id:       str   = ""
    dominant_policy_name:     str   = ""
    rationale:                str   = ""
    human_oversight_required: bool  = False
    emergency_stop_triggered: bool  = False
    created_at:               float = field(default_factory=time.time)
    framework_version:        str   = VERSION

    @classmethod
    def from_results(
        cls,
        results:              Tuple[AIGovernancePolicyResult, ...],
        final_action:         AIGovernancePolicyAction,
        dominant_policy_id:   str = "",
        dominant_policy_name: str = "",
        rationale:            str = "",
    ) -> "GovernanceDecisionSummary":
        counts: Dict[AIGovernancePolicyAction, int] = {a: 0 for a in AIGovernancePolicyAction}
        for r in results:
            counts[r.action] = counts.get(r.action, 0) + 1

        human_required = any(r.requires_human_approval for r in results)
        emergency      = any(r.is_emergency_stop for r in results)

        return cls(
            summary_id               = str(uuid.uuid4()),
            final_action             = final_action,
            total_policies           = len(results),
            approved                 = counts[AIGovernancePolicyAction.APPROVE],
            conditionally_approved   = counts[AIGovernancePolicyAction.APPROVE_WITH_CONDITIONS],
            rejected                 = counts[AIGovernancePolicyAction.REJECT],
            blocked                  = counts[AIGovernancePolicyAction.BLOCK],
            escalated                = counts[AIGovernancePolicyAction.ESCALATE],
            human_approval_required  = counts[AIGovernancePolicyAction.REQUIRE_HUMAN_APPROVAL],
            manual_review_required   = counts[AIGovernancePolicyAction.REQUIRE_MANUAL_REVIEW],
            emergency_stops          = counts[AIGovernancePolicyAction.EMERGENCY_STOP],
            dominant_policy_id       = dominant_policy_id,
            dominant_policy_name     = dominant_policy_name,
            rationale                = rationale,
            human_oversight_required = human_required,
            emergency_stop_triggered = emergency,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary_id":               self.summary_id,
            "final_action":             self.final_action.value,
            "total_policies":           self.total_policies,
            "approved":                 self.approved,
            "conditionally_approved":   self.conditionally_approved,
            "rejected":                 self.rejected,
            "blocked":                  self.blocked,
            "escalated":                self.escalated,
            "human_approval_required":  self.human_approval_required,
            "manual_review_required":   self.manual_review_required,
            "emergency_stops":          self.emergency_stops,
            "dominant_policy_id":       self.dominant_policy_id,
            "dominant_policy_name":     self.dominant_policy_name,
            "rationale":                self.rationale,
            "human_oversight_required": self.human_oversight_required,
            "emergency_stop_triggered": self.emergency_stop_triggered,
        }


# ---------------------------------------------------------------------------
# AIGovernancePolicyResponse
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AIGovernancePolicyResponse:
    """
    Immutable aggregate governance policy evaluation response.

    Fields
    ------
    response_id :           Unique identifier.
    request_id :            Original request identifier.
    supervision_id :        Supervision run identifier.
    subsystem_id :          Target subsystem identifier.
    final_action :          Resolved governance outcome.
    results :               Per-policy evaluation results.
    summary :               Aggregated decision summary.
    policies_evaluated :    Number of policies that ran.
    policies_skipped :      Policies skipped due to type filter or disabled.
    evaluation_elapsed_s :  Total evaluation duration in seconds.
    error_message :         Non-empty when evaluation failed structurally.
    is_success :            True when evaluation completed without error.
    responded_at :          Wall-clock response creation time.
    framework_version :     Framework version string.
    """
    response_id:          str
    request_id:           str
    supervision_id:       str
    subsystem_id:         str
    final_action:         AIGovernancePolicyAction
    results:              Tuple[AIGovernancePolicyResult, ...]
    summary:              GovernanceDecisionSummary
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
        final_action:  AIGovernancePolicyAction,
        results:       Tuple[AIGovernancePolicyResult, ...],
        summary:       GovernanceDecisionSummary,
        *,
        response_id:          Optional[str] = None,
        policies_evaluated:   int           = 0,
        policies_skipped:     int           = 0,
        evaluation_elapsed_s: float         = 0.0,
    ) -> "AIGovernancePolicyResponse":
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
    ) -> "AIGovernancePolicyResponse":
        summary = GovernanceDecisionSummary.from_results(
            (),
            AIGovernancePolicyAction.EMERGENCY_STOP,
            rationale = f"Evaluation error — emergency stop applied: {error_message}",
        )
        return cls(
            response_id          = response_id or str(uuid.uuid4()),
            request_id           = request_id,
            supervision_id       = supervision_id,
            subsystem_id         = subsystem_id,
            final_action         = AIGovernancePolicyAction.EMERGENCY_STOP,
            results              = (),
            summary              = summary,
            evaluation_elapsed_s = evaluation_elapsed_s,
            error_message        = error_message,
            is_success           = False,
        )

    # ------------------------------------------------------------------
    # Classification helpers
    # ------------------------------------------------------------------

    @property
    def is_approved(self) -> bool:
        return self.final_action in PERMISSIVE_ACTIONS

    @property
    def is_denied(self) -> bool:
        return self.final_action in DENY_ACTIONS

    @property
    def requires_human_approval(self) -> bool:
        return self.final_action in HUMAN_REVIEW_ACTIONS or self.summary.human_oversight_required

    @property
    def is_emergency_stop(self) -> bool:
        return self.final_action in STOP_ACTIONS

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
            "requires_human_approval": self.requires_human_approval,
            "is_emergency_stop":    self.is_emergency_stop,
            "summary":              self.summary.to_dict(),
            "responded_at":         self.responded_at,
            "framework_version":    self.framework_version,
        }
