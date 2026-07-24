"""
knowledge_policy_priority.py — iios.knowledge.policies
--------------------------------------------------------
PolicyPriorityResolver — resolves conflicts across multiple policy decisions.

Conflict Resolution Rules (in precedence order):
  1. BLOCKED        overrides everything
  2. REJECTED       overrides APPROVED / APPROVED_WITH_CONDITIONS
  3. ESCALATED      overrides APPROVED_WITH_CONDITIONS
  4. MANUAL_REVIEW  overrides automatic APPROVED
  5. STEWARD_APPROVAL overrides automatic APPROVED
  6. APPROVED_WITH_CONDITIONS overrides plain APPROVED
  7. APPROVED       — base case

C14 Enterprise Knowledge Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

from typing import List, Tuple

from iios.common.logging.logging_manager import get_logger

from .constants import GovernanceDecision
from .knowledge_policy_result import PolicyEvaluationResult

_log = get_logger(__name__)


class PolicyPriorityResolver:
    """
    Resolves conflicts among multiple PolicyEvaluationResults.

    Implements the enterprise conflict resolution rules defined in the spec.
    """

    # Dominance order — first entry wins
    _DOMINANCE: List[GovernanceDecision] = [
        GovernanceDecision.BLOCKED,
        GovernanceDecision.REJECTED,
        GovernanceDecision.ESCALATED,
        GovernanceDecision.MANUAL_REVIEW,
        GovernanceDecision.STEWARD_APPROVAL,
        GovernanceDecision.APPROVED_WITH_CONDITIONS,
        GovernanceDecision.APPROVED,
        GovernanceDecision.ARCHIVED,
    ]

    def resolve(
        self,
        results: List[PolicyEvaluationResult],
    ) -> Tuple[GovernanceDecision, str]:
        """
        Compute the aggregate governance decision from all policy results.

        Returns (GovernanceDecision, reason_str).
        """
        if not results:
            return (
                GovernanceDecision.APPROVED,
                "No policies evaluated — approved by default",
            )

        decisions = {r.decision for r in results}

        for candidate in self._DOMINANCE:
            if candidate in decisions:
                reason = self._build_reason(candidate, results)
                _log.debug(
                    f"Conflict resolution: "
                    f"decision={candidate.value!r} "
                    f"policies_evaluated={len(results)}"
                )
                return candidate, reason

        return GovernanceDecision.APPROVED, "All policies approved"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_reason(
        self,
        decision: GovernanceDecision,
        results:  List[PolicyEvaluationResult],
    ) -> str:
        blocking = [r.policy_name for r in results if r.decision == decision]
        return f"Decision={decision.value!r}; policies: {', '.join(blocking)}"
