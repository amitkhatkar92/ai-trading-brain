"""
policy_registry.py -- iios.ai.governance.policy
=================================================
:class:`PolicyRegistry` — thread-safe registry for GovernancePolicy objects.

A8 AI Governance Platform — Phase 3, Module 8
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from ..core.governance_policy import GovernancePolicy
from ..exceptions.governance_exceptions import (
    AIPolicyAlreadyExistsError,
    AIPolicyNotFoundError,
)


class PolicyRegistry:
    """Thread-safe in-memory registry for :class:`GovernancePolicy` objects."""

    def __init__(self) -> None:
        self._lock:     threading.Lock             = threading.Lock()
        self._policies: Dict[str, GovernancePolicy] = {}

    def register(self, policy: GovernancePolicy) -> None:
        with self._lock:
            if policy.policy_id in self._policies:
                raise AIPolicyAlreadyExistsError(
                    f"Policy {policy.policy_id!r} already registered"
                )
            self._policies[policy.policy_id] = policy

    def deregister(self, policy_id: str) -> None:
        with self._lock:
            self._policies.pop(policy_id, None)

    def get(self, policy_id: str) -> GovernancePolicy:
        with self._lock:
            p = self._policies.get(policy_id)
        if p is None:
            raise AIPolicyNotFoundError(f"Policy {policy_id!r} not found")
        return p

    def get_optional(self, policy_id: str) -> Optional[GovernancePolicy]:
        with self._lock:
            return self._policies.get(policy_id)

    def list_policies(self, active_only: bool = True) -> List[GovernancePolicy]:
        with self._lock:
            policies = list(self._policies.values())
        if active_only:
            policies = [p for p in policies if p.is_active]
        return sorted(policies, key=lambda p: -p.priority)

    def count(self) -> int:
        with self._lock:
            return len(self._policies)
