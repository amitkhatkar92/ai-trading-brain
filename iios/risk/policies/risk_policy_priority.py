"""
risk_policy_priority.py — iios.risk.policies
==============================================
Priority resolution for conflicting policy outcomes.

C11 Risk Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

from typing import List, Optional

from .constants import (
    ACTION_SEVERITY,
    ConflictResolutionStrategy,
    PolicyAction,
    PolicyPriority,
)
from .risk_policy_result import RiskPolicyResult


class PolicyPriorityResolver:
    """
    Resolves conflicting :class:`~.risk_policy_result.RiskPolicyResult` objects
    into a single dominant result and final :class:`~.constants.PolicyAction`.

    Resolution order (applied in sequence until a dominant result is found):

    1. ``IMMEDIATE_ACTION_OVERRIDES_ALL``  — REQUIRE_IMMEDIATE_ACTION wins
    2. ``CRITICAL_OVERRIDES``             — Critical-priority policies win
    3. ``EXPLICIT_DENY_OVERRIDES``        — REJECT / BLOCK override approvals
    4. ``ESCALATION_OVERRIDES_CONDITIONAL`` — ESCALATE overrides conditional approval
    5. ``HIGHEST_PRIORITY_WINS``          — PolicyPriority int value (lower = higher)

    All strategies are stateless.
    """

    @staticmethod
    def resolve(results: List[RiskPolicyResult]) -> Optional[RiskPolicyResult]:
        """
        Return the dominant result from a list of results.

        Returns ``None`` when ``results`` is empty.
        """
        if not results:
            return None

        # Strategy 1: REQUIRE_IMMEDIATE_ACTION beats everything
        immediate = [
            r for r in results
            if r.action == PolicyAction.REQUIRE_IMMEDIATE_ACTION
        ]
        if immediate:
            return min(immediate, key=lambda r: r.priority.value)

        # Strategy 2: CRITICAL priority policies
        critical = [r for r in results if r.priority == PolicyPriority.CRITICAL]
        if critical:
            return PolicyPriorityResolver._most_severe(critical)

        # Strategy 3: Explicit deny (REJECT / BLOCK) overrides approvals
        deny = [
            r for r in results
            if r.action in (PolicyAction.REJECT, PolicyAction.BLOCK)
        ]
        if deny:
            return PolicyPriorityResolver._most_severe(deny)

        # Strategy 4: ESCALATE overrides conditional approvals
        escalate = [r for r in results if r.action == PolicyAction.ESCALATE]
        conditional = [
            r for r in results
            if r.action == PolicyAction.APPROVE_WITH_CONDITIONS
        ]
        if escalate and conditional:
            return PolicyPriorityResolver._most_severe(escalate)

        # Strategy 5: Highest priority (lowest int) with highest ACTION_SEVERITY as tiebreak
        return PolicyPriorityResolver._most_severe(results)

    @staticmethod
    def _most_severe(results: List[RiskPolicyResult]) -> RiskPolicyResult:
        """Return the result with the highest action severity; break ties by priority."""
        return max(
            results,
            key=lambda r: (
                ACTION_SEVERITY.get(r.action, 0),
                # Lower priority int = more dominant
                -r.priority.value,
            ),
        )

    @staticmethod
    def final_action(results: List[RiskPolicyResult]) -> PolicyAction:
        """Convenience helper — return the final action for a list of results."""
        from .constants import DEFAULT_POLICY_ACTION
        dominant = PolicyPriorityResolver.resolve(results)
        if dominant is None:
            return DEFAULT_POLICY_ACTION
        return dominant.action

    @staticmethod
    def applies_strategy(
        results:  List[RiskPolicyResult],
        strategy: ConflictResolutionStrategy,
    ) -> bool:
        """Return True when the given strategy would be the deciding strategy."""
        if not results:
            return False
        if strategy == ConflictResolutionStrategy.IMMEDIATE_ACTION_OVERRIDES_ALL:
            return any(r.action == PolicyAction.REQUIRE_IMMEDIATE_ACTION for r in results)
        if strategy == ConflictResolutionStrategy.CRITICAL_OVERRIDES:
            return any(r.priority == PolicyPriority.CRITICAL for r in results)
        if strategy == ConflictResolutionStrategy.EXPLICIT_DENY_OVERRIDES:
            has_deny = any(
                r.action in (PolicyAction.REJECT, PolicyAction.BLOCK) for r in results
            )
            return has_deny and not any(
                r.action == PolicyAction.REQUIRE_IMMEDIATE_ACTION for r in results
            )
        if strategy == ConflictResolutionStrategy.ESCALATION_OVERRIDES_CONDITIONAL:
            has_escalate  = any(r.action == PolicyAction.ESCALATE for r in results)
            has_cond      = any(r.action == PolicyAction.APPROVE_WITH_CONDITIONS for r in results)
            return has_escalate and has_cond
        return True  # HIGHEST_PRIORITY_WINS always applies as fallback
