"""
decision_policy_priority.py — iios.decision.policies
======================================================
Conflict resolution and priority-based action selection.

C9 Decision Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

from typing import List, Tuple

from .constants import (
    ACTION_PRECEDENCE,
    DENY_ACTIONS,
    ESCALATION_ACTIONS,
    ConflictResolutionStrategy,
    PolicyAction,
    PolicyPriority,
)
from .decision_policy_result import SinglePolicyResult


class PolicyPriorityResolver:
    """
    Resolves the final :class:`PolicyAction` from a list of
    :class:`SinglePolicyResult` objects using the chosen conflict
    resolution strategy.

    Strategies
    ----------
    EXPLICIT_DENY_OVERRIDES
        Hard denial (BLOCK or REJECT) wins over any approval regardless
        of priority. Within the deny tier, BLOCK beats REJECT.
        Escalation actions override conditional approval.
        Applies the full ``ACTION_PRECEDENCE`` ordering.

    HIGHEST_PRIORITY_WINS
        The result produced by the highest-priority policy (lowest
        ``PolicyPriority`` integer) wins outright.  Ties are broken by
        action precedence.

    ESCALATION_OVERRIDES
        Any ESCALATE action overrides all non-deny decisions.
        Falls back to EXPLICIT_DENY_OVERRIDES when no escalation is
        present.
    """

    def resolve(
        self,
        results:  List[SinglePolicyResult],
        strategy: ConflictResolutionStrategy,
    ) -> Tuple[PolicyAction, bool]:
        """
        Return ``(final_action, conflict_applied)`` where
        ``conflict_applied`` is ``True`` when multiple results disagreed
        and conflict resolution was needed.

        Parameters
        ----------
        results :  Evaluated policy results.
        strategy : Conflict resolution strategy.
        """
        if not results:
            return PolicyAction.APPROVE, False

        # Collect unique actions
        actions = {r.action for r in results}
        conflict_applied = len(actions) > 1

        if strategy == ConflictResolutionStrategy.HIGHEST_PRIORITY_WINS:
            return self._by_highest_priority(results), conflict_applied

        if strategy == ConflictResolutionStrategy.ESCALATION_OVERRIDES:
            return self._with_escalation_override(results), conflict_applied

        # Default: EXPLICIT_DENY_OVERRIDES
        return self._explicit_deny(results), conflict_applied

    # ------------------------------------------------------------------
    # Strategy implementations
    # ------------------------------------------------------------------

    def _explicit_deny(self, results: List[SinglePolicyResult]) -> PolicyAction:
        """
        BLOCK > REJECT > ESCALATE > REQUIRE_MANUAL_REVIEW > DEFER
        > APPROVE_WITH_CONDITIONS > APPROVE
        """
        return min(
            (r.action for r in results),
            key=lambda a: ACTION_PRECEDENCE.get(a, 99),
        )

    def _by_highest_priority(self, results: List[SinglePolicyResult]) -> PolicyAction:
        """Winner = highest-priority policy (lowest priority integer)."""
        # Sort: primary = PolicyPriority (asc), secondary = ACTION_PRECEDENCE (asc)
        best = min(
            results,
            key=lambda r: (int(r.priority), ACTION_PRECEDENCE.get(r.action, 99)),
        )
        return best.action

    def _with_escalation_override(self, results: List[SinglePolicyResult]) -> PolicyAction:
        """ESCALATE overrides approval; falls back to explicit-deny ordering."""
        escalated = [r for r in results if r.action in ESCALATION_ACTIONS]
        if escalated:
            # Within escalation actions, prefer ESCALATE > REQUIRE_MANUAL_REVIEW
            return min(
                (r.action for r in escalated),
                key=lambda a: ACTION_PRECEDENCE.get(a, 99),
            )
        return self._explicit_deny(results)
