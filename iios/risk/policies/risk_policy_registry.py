"""
risk_policy_registry.py — iios.risk.policies
==============================================
Thread-safe in-process policy registry.

C11 Risk Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from .constants import DEFAULT_MAX_POLICIES, PolicyType
from .exceptions import (
    RiskPolicyCapacityError,
    RiskPolicyNotFoundError,
    RiskPolicyRegistryError,
)
from .risk_policy import RiskPolicy


class RiskPolicyRegistry:
    """
    Thread-safe container for :class:`~.risk_policy.RiskPolicy` objects.

    All read and write operations acquire a reentrant lock, making the
    registry safe for concurrent use from multiple threads.

    Parameters
    ----------
    max_policies :
        Maximum number of policies that can be registered simultaneously.
        Defaults to :data:`~.constants.DEFAULT_MAX_POLICIES`.
    """

    def __init__(self, max_policies: int = DEFAULT_MAX_POLICIES) -> None:
        self._max_policies = max_policies
        self._policies: Dict[str, RiskPolicy] = {}
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, policy: RiskPolicy) -> None:
        """
        Register a policy.

        Raises
        ------
        RiskPolicyCapacityError
            When capacity is already exhausted and the policy is not an update.
        RiskPolicyRegistryError
            When ``policy`` is ``None``.
        """
        if policy is None:
            raise RiskPolicyRegistryError("Cannot register None policy")
        with self._lock:
            is_update = policy.policy_id in self._policies
            if not is_update and len(self._policies) >= self._max_policies:
                raise RiskPolicyCapacityError(self._max_policies)
            self._policies[policy.policy_id] = policy

    def unregister(self, policy_id: str) -> None:
        """
        Remove a policy.

        Raises
        ------
        RiskPolicyNotFoundError
            When no policy with *policy_id* is registered.
        """
        with self._lock:
            if policy_id not in self._policies:
                raise RiskPolicyNotFoundError(policy_id)
            del self._policies[policy_id]

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def get(self, policy_id: str) -> RiskPolicy:
        """
        Return the policy with *policy_id*.

        Raises
        ------
        RiskPolicyNotFoundError
        """
        with self._lock:
            policy = self._policies.get(policy_id)
        if policy is None:
            raise RiskPolicyNotFoundError(policy_id)
        return policy

    def get_optional(self, policy_id: str) -> Optional[RiskPolicy]:
        """Return the policy or ``None``."""
        with self._lock:
            return self._policies.get(policy_id)

    def contains(self, policy_id: str) -> bool:
        """Return True if *policy_id* is registered."""
        with self._lock:
            return policy_id in self._policies

    # ------------------------------------------------------------------
    # Bulk queries
    # ------------------------------------------------------------------

    def list_all(self) -> List[RiskPolicy]:
        """Return all registered policies (unordered snapshot)."""
        with self._lock:
            return list(self._policies.values())

    def list_by_type(self, policy_type: PolicyType) -> List[RiskPolicy]:
        """Return all policies of the given *policy_type*."""
        with self._lock:
            return [
                p for p in self._policies.values()
                if p.policy_type == policy_type
            ]

    def list_enabled(self) -> List[RiskPolicy]:
        """Return all currently enabled policies."""
        with self._lock:
            return [p for p in self._policies.values() if p.enabled]

    def list_enabled_by_type(self, policy_type: PolicyType) -> List[RiskPolicy]:
        """Return enabled policies filtered by *policy_type*."""
        with self._lock:
            return [
                p for p in self._policies.values()
                if p.enabled and p.policy_type == policy_type
            ]

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    @property
    def count(self) -> int:
        """Total number of registered policies."""
        with self._lock:
            return len(self._policies)

    @property
    def enabled_count(self) -> int:
        """Number of enabled policies."""
        with self._lock:
            return sum(1 for p in self._policies.values() if p.enabled)

    @property
    def max_policies(self) -> int:
        return self._max_policies

    def clear(self) -> None:
        """Remove all registered policies."""
        with self._lock:
            self._policies.clear()
