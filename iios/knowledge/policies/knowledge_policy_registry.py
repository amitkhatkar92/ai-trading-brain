"""
knowledge_policy_registry.py — iios.knowledge.policies
--------------------------------------------------------
KnowledgePolicyRegistry — thread-safe store for governance policies.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import DEFAULT_MAX_POLICIES, PolicyDomain, PolicyPriority, PolicyStatus, PolicyType
from .exceptions import GovernanceCapacityError, PolicyLoadError, PolicyNotFoundError
from .knowledge_policy import KnowledgePolicy

_log = get_logger(__name__)


class KnowledgePolicyRegistry:
    """
    Thread-safe registry of governance policies.

    Active policies are evaluated during governance runs.
    Archived policies are retained for audit purposes but not evaluated.
    """

    def __init__(self, max_policies: int = DEFAULT_MAX_POLICIES) -> None:
        self._max_policies = max_policies
        self._active:   Dict[str, KnowledgePolicy] = {}
        self._archived: Dict[str, KnowledgePolicy] = {}
        self._lock      = threading.Lock()

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, policy: KnowledgePolicy) -> None:
        """Register a policy. Raises PolicyLoadError if duplicate or capacity exceeded."""
        with self._lock:
            if policy.policy_id in self._active:
                raise PolicyLoadError(
                    f"Policy already registered: {policy.policy_id!r}",
                    policy_id=policy.policy_id,
                )
            if len(self._active) >= self._max_policies:
                raise GovernanceCapacityError(limit=self._max_policies)
            self._active[policy.policy_id] = policy
            _log.debug(
                f"Policy registered: policy_id={policy.policy_id!r} name={policy.name!r}"
            )

    def deregister(self, policy_id: str) -> bool:
        """Remove a policy from the active registry. Returns True if removed."""
        with self._lock:
            if policy_id in self._active:
                del self._active[policy_id]
                _log.debug(f"Policy deregistered: policy_id={policy_id!r}")
                return True
            return False

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def get(self, policy_id: str) -> KnowledgePolicy:
        """Retrieve a policy. Raises PolicyNotFoundError if missing."""
        with self._lock:
            policy = self._active.get(policy_id) or self._archived.get(policy_id)
            if policy is None:
                raise PolicyNotFoundError(policy_id=policy_id)
            return policy

    def get_optional(self, policy_id: str) -> Optional[KnowledgePolicy]:
        """Retrieve a policy or None if not found."""
        with self._lock:
            return self._active.get(policy_id) or self._archived.get(policy_id)

    def all_active(self) -> List[KnowledgePolicy]:
        """Return all policies in the active bucket (any status)."""
        with self._lock:
            return list(self._active.values())

    def all_archived(self) -> List[KnowledgePolicy]:
        with self._lock:
            return list(self._archived.values())

    def active_only(self) -> List[KnowledgePolicy]:
        """Return only policies with ACTIVE status (evaluated during governance)."""
        with self._lock:
            return [p for p in self._active.values() if p.status == PolicyStatus.ACTIVE]

    def by_type(self, policy_type: PolicyType) -> List[KnowledgePolicy]:
        with self._lock:
            return [p for p in self._active.values() if p.policy_type == policy_type]

    def by_domain(self, domain: PolicyDomain) -> List[KnowledgePolicy]:
        with self._lock:
            return [p for p in self._active.values() if p.domain == domain]

    def by_priority(self, priority: PolicyPriority) -> List[KnowledgePolicy]:
        with self._lock:
            return [p for p in self._active.values() if p.priority == priority]

    # ------------------------------------------------------------------
    # Archival
    # ------------------------------------------------------------------

    def archive_policy(self, policy_id: str) -> bool:
        """Move a policy from active to archived. Returns True if moved."""
        with self._lock:
            policy = self._active.pop(policy_id, None)
            if policy is None:
                return False
            policy.archive()
            self._archived[policy_id] = policy
            _log.debug(f"Policy archived: policy_id={policy_id!r}")
            return True

    # ------------------------------------------------------------------
    # Counts
    # ------------------------------------------------------------------

    def active_count(self) -> int:
        with self._lock:
            return len(self._active)

    def archived_count(self) -> int:
        with self._lock:
            return len(self._archived)

    def total_count(self) -> int:
        with self._lock:
            return len(self._active) + len(self._archived)

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------

    def clear(self) -> None:
        with self._lock:
            self._active.clear()
            self._archived.clear()
