"""
decision_policy_registry.py — iios.decision.policies
======================================================
Thread-safe registry that stores and retrieves :class:`DecisionPolicy`
objects.

C9 Decision Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import DEFAULT_MAX_POLICIES, PolicyStatus, PolicyType
from .decision_policy import DecisionPolicy
from .exceptions import PolicyNotFoundError, PolicyRegistryError

_log = get_logger(__name__)


class DecisionPolicyRegistry:
    """
    Thread-safe store for :class:`DecisionPolicy` objects.

    All mutation operations acquire an RLock (supports nested calls
    from the same thread).

    Parameters
    ----------
    max_policies : Maximum number of policies the registry accepts.
    """

    def __init__(self, max_policies: int = DEFAULT_MAX_POLICIES) -> None:
        self._lock:        threading.RLock           = threading.RLock()
        self._policies:    Dict[str, DecisionPolicy] = {}
        self._max_policies = max_policies

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def register(self, policy: DecisionPolicy) -> None:
        """
        Add *policy* to the registry.

        Raises
        ------
        PolicyRegistryError : When the registry is full or a policy with
                              the same ID already exists with a different
                              object identity (use update to overwrite).
        """
        with self._lock:
            if len(self._policies) >= self._max_policies:
                raise PolicyRegistryError(
                    f"Registry is full (max {self._max_policies} policies)"
                )
            if policy.policy_id in self._policies:
                _log.debug(
                    f"DecisionPolicyRegistry: updating existing policy "
                    f"{policy.policy_id!r}"
                )
            self._policies[policy.policy_id] = policy
            _log.debug(
                f"DecisionPolicyRegistry: registered '{policy.name}' "
                f"({policy.policy_id})"
            )

    def deregister(self, policy_id: str) -> Optional[DecisionPolicy]:
        """
        Remove and return the policy with *policy_id*, or ``None`` if not
        found.
        """
        with self._lock:
            policy = self._policies.pop(policy_id, None)
            if policy:
                _log.debug(
                    f"DecisionPolicyRegistry: deregistered '{policy.name}' "
                    f"({policy_id})"
                )
            return policy

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    def get(self, policy_id: str) -> DecisionPolicy:
        """
        Return the policy or raise :class:`PolicyNotFoundError`.
        """
        with self._lock:
            if policy_id not in self._policies:
                raise PolicyNotFoundError(policy_id)
            return self._policies[policy_id]

    def find(self, policy_id: str) -> Optional[DecisionPolicy]:
        """Return the policy or ``None`` if not registered."""
        with self._lock:
            return self._policies.get(policy_id)

    def active_policies(self) -> List[DecisionPolicy]:
        """Return all policies with status ACTIVE."""
        with self._lock:
            return [p for p in self._policies.values() if p.is_active()]

    def policies_by_type(self, policy_type: PolicyType) -> List[DecisionPolicy]:
        """Return all ACTIVE policies of *policy_type*."""
        with self._lock:
            return [
                p for p in self._policies.values()
                if p.is_active() and p.policy_type == policy_type
            ]

    def all_policies(self) -> List[DecisionPolicy]:
        """Return all policies regardless of status."""
        with self._lock:
            return list(self._policies.values())

    def policy_count(self) -> int:
        """Return the number of registered policies."""
        with self._lock:
            return len(self._policies)

    def active_count(self) -> int:
        with self._lock:
            return sum(1 for p in self._policies.values() if p.is_active())

    def clear(self) -> None:
        """Remove all policies from the registry."""
        with self._lock:
            self._policies.clear()
            _log.debug("DecisionPolicyRegistry: cleared")
