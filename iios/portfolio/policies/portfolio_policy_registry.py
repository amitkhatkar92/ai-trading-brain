"""
portfolio_policy_registry.py — iios.portfolio.policies
=======================================================
Thread-safe registry for PortfolioPolicy objects.

C10 Portfolio Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from .constants import DEFAULT_MAX_POLICIES, PolicyStatus, PolicyType
from .exceptions import (
    PortfolioPolicyCapacityError,
    PortfolioPolicyNotFoundError,
)
from .portfolio_policy import PortfolioPolicy


class PortfolioPolicyRegistry:
    """
    Thread-safe store for PortfolioPolicy objects.

    Parameters
    ----------
    max_policies : Maximum number of policies that may be registered.
    """

    def __init__(self, max_policies: int = DEFAULT_MAX_POLICIES) -> None:
        self._max_policies                   = max_policies
        self._lock                           = threading.RLock()
        self._policies: Dict[str, PortfolioPolicy] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, policy: PortfolioPolicy) -> None:
        """
        Register a policy.

        Raises
        ------
        PortfolioPolicyCapacityError
            If the registry is at capacity.
        """
        with self._lock:
            if len(self._policies) >= self._max_policies:
                raise PortfolioPolicyCapacityError(self._max_policies)
            self._policies[policy.policy_id] = policy

    def unregister(self, policy_id: str) -> bool:
        """Remove a policy by ID.  Returns True if found and removed."""
        with self._lock:
            if policy_id in self._policies:
                del self._policies[policy_id]
                return True
            return False

    # ------------------------------------------------------------------
    # Lookups
    # ------------------------------------------------------------------

    def get(self, policy_id: str) -> Optional[PortfolioPolicy]:
        """Return the policy with the given ID, or None."""
        with self._lock:
            return self._policies.get(policy_id)

    def get_or_raise(self, policy_id: str) -> PortfolioPolicy:
        """Return the policy or raise PortfolioPolicyNotFoundError."""
        policy = self.get(policy_id)
        if policy is None:
            raise PortfolioPolicyNotFoundError(policy_id)
        return policy

    def find_by_type(self, policy_type: PolicyType) -> List[PortfolioPolicy]:
        """Return all policies of the given type (any status)."""
        with self._lock:
            return [p for p in self._policies.values() if p.policy_type == policy_type]

    def all_active(self) -> List[PortfolioPolicy]:
        """Return all currently active policies, sorted by priority."""
        with self._lock:
            active = [p for p in self._policies.values() if p.is_active]
        return sorted(active, key=lambda p: int(p.priority))

    def all_policies(self) -> List[PortfolioPolicy]:
        """Return all registered policies regardless of status."""
        with self._lock:
            return list(self._policies.values())

    # ------------------------------------------------------------------
    # Status mutations
    # ------------------------------------------------------------------

    def deactivate(self, policy_id: str) -> bool:
        """
        Set a policy's status to INACTIVE.

        Returns True if the policy was found, False otherwise.
        """
        with self._lock:
            policy = self._policies.get(policy_id)
            if policy is None:
                return False
            policy.deactivate()
            return True

    def activate(self, policy_id: str) -> bool:
        """
        Set a policy's status back to ACTIVE.

        Returns True if the policy was found, False otherwise.
        """
        with self._lock:
            policy = self._policies.get(policy_id)
            if policy is None:
                return False
            policy.activate()
            return True

    def deprecate(self, policy_id: str) -> bool:
        """
        Set a policy's status to DEPRECATED.

        Returns True if the policy was found, False otherwise.
        """
        with self._lock:
            policy = self._policies.get(policy_id)
            if policy is None:
                return False
            policy.deprecate()
            return True

    # ------------------------------------------------------------------
    # Counts
    # ------------------------------------------------------------------

    def policy_count(self) -> int:
        with self._lock:
            return len(self._policies)

    def active_count(self) -> int:
        with self._lock:
            return sum(1 for p in self._policies.values() if p.is_active)

    # ------------------------------------------------------------------
    # Bulk
    # ------------------------------------------------------------------

    def clear(self) -> None:
        with self._lock:
            self._policies.clear()
