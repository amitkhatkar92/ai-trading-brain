"""
governance_policy_registry.py — iios.supervisor.policy
--------------------------------------------------------
Thread-safe in-process governance policy registry.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 3
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from .constants import DEFAULT_MAX_POLICIES, GovernancePolicyType
from .exceptions import (
    GovernancePolicyCapacityError,
    GovernancePolicyNotFoundError,
    GovernancePolicyRegistryError,
)
from .governance_policy import GovernancePolicy


class GovernancePolicyRegistry:
    """
    Thread-safe container for :class:`GovernancePolicy` objects.

    Parameters
    ----------
    max_policies :
        Maximum number of policies that can be registered simultaneously.
    """

    def __init__(self, max_policies: int = DEFAULT_MAX_POLICIES) -> None:
        self._max_policies = max_policies
        self._policies: Dict[str, GovernancePolicy] = {}
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, policy: GovernancePolicy) -> None:
        """
        Register a governance policy.

        Raises
        ------
        GovernancePolicyCapacityError
            When capacity is exhausted and the policy is not an update.
        GovernancePolicyRegistryError
            When ``policy`` is None.
        """
        if policy is None:
            raise GovernancePolicyRegistryError("Cannot register None policy")
        with self._lock:
            is_update = policy.policy_id in self._policies
            if not is_update and len(self._policies) >= self._max_policies:
                raise GovernancePolicyCapacityError(self._max_policies)
            self._policies[policy.policy_id] = policy

    def unregister(self, policy_id: str) -> None:
        """
        Remove a policy.

        Raises
        ------
        GovernancePolicyNotFoundError
        """
        with self._lock:
            if policy_id not in self._policies:
                raise GovernancePolicyNotFoundError(policy_id)
            del self._policies[policy_id]

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def get(self, policy_id: str) -> GovernancePolicy:
        """Return the policy with *policy_id*."""
        with self._lock:
            policy = self._policies.get(policy_id)
        if policy is None:
            raise GovernancePolicyNotFoundError(policy_id)
        return policy

    def get_optional(self, policy_id: str) -> Optional[GovernancePolicy]:
        """Return the policy or None."""
        with self._lock:
            return self._policies.get(policy_id)

    def all_policies(self) -> List[GovernancePolicy]:
        """Return all registered policies (copy)."""
        with self._lock:
            return list(self._policies.values())

    def enabled_policies(self) -> List[GovernancePolicy]:
        """Return all enabled policies."""
        with self._lock:
            return [p for p in self._policies.values() if p.enabled]

    def policies_by_type(
        self, policy_type: GovernancePolicyType
    ) -> List[GovernancePolicy]:
        """Return all policies of the given type."""
        with self._lock:
            return [
                p for p in self._policies.values()
                if p.policy_type == policy_type
            ]

    def enable(self, policy_id: str) -> None:
        """Enable a policy."""
        policy = self.get(policy_id)
        with self._lock:
            self._policies[policy_id] = policy.with_enabled(True)

    def disable(self, policy_id: str) -> None:
        """Disable a policy."""
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
        """Remove all policies (for testing)."""
        with self._lock:
            self._policies.clear()
