"""
ai_governance_policy_registry.py — iios.supervisor.policies
-------------------------------------------------------------
Thread-safe in-process AI governance policy registry.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 3
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from .constants import DEFAULT_MAX_POLICIES, AIGovernancePolicyType
from .exceptions import (
    AIGovernancePolicyCapacityError,
    AIGovernancePolicyNotFoundError,
    AIGovernancePolicyRegistryError,
)
from .ai_governance_policy import AIGovernancePolicy


class AIGovernancePolicyRegistry:
    """
    Thread-safe container for :class:`AIGovernancePolicy` objects.

    Parameters
    ----------
    max_policies :
        Maximum number of policies that can be registered simultaneously.
        Updating an existing policy does not count against the limit.
    """

    def __init__(self, max_policies: int = DEFAULT_MAX_POLICIES) -> None:
        self._max_policies = max_policies
        self._policies: Dict[str, AIGovernancePolicy] = {}
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, policy: AIGovernancePolicy) -> None:
        """
        Register a governance policy.

        Raises
        ------
        AIGovernancePolicyRegistryError
            When ``policy`` is None.
        AIGovernancePolicyCapacityError
            When capacity is exhausted and the policy is not an update.
        """
        if policy is None:
            raise AIGovernancePolicyRegistryError("Cannot register None policy")
        with self._lock:
            is_update = policy.policy_id in self._policies
            if not is_update and len(self._policies) >= self._max_policies:
                raise AIGovernancePolicyCapacityError(self._max_policies)
            self._policies[policy.policy_id] = policy

    def unregister(self, policy_id: str) -> None:
        """
        Remove a policy by ID.

        Raises
        ------
        AIGovernancePolicyNotFoundError
        """
        with self._lock:
            if policy_id not in self._policies:
                raise AIGovernancePolicyNotFoundError(policy_id)
            del self._policies[policy_id]

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def get(self, policy_id: str) -> AIGovernancePolicy:
        """Return the policy with *policy_id*."""
        with self._lock:
            policy = self._policies.get(policy_id)
        if policy is None:
            raise AIGovernancePolicyNotFoundError(policy_id)
        return policy

    def get_optional(self, policy_id: str) -> Optional[AIGovernancePolicy]:
        """Return the policy or None."""
        with self._lock:
            return self._policies.get(policy_id)

    def all_policies(self) -> List[AIGovernancePolicy]:
        """Return a snapshot of all registered policies."""
        with self._lock:
            return list(self._policies.values())

    def enabled_policies(self) -> List[AIGovernancePolicy]:
        """Return all enabled policies."""
        with self._lock:
            return [p for p in self._policies.values() if p.enabled]

    def policies_by_type(
        self, policy_type: AIGovernancePolicyType
    ) -> List[AIGovernancePolicy]:
        """Return all policies of the given governance domain."""
        with self._lock:
            return [
                p for p in self._policies.values()
                if p.policy_type == policy_type
            ]

    def enable(self, policy_id: str) -> None:
        """Enable a registered policy."""
        policy = self.get(policy_id)
        with self._lock:
            self._policies[policy_id] = policy.with_enabled(True)

    def disable(self, policy_id: str) -> None:
        """Disable a registered policy."""
        policy = self.get(policy_id)
        with self._lock:
            self._policies[policy_id] = policy.with_enabled(False)

    # ------------------------------------------------------------------
    # Counts
    # ------------------------------------------------------------------

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._policies)

    @property
    def enabled_count(self) -> int:
        with self._lock:
            return sum(1 for p in self._policies.values() if p.enabled)

    def clear(self) -> None:
        """Remove all policies (primarily for testing)."""
        with self._lock:
            self._policies.clear()
