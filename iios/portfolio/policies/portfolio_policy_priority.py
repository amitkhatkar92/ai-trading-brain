"""
portfolio_policy_priority.py — iios.portfolio.policies
=======================================================
Conflict resolution between multiple PolicyOutcome objects.

When multiple policies evaluate a portfolio operation, they can
produce conflicting actions.  PolicyPriorityResolver applies an
institutional conflict resolution strategy to produce a single
final PolicyAction.

Conflict Resolution Strategies
-------------------------------
DENY_OVERRIDES (default):
    BLOCK > REJECT > ESCALATE > REQUIRE_MANUAL_REVIEW > DEFER
    > APPROVE_WITH_CONDITIONS > APPROVE.
    Critical policies are checked first — a CRITICAL policy's
    blocking/rejecting action overrides all non-critical outcomes.

PRIORITY_WINS:
    The action of the highest-priority policy (CRITICAL=0 wins)
    is returned.  Ties are broken by action severity.

ESCALATION_OVERRIDES:
    ESCALATE overrides conditional approvals but not BLOCK/REJECT.
    Otherwise behaves like DENY_OVERRIDES.

C10 Portfolio Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

from typing import List, Optional

from .constants import (
    ACTION_SEVERITY,
    ACTION_SEVERITY_ORDER,
    BLOCKING_ACTIONS,
    PolicyAction,
    PolicyConflictResolution,
    PolicyPriority,
)


class PolicyPriorityResolver:
    """
    Resolves conflicting PolicyOutcome objects to a single PolicyAction.

    Parameters
    ----------
    resolution : Conflict resolution strategy
                 (default: PolicyConflictResolution.DENY_OVERRIDES).
    """

    def __init__(
        self,
        resolution: PolicyConflictResolution = PolicyConflictResolution.DENY_OVERRIDES,
    ) -> None:
        self._resolution = resolution

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def resolution(self) -> PolicyConflictResolution:
        return self._resolution

    # ------------------------------------------------------------------
    # Primary interface
    # ------------------------------------------------------------------

    def resolve(self, outcomes: list) -> PolicyAction:
        """
        Apply conflict resolution to a list of PolicyOutcome objects
        and return a single final PolicyAction.

        An empty outcomes list resolves to APPROVE (pass-through).
        """
        if not outcomes:
            return PolicyAction.APPROVE

        if self._resolution == PolicyConflictResolution.PRIORITY_WINS:
            return self._resolve_priority_wins(outcomes)
        elif self._resolution == PolicyConflictResolution.ESCALATION_OVERRIDES:
            return self._resolve_escalation_overrides(outcomes)
        else:
            return self._resolve_deny_overrides(outcomes)

    def sort_by_priority(self, outcomes: list) -> list:
        """
        Sort outcomes by (policy priority ASC, action severity ASC).

        CRITICAL policies with the most restrictive actions appear first.
        """
        return sorted(
            outcomes,
            key=lambda o: (int(o.priority), ACTION_SEVERITY[o.action]),
        )

    # ------------------------------------------------------------------
    # Private resolution strategies
    # ------------------------------------------------------------------

    def _resolve_deny_overrides(self, outcomes: list) -> PolicyAction:
        """
        DENY_OVERRIDES:
        1. CRITICAL policies' most restrictive action overrides others.
        2. Across all policies: most restrictive action (lowest severity) wins.
        """
        # 1 — Critical policies take precedence
        critical = [o for o in outcomes if int(o.priority) == int(PolicyPriority.CRITICAL)]
        if critical:
            critical_action = min(critical, key=lambda o: ACTION_SEVERITY[o.action]).action
            # If the critical policy demands a blocking or escalation outcome, honour it
            if ACTION_SEVERITY[critical_action] <= ACTION_SEVERITY[PolicyAction.APPROVE_WITH_CONDITIONS]:
                return critical_action

        # 2 — Most restrictive action across all policies
        return min(outcomes, key=lambda o: ACTION_SEVERITY[o.action]).action

    def _resolve_priority_wins(self, outcomes: list) -> PolicyAction:
        """
        PRIORITY_WINS: the highest-priority policy's action wins.
        Ties broken by action severity (most restrictive wins).
        """
        sorted_outcomes = sorted(
            outcomes,
            key=lambda o: (int(o.priority), ACTION_SEVERITY[o.action]),
        )
        return sorted_outcomes[0].action

    def _resolve_escalation_overrides(self, outcomes: list) -> PolicyAction:
        """
        ESCALATION_OVERRIDES:
        BLOCK/REJECT still win if present, but ESCALATE overrides
        APPROVE/APPROVE_WITH_CONDITIONS/DEFER/REQUIRE_MANUAL_REVIEW.
        """
        # Hard blocking actions still win
        for action in [PolicyAction.BLOCK, PolicyAction.REJECT]:
            if any(o.action == action for o in outcomes):
                return action
        # Escalate overrides conditional approvals
        if any(o.action == PolicyAction.ESCALATE for o in outcomes):
            return PolicyAction.ESCALATE
        # Fallback: most restrictive
        return min(outcomes, key=lambda o: ACTION_SEVERITY[o.action]).action
