"""
integration_policy_registry.py — iios.integration.policies
-----------------------------------------------------------
IntegrationPolicyRegistry — thread-safe storage for governance policies.

C15 Enterprise Integration & Connectivity — Phase 1, Module 3
"""
from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional

from .constants import DEFAULT_MAX_POLICIES, PolicyDomain, PolicyPriority, PolicyType
from .exceptions import PolicyNotFoundError, PolicyRegistrationError
from .integration_policy import IntegrationPolicy


class IntegrationPolicyRegistry:
    """
    Thread-safe registry for governance policies.

    Policies are keyed by policy_id and bounded by max_policies.
    """

    def __init__(self, max_policies: int = DEFAULT_MAX_POLICIES) -> None:
        self._max      = max_policies
        self._policies: Dict[str, IntegrationPolicy] = {}
        self._lock     = threading.Lock()

    # ── registration ──────────────────────────────────────────────────

    def register(self, policy: IntegrationPolicy) -> None:
        with self._lock:
            if len(self._policies) >= self._max:
                raise PolicyRegistrationError(
                    f"Policy registry at capacity ({self._max})"
                )
            self._policies[policy.policy_id] = policy

    def deregister(self, policy_id: str) -> bool:
        with self._lock:
            if policy_id in self._policies:
                del self._policies[policy_id]
                return True
        return False

    # ── lookup ────────────────────────────────────────────────────────

    def get(self, policy_id: str) -> Optional[IntegrationPolicy]:
        with self._lock:
            return self._policies.get(policy_id)

    def get_or_raise(self, policy_id: str) -> IntegrationPolicy:
        policy = self.get(policy_id)
        if policy is None:
            raise PolicyNotFoundError(policy_id)
        return policy

    def has(self, policy_id: str) -> bool:
        with self._lock:
            return policy_id in self._policies

    # ── filtering ─────────────────────────────────────────────────────

    def by_domain(self, domain: PolicyDomain) -> List[IntegrationPolicy]:
        with self._lock:
            return [p for p in self._policies.values() if p.domain == domain]

    def by_type(self, policy_type: PolicyType) -> List[IntegrationPolicy]:
        with self._lock:
            return [p for p in self._policies.values() if p.policy_type == policy_type]

    def by_priority(self, priority: PolicyPriority) -> List[IntegrationPolicy]:
        with self._lock:
            return [p for p in self._policies.values() if p.priority == priority]

    def all_enabled(self) -> List[IntegrationPolicy]:
        with self._lock:
            return [p for p in self._policies.values() if p.enabled]

    def all_policies(self) -> List[IntegrationPolicy]:
        with self._lock:
            return list(self._policies.values())

    # ── metrics ───────────────────────────────────────────────────────

    def count(self) -> int:
        with self._lock:
            return len(self._policies)

    def summary(self) -> Dict[str, Any]:
        with self._lock:
            policies = list(self._policies.values())
        return {
            "total":     len(policies),
            "enabled":   sum(1 for p in policies if p.enabled),
            "by_domain": {
                d.value: sum(1 for p in policies if p.domain == d)
                for d in PolicyDomain
            },
            "by_type": {
                t.value: sum(1 for p in policies if p.policy_type == t)
                for t in PolicyType
            },
        }

    def clear(self) -> None:
        with self._lock:
            self._policies.clear()
