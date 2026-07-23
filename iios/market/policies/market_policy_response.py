"""
market_policy_response.py — iios.market.policies
==================================================
Immutable policy evaluation response and summary value objects.

C12 Market Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from .constants import VERSION, DENY_ACTIONS, PolicyAction
from .market_policy_result import MarketPolicyResult


# ---------------------------------------------------------------------------
# MarketEvaluationSummary
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MarketEvaluationSummary:
    """
    High-level aggregation of all market policy evaluation outcomes.

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
    approved:               int          = 0
    conditionally_approved: int          = 0
    rejected:               int          = 0
    blocked:                int          = 0
    escalated:              int          = 0
    deferred:               int          = 0
    manual_review_required: int          = 0
    dominant_policy_id:     str          = ""
    dominant_policy_name:   str          = ""
    rationale:              str          = ""
    created_at:             float        = field(default_factory=time.time)
    framework_version:      str          = VERSION

    @classmethod
    def from_results(
        cls,
        results:              Tuple[MarketPolicyResult, ...],
        final_action:         PolicyAction,
        dominant_policy_id:   str = "",
        dominant_policy_name: str = "",
        rationale:            str = "",
    ) -> "MarketEvaluationSummary":
        from .constants import PolicyAction as PA
        counts: Dict[PolicyAction, int] = {a: 0 for a in PolicyAction}
        for r in results:
            counts[r.action] = counts.get(r.action, 0) + 1
        return cls(
            summary_id             = str(uuid.uuid4()),
            final_action           = final_action,
            total_policies         = len(results),
            approved               = counts[PA.APPROVE],
            conditionally_approved = counts[PA.APPROVE_WITH_CONDITIONS],
            rejected               = counts[PA.REJECT],
            blocked                = counts[PA.BLOCK],
            escalated              = counts[PA.ESCALATE],
            deferred               = counts[PA.DEFER],
            manual_review_required = counts[PA.REQUIRE_MANUAL_REVIEW],
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
            "created_at":             self.created_at,
            "framework_version":      self.framework_version,
        }


# ---------------------------------------------------------------------------
# MarketPolicyResponse
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MarketPolicyResponse:
    """
    Immutable response returned by the Market Policy Framework after evaluation.

    Fields
    ------
    response_id :           Unique identifier.
    request_id :            Originating request identifier.
    evaluation_id :         Market workflow evaluation correlation identifier.
    market_analysis_id :    Market analysis identifier.
    exchange :              Exchange identifier.
    final_action :          Resolved governance outcome.
    results :               Per-policy evaluation results.
    summary :               Aggregated evaluation summary.
    policies_evaluated :    Number of policies evaluated.
    evaluation_elapsed_s :  Total evaluation time in seconds.
    is_success :            True when the evaluation completed without errors.
    error_message :         Non-empty when is_success is False.
    created_at :            Wall-clock response creation time.
    metadata :              Supplementary metadata.
    framework_version :     Framework version string.
    """
    response_id:          str
    request_id:           str
    evaluation_id:        str
    market_analysis_id:   str
    exchange:             str
    final_action:         PolicyAction
    results:              Tuple[MarketPolicyResult, ...]
    summary:              MarketEvaluationSummary
    policies_evaluated:   int
    evaluation_elapsed_s: float
    is_success:           bool             = True
    error_message:        str              = ""
    created_at:           float            = field(default_factory=time.time)
    metadata:             Dict[str, Any]   = field(default_factory=dict)
    framework_version:    str              = VERSION

    @property
    def is_approved(self) -> bool:
        return self.final_action in (
            PolicyAction.APPROVE,
            PolicyAction.APPROVE_WITH_CONDITIONS,
        )

    @property
    def is_denied(self) -> bool:
        return self.final_action in DENY_ACTIONS

    @property
    def requires_escalation(self) -> bool:
        return self.final_action == PolicyAction.ESCALATE

    @classmethod
    def create_success(
        cls,
        request_id:           str,
        evaluation_id:        str,
        market_analysis_id:   str,
        exchange:             str,
        final_action:         PolicyAction,
        results:              Tuple[MarketPolicyResult, ...],
        summary:              MarketEvaluationSummary,
        evaluation_elapsed_s: float,
        *,
        response_id: Optional[str]            = None,
        metadata:    Optional[Dict[str, Any]] = None,
    ) -> "MarketPolicyResponse":
        return cls(
            response_id          = response_id or str(uuid.uuid4()),
            request_id           = request_id,
            evaluation_id        = evaluation_id,
            market_analysis_id   = market_analysis_id,
            exchange             = exchange,
            final_action         = final_action,
            results              = tuple(results),
            summary              = summary,
            policies_evaluated   = len(results),
            evaluation_elapsed_s = evaluation_elapsed_s,
            is_success           = True,
            metadata             = dict(metadata or {}),
        )

    @classmethod
    def create_failure(
        cls,
        request_id:           str,
        evaluation_id:        str,
        market_analysis_id:   str,
        exchange:             str,
        error_message:        str,
        evaluation_elapsed_s: float,
        *,
        response_id: Optional[str]            = None,
        metadata:    Optional[Dict[str, Any]] = None,
    ) -> "MarketPolicyResponse":
        from .constants import DEFAULT_POLICY_ACTION
        empty_summary = MarketEvaluationSummary.from_results(
            (), DEFAULT_POLICY_ACTION
        )
        return cls(
            response_id          = response_id or str(uuid.uuid4()),
            request_id           = request_id,
            evaluation_id        = evaluation_id,
            market_analysis_id   = market_analysis_id,
            exchange             = exchange,
            final_action         = DEFAULT_POLICY_ACTION,
            results              = (),
            summary              = empty_summary,
            policies_evaluated   = 0,
            evaluation_elapsed_s = evaluation_elapsed_s,
            is_success           = False,
            error_message        = error_message,
            metadata             = dict(metadata or {}),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "response_id":          self.response_id,
            "request_id":           self.request_id,
            "evaluation_id":        self.evaluation_id,
            "market_analysis_id":   self.market_analysis_id,
            "exchange":             self.exchange,
            "final_action":         self.final_action.value,
            "policies_evaluated":   self.policies_evaluated,
            "evaluation_elapsed_s": self.evaluation_elapsed_s,
            "is_success":           self.is_success,
            "error_message":        self.error_message,
            "summary":              self.summary.to_dict(),
            "results":              [r.to_dict() for r in self.results],
            "created_at":           self.created_at,
            "framework_version":    self.framework_version,
        }
