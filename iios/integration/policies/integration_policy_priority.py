"""
integration_policy_priority.py — iios.integration.policies
------------------------------------------------------------
IntegrationPolicyPriority — priority ordering and conflict resolution.

Implements the conflict resolution rules defined in the framework:

  EMERGENCY_STOP   overrides all
  BLOCK            overrides approval actions
  REJECT           overrides approval actions
  SECURITY_APPROVAL overrides automation
  ESCALATION       overrides conditional approval
  Critical policy priority overrides lower priorities

C15 Enterprise Integration & Connectivity — Phase 1, Module 3
"""
from __future__ import annotations

from typing import List, Optional

from .constants import (
    ACTION_PRECEDENCE,
    PRIORITY_RANK,
    ConflictResolutionStrategy,
    PolicyAction,
    PolicyPriority,
)
from .integration_policy import IntegrationPolicy
from .integration_policy_result import IntegrationPolicyResult


class IntegrationPolicyPriority:
    """
    Resolves conflicts between multiple governance policy results.

    Implements five conflict resolution strategies.  The default
    strategy is MOST_RESTRICTIVE, which maps directly to the
    framework-defined conflict resolution rules.
    """

    def __init__(
        self,
        strategy: ConflictResolutionStrategy = ConflictResolutionStrategy.MOST_RESTRICTIVE,
    ) -> None:
        self._strategy = strategy

    @property
    def strategy(self) -> ConflictResolutionStrategy:
        return self._strategy

    def resolve(
        self,
        results:  List[IntegrationPolicyResult],
        policies: Optional[List[IntegrationPolicy]] = None,
    ) -> PolicyAction:
        """
        Resolve the final action from a list of per-policy results.

        Resolution precedence (MOST_RESTRICTIVE, highest wins):
        1. EMERGENCY_STOP
        2. BLOCK
        3. REJECT
        4. REQUIRE_SECURITY_APPROVAL
        5. REQUIRE_MANUAL_REVIEW
        6. ESCALATE
        7. APPROVE_WITH_CONDITIONS
        8. APPROVE  (default)
        """
        if not results:
            return PolicyAction.APPROVE

        actions = [r.action for r in results]
        return self._apply_strategy(actions, policies)

    def _apply_strategy(
        self,
        actions:  List[PolicyAction],
        policies: Optional[List[IntegrationPolicy]],
    ) -> PolicyAction:
        s = self._strategy

        if s == ConflictResolutionStrategy.MOST_RESTRICTIVE:
            return self._most_restrictive(actions)

        if s == ConflictResolutionStrategy.MOST_PERMISSIVE:
            return self._most_permissive(actions)

        if s == ConflictResolutionStrategy.EMERGENCY_STOP_OVERRIDES_ALL:
            if PolicyAction.EMERGENCY_STOP in actions:
                return PolicyAction.EMERGENCY_STOP
            return self._most_restrictive(actions)

        if s == ConflictResolutionStrategy.CRITICAL_OVERRIDES_ALL:
            # Use the action from the highest-priority policy
            if policies:
                paired = list(zip(actions, policies))
                paired.sort(
                    key=lambda x: PRIORITY_RANK.get(x[1].priority, 0),
                    reverse=True,
                )
                return paired[0][0]
            return self._most_restrictive(actions)

        # PRIORITY_WINS — same as most restrictive
        return self._most_restrictive(actions)

    @staticmethod
    def _most_restrictive(actions: List[PolicyAction]) -> PolicyAction:
        if not actions:
            return PolicyAction.APPROVE
        return max(actions, key=lambda a: ACTION_PRECEDENCE.index(a))

    @staticmethod
    def _most_permissive(actions: List[PolicyAction]) -> PolicyAction:
        if not actions:
            return PolicyAction.APPROVE
        return min(actions, key=lambda a: ACTION_PRECEDENCE.index(a))

    def rank(self, action: PolicyAction) -> int:
        """Return numeric precedence rank (higher = more restrictive)."""
        return ACTION_PRECEDENCE.index(action)
