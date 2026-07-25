"""
workflow_policy_registry.py — iios.workflow.policies
-----------------------------------------------------
WorkflowPolicyRegistry — thread-safe storage and lookup for
registered governance policies.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 3
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import DEFAULT_MAX_POLICIES, PolicyDomain, PolicyType
from .exceptions import WorkflowPolicyNotFoundError, WorkflowPolicyRegistryError
from .workflow_policy import WorkflowPolicy

_log = get_logger(__name__)


class WorkflowPolicyRegistry:
    """
    Thread-safe registry for governance policies.

    Policies are indexed by policy_id, type, and domain for fast lookup.
    """

    def __init__(self, max_policies: int = DEFAULT_MAX_POLICIES) -> None:
        self._max       = max_policies
        self._policies: Dict[str, WorkflowPolicy]           = {}
        self._by_type:  Dict[str, List[str]]                = {}   # type.value → [policy_id]
        self._by_domain: Dict[str, List[str]]               = {}   # domain.value → [policy_id]
        self._lock      = threading.Lock()

    # ----------------------------------------------------------------
    # Registration
    # ----------------------------------------------------------------

    def register(self, policy: WorkflowPolicy) -> None:
        """
        Register a policy.

        Raises:
            WorkflowPolicyRegistryError if capacity exceeded.
        """
        with self._lock:
            if len(self._policies) >= self._max:
                raise WorkflowPolicyRegistryError(
                    f"Registry at capacity: limit={self._max}"
                )
            self._policies[policy.policy_id] = policy
            # Type index
            key_type = policy.policy_type.value
            self._by_type.setdefault(key_type, [])
            if policy.policy_id not in self._by_type[key_type]:
                self._by_type[key_type].append(policy.policy_id)
            # Domain index
            key_domain = policy.domain.value
            self._by_domain.setdefault(key_domain, [])
            if policy.policy_id not in self._by_domain[key_domain]:
                self._by_domain[key_domain].append(policy.policy_id)
        _log.debug(
            f"Registry: registered policy={policy.policy_id!r} "
            f"name={policy.name!r}"
        )

    def deregister(self, policy_id: str) -> bool:
        """Remove a policy by ID.  Returns True if removed, False if not found."""
        with self._lock:
            policy = self._policies.pop(policy_id, None)
            if policy is None:
                return False
            # Clean up indexes
            self._by_type.get(policy.policy_type.value, []).remove(policy_id) if (
                policy_id in self._by_type.get(policy.policy_type.value, [])
            ) else None
            self._by_domain.get(policy.domain.value, []).remove(policy_id) if (
                policy_id in self._by_domain.get(policy.domain.value, [])
            ) else None
        return True

    # ----------------------------------------------------------------
    # Lookup
    # ----------------------------------------------------------------

    def get(self, policy_id: str) -> WorkflowPolicy:
        """Return a policy by ID.  Raises WorkflowPolicyNotFoundError if missing."""
        with self._lock:
            policy = self._policies.get(policy_id)
        if policy is None:
            raise WorkflowPolicyNotFoundError(policy_id)
        return policy

    def get_or_none(self, policy_id: str) -> Optional[WorkflowPolicy]:
        """Return a policy by ID or None if not found."""
        with self._lock:
            return self._policies.get(policy_id)

    def get_by_type(self, policy_type: PolicyType) -> List[WorkflowPolicy]:
        """Return all policies of a given type."""
        with self._lock:
            ids = list(self._by_type.get(policy_type.value, []))
        return [self._policies[pid] for pid in ids if pid in self._policies]

    def get_by_domain(self, domain: PolicyDomain) -> List[WorkflowPolicy]:
        """Return all policies in a given domain."""
        with self._lock:
            ids = list(self._by_domain.get(domain.value, []))
        return [self._policies[pid] for pid in ids if pid in self._policies]

    def all_policies(self) -> List[WorkflowPolicy]:
        """Return all registered policies."""
        with self._lock:
            return list(self._policies.values())

    def enabled_policies(self) -> List[WorkflowPolicy]:
        """Return all enabled policies."""
        with self._lock:
            return [p for p in self._policies.values() if p.enabled]

    def exists(self, policy_id: str) -> bool:
        with self._lock:
            return policy_id in self._policies

    # ----------------------------------------------------------------
    # Introspection
    # ----------------------------------------------------------------

    def policy_count(self) -> int:
        with self._lock:
            return len(self._policies)

    def clear(self) -> int:
        """Clear all policies.  Returns the count cleared."""
        with self._lock:
            n = len(self._policies)
            self._policies.clear()
            self._by_type.clear()
            self._by_domain.clear()
        return n

    @property
    def max_policies(self) -> int:
        return self._max
