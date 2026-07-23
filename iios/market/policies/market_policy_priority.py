"""
market_policy_priority.py — iios.market.policies
==================================================
Priority resolution for conflicting market policy outcomes.

C12 Market Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

from typing import List, Optional

from .constants import (
    ACTION_SEVERITY,
    DENY_ACTIONS,
    PolicyAction,
    PolicyPriority,
)
from .market_policy_result import MarketPolicyResult


class MarketPolicyPriorityResolver:
    """
    Resolves conflicting :class:`~.market_policy_result.MarketPolicyResult`
    objects into a single dominant result and final
    :class:`~.constants.PolicyAction`.

    Resolution order (applied in sequence until a dominant result is found):

    1. ``BLOCK_OVERRIDES_ALL``              — BLOCK wins unconditionally
    2. ``CRITICAL_OVERRIDES``              — Critical-priority policies win
    3. ``EXPLICIT_DENY_OVERRIDES``         — REJECT overrides approvals
    4. ``ESCALATION_OVERRIDES_CONDITIONAL`` — ESCALATE overrides conditional approval
    5. ``HIGHEST_PRIORITY_WINS``           — PolicyPriority int value (lower = higher)

    All strategies are stateless.
    """

    @staticmethod
    def resolve(results: List[MarketPolicyResult]) -> Optional[MarketPolicyResult]:
        """
        Return the dominant result from a list of results.

        Returns ``None`` when ``results`` is empty.
        """
        if not results:
            return None

        # Strategy 1: BLOCK beats everything
        blocks = [r for r in results if r.action == PolicyAction.BLOCK]
        if blocks:
            return min(blocks, key=lambda r: r.priority.value)

        # Strategy 2: CRITICAL priority policies
        critical = [r for r in results if r.priority == PolicyPriority.CRITICAL]
        if critical:
            return MarketPolicyPriorityResolver._most_severe(critical)

        # Strategy 3: Explicit deny (REJECT) overrides approvals
        denying = [r for r in results if r.action in DENY_ACTIONS]
        if denying:
            return MarketPolicyPriorityResolver._most_severe(denying)

        # Strategy 4: ESCALATE overrides conditional approval
        escalated = [r for r in results if r.action == PolicyAction.ESCALATE]
        if escalated:
            return min(escalated, key=lambda r: r.priority.value)

        # Strategy 5: Highest priority wins (lowest int value)
        return MarketPolicyPriorityResolver._most_severe(results)

    @staticmethod
    def _most_severe(results: List[MarketPolicyResult]) -> MarketPolicyResult:
        """Return the result with the most severe action; break ties by priority."""
        return max(
            results,
            key=lambda r: (
                ACTION_SEVERITY.get(r.action, 0),
                -r.priority.value,  # lower int = higher priority
            ),
        )
