"""
portfolio_policy_result.py — iios.portfolio.policies
=====================================================
Full evaluation result and summary value objects.

PortfolioPolicyResult — complete result with all PolicyOutcome objects.
PolicyEvaluationSummary — compact counts-based summary.

C10 Portfolio Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .constants import (
    APPROVAL_ACTIONS,
    BLOCKING_ACTIONS,
    ESCALATION_ACTIONS,
    VERSION,
    PolicyAction,
    PolicyType,
)
from .portfolio_policy import PolicyOutcome


@dataclass(frozen=True)
class PolicyEvaluationSummary:
    """
    Compact, counts-based summary of an evaluation run.

    Fields
    ------
    evaluation_id :        Unique evaluation run identifier.
    portfolio_id :         Portfolio that was evaluated.
    final_action :         Resolved final governance outcome.
    total_policies :       Total number of policies evaluated.
    approved_count :       Policies that returned APPROVE.
    conditional_count :    Policies that returned APPROVE_WITH_CONDITIONS.
    rejected_count :       Policies that returned REJECT.
    blocked_count :        Policies that returned BLOCK.
    escalated_count :      Policies that returned ESCALATE.
    deferred_count :       Policies that returned DEFER.
    manual_review_count :  Policies that returned REQUIRE_MANUAL_REVIEW.
    elapsed_s :            Total evaluation wall-clock seconds.
    evaluated_at :         Wall-clock timestamp of evaluation completion.
    framework_version :    Framework version string.
    """
    evaluation_id:       str
    portfolio_id:        str
    final_action:        PolicyAction
    total_policies:      int
    approved_count:      int
    conditional_count:   int
    rejected_count:      int
    blocked_count:       int
    escalated_count:     int
    deferred_count:      int
    manual_review_count: int
    elapsed_s:           float
    evaluated_at:        float
    framework_version:   str = VERSION

    @property
    def is_approved(self) -> bool:
        return self.final_action in APPROVAL_ACTIONS

    @property
    def is_blocked(self) -> bool:
        return self.final_action == PolicyAction.BLOCK

    @property
    def is_rejected(self) -> bool:
        return self.final_action == PolicyAction.REJECT

    @property
    def requires_escalation(self) -> bool:
        return self.final_action == PolicyAction.ESCALATE

    @property
    def requires_manual_review(self) -> bool:
        return self.final_action == PolicyAction.REQUIRE_MANUAL_REVIEW

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evaluation_id":       self.evaluation_id,
            "portfolio_id":        self.portfolio_id,
            "final_action":        self.final_action.value,
            "total_policies":      self.total_policies,
            "approved_count":      self.approved_count,
            "conditional_count":   self.conditional_count,
            "rejected_count":      self.rejected_count,
            "blocked_count":       self.blocked_count,
            "escalated_count":     self.escalated_count,
            "deferred_count":      self.deferred_count,
            "manual_review_count": self.manual_review_count,
            "elapsed_s":           self.elapsed_s,
            "evaluated_at":        self.evaluated_at,
            "framework_version":   self.framework_version,
        }


@dataclass(frozen=True)
class PortfolioPolicyResult:
    """
    Full evaluation result including all PolicyOutcome objects.

    Fields
    ------
    result_id :      Unique result identifier.
    evaluation_id :  Evaluation run that produced this result.
    portfolio_id :   Portfolio that was evaluated.
    final_action :   Resolved final governance outcome.
    outcomes :       Tuple of per-policy outcomes.
    summary :        Compact counts-based summary.
    elapsed_s :      Total evaluation wall-clock seconds.
    evaluated_at :   Wall-clock timestamp.
    framework_version: Framework version string.
    """
    result_id:         str
    evaluation_id:     str
    portfolio_id:      str
    final_action:      PolicyAction
    outcomes:          tuple   # Tuple[PolicyOutcome, ...]
    summary:           PolicyEvaluationSummary
    elapsed_s:         float
    evaluated_at:      float
    framework_version: str = VERSION

    @property
    def is_approved(self) -> bool:
        return self.final_action in APPROVAL_ACTIONS

    @property
    def is_blocked(self) -> bool:
        return self.final_action == PolicyAction.BLOCK

    @property
    def is_rejected(self) -> bool:
        return self.final_action == PolicyAction.REJECT

    @property
    def requires_escalation(self) -> bool:
        return self.final_action == PolicyAction.ESCALATE

    @property
    def outcome_count(self) -> int:
        return len(self.outcomes)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_id":        self.result_id,
            "evaluation_id":    self.evaluation_id,
            "portfolio_id":     self.portfolio_id,
            "final_action":     self.final_action.value,
            "outcome_count":    len(self.outcomes),
            "outcomes":         [o.to_dict() for o in self.outcomes],
            "summary":          self.summary.to_dict(),
            "elapsed_s":        self.elapsed_s,
            "evaluated_at":     self.evaluated_at,
            "framework_version": self.framework_version,
        }


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

def _build_summary(
    evaluation_id: str,
    portfolio_id:  str,
    final_action:  PolicyAction,
    outcomes:      List[PolicyOutcome],
    elapsed_s:     float,
) -> PolicyEvaluationSummary:
    """Build a PolicyEvaluationSummary from a list of PolicyOutcome objects."""
    counts: Dict[PolicyAction, int] = {a: 0 for a in PolicyAction}
    for o in outcomes:
        counts[o.action] = counts.get(o.action, 0) + 1

    return PolicyEvaluationSummary(
        evaluation_id       = evaluation_id,
        portfolio_id        = portfolio_id,
        final_action        = final_action,
        total_policies      = len(outcomes),
        approved_count      = counts[PolicyAction.APPROVE],
        conditional_count   = counts[PolicyAction.APPROVE_WITH_CONDITIONS],
        rejected_count      = counts[PolicyAction.REJECT],
        blocked_count       = counts[PolicyAction.BLOCK],
        escalated_count     = counts[PolicyAction.ESCALATE],
        deferred_count      = counts[PolicyAction.DEFER],
        manual_review_count = counts[PolicyAction.REQUIRE_MANUAL_REVIEW],
        elapsed_s           = elapsed_s,
        evaluated_at        = time.time(),
    )
