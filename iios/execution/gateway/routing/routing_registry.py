"""iios/execution/gateway/routing/routing_registry.py
==================================================
RoutingRegistry — lifecycle-aware store for routing policies
and routing candidates.

C6 Execution Intelligence — Phase 5, Module 4
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import (
    DEFAULT_MAX_CANDIDATES,
    DEFAULT_MAX_POLICIES,
    ROUTING_REGISTRY_SYSTEM_ID,
    VERSION,
)
from .exceptions import (
    CandidateAlreadyRegisteredError,
    CandidateNotFoundError,
    PolicyAlreadyRegisteredError,
    RoutingEngineNotRunningError,
    RoutingPolicyNotFoundError,
    RoutingRegistryCapacityError,
)
from .routing_candidate import RoutingCandidate
from .routing_policy import RoutingPolicyBase

_log = get_logger(__name__, engine_id=ROUTING_REGISTRY_SYSTEM_ID)


class RoutingRegistry(LifecycleAwareMixin):
    """
    Lifecycle-aware registry of routing policies and candidates.

    Write operations require the registry to be in RUNNING state.
    Read operations are always permitted.
    """

    SYSTEM_ID = ROUTING_REGISTRY_SYSTEM_ID

    def __init__(
        self,
        max_policies:   int = DEFAULT_MAX_POLICIES,
        max_candidates: int = DEFAULT_MAX_CANDIDATES,
    ) -> None:
        super().__init__()
        self._max_policies   = max(1, max_policies)
        self._max_candidates = max(1, max_candidates)

        self._policies:          Dict[str, RoutingPolicyBase] = {}
        self._candidates:        Dict[str, RoutingCandidate]  = {}
        self._default_policy_id: Optional[str]                = None
        self._blacklist:         set[str]                     = set()
        self._lock               = threading.RLock()

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def _on_start(self) -> None:
        _log.info("RoutingRegistry started.", version=VERSION)

    def _on_stop(self) -> None:
        _log.info("RoutingRegistry stopped.", version=VERSION)

    def _guard_write(self) -> None:
        if self.lifecycle_state() != EngineState.RUNNING:
            raise RoutingEngineNotRunningError()

    # ── Policy management ─────────────────────────────────────────────────────

    def register_policy(self, policy: RoutingPolicyBase) -> None:
        """Register a routing policy.  Requires RUNNING state."""
        self._guard_write()
        with self._lock:
            if policy.policy_id in self._policies:
                raise PolicyAlreadyRegisteredError(policy.policy_id)
            if len(self._policies) >= self._max_policies:
                raise RoutingRegistryCapacityError("policies", self._max_policies)
            self._policies[policy.policy_id] = policy
            _log.debug("Policy registered.", policy_id=policy.policy_id)

    def remove_policy(self, policy_id: str) -> None:
        """Remove a routing policy.  Requires RUNNING state."""
        self._guard_write()
        with self._lock:
            if policy_id not in self._policies:
                raise RoutingPolicyNotFoundError(policy_id)
            del self._policies[policy_id]
            if self._default_policy_id == policy_id:
                self._default_policy_id = None
            _log.debug("Policy removed.", policy_id=policy_id)

    def get_policy(self, policy_id: str) -> RoutingPolicyBase:
        """Return a policy by ID.  Raises RoutingPolicyNotFoundError."""
        with self._lock:
            if policy_id not in self._policies:
                raise RoutingPolicyNotFoundError(policy_id)
            return self._policies[policy_id]

    def get_policy_optional(self, policy_id: Optional[str]) -> Optional[RoutingPolicyBase]:
        """Return a policy by ID, or None if not found / None given."""
        if policy_id is None:
            return None
        with self._lock:
            return self._policies.get(policy_id)

    def set_default_policy(self, policy_id: str) -> None:
        """Designate the default policy.  Requires RUNNING state."""
        self._guard_write()
        with self._lock:
            if policy_id not in self._policies:
                raise RoutingPolicyNotFoundError(policy_id)
            self._default_policy_id = policy_id
            _log.debug("Default policy set.", policy_id=policy_id)

    def default_policy(self) -> Optional[RoutingPolicyBase]:
        """Return the default policy, or None if not set."""
        with self._lock:
            if self._default_policy_id is None:
                return None
            return self._policies.get(self._default_policy_id)

    def all_policies(self) -> List[RoutingPolicyBase]:
        with self._lock:
            return list(self._policies.values())

    @property
    def policy_count(self) -> int:
        with self._lock:
            return len(self._policies)

    # ── Candidate management ──────────────────────────────────────────────────

    def register_candidate(self, candidate: RoutingCandidate) -> None:
        """Register a broker routing candidate.  Requires RUNNING state."""
        self._guard_write()
        with self._lock:
            if candidate.broker_id in self._candidates:
                raise CandidateAlreadyRegisteredError(candidate.broker_id)
            if len(self._candidates) >= self._max_candidates:
                raise RoutingRegistryCapacityError("candidates", self._max_candidates)
            self._candidates[candidate.broker_id] = candidate
            _log.debug("Candidate registered.", broker_id=candidate.broker_id)

    def remove_candidate(self, broker_id: str) -> None:
        """Remove a candidate.  Requires RUNNING state."""
        self._guard_write()
        with self._lock:
            if broker_id not in self._candidates:
                raise CandidateNotFoundError(broker_id)
            del self._candidates[broker_id]
            self._blacklist.discard(broker_id)
            _log.debug("Candidate removed.", broker_id=broker_id)

    def get_candidate(self, broker_id: str) -> RoutingCandidate:
        """Return a candidate by broker_id.  Raises CandidateNotFoundError."""
        with self._lock:
            if broker_id not in self._candidates:
                raise CandidateNotFoundError(broker_id)
            return self._candidates[broker_id]

    def get_candidate_optional(self, broker_id: str) -> Optional[RoutingCandidate]:
        with self._lock:
            return self._candidates.get(broker_id)

    def all_candidates(self) -> List[RoutingCandidate]:
        """All registered candidates (including unavailable / blacklisted)."""
        with self._lock:
            return list(self._candidates.values())

    def available_candidates(self) -> List[RoutingCandidate]:
        """Candidates that are connected, authenticated, and not blacklisted."""
        with self._lock:
            return [c for c in self._candidates.values() if c.is_available]

    @property
    def candidate_count(self) -> int:
        with self._lock:
            return len(self._candidates)

    # ── Blacklist management ──────────────────────────────────────────────────

    def blacklist_broker(self, broker_id: str) -> None:
        """Blacklist a broker.  Requires RUNNING state."""
        self._guard_write()
        with self._lock:
            self._blacklist.add(broker_id)
            candidate = self._candidates.get(broker_id)
            if candidate is not None:
                candidate.blacklist()
            _log.warning("Broker blacklisted.", broker_id=broker_id)

    def unblacklist_broker(self, broker_id: str) -> None:
        """Remove a broker from the blacklist.  Requires RUNNING state."""
        self._guard_write()
        with self._lock:
            self._blacklist.discard(broker_id)
            candidate = self._candidates.get(broker_id)
            if candidate is not None:
                candidate.unblacklist()
            _log.info("Broker unblacklisted.", broker_id=broker_id)

    def is_blacklisted(self, broker_id: str) -> bool:
        with self._lock:
            return broker_id in self._blacklist

    def blacklisted_broker_ids(self) -> List[str]:
        with self._lock:
            return sorted(self._blacklist)
