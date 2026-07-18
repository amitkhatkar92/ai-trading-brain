"""
iios/execution/recovery/policies/recovery_policy_registry.py
============================================================
RecoveryPolicyRegistry — lifecycle-aware, thread-safe store for policies.

C7 Execution Recovery & Resilience — Phase 1, Module 3
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from iios.common.logging.logging_manager import get_logger
from iios.common.logging.audit_logger import get_audit_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import (
    DEFAULT_MAX_POLICIES,
    REGISTRY_ID,
    VERSION,
    FailureCategory,
    RecoveryStrategyType,
)
from .exceptions import (
    RecoveryPolicyConflictError,
    RecoveryPolicyNotFoundError,
    RecoveryPolicyNotRunningError,
    RecoveryPolicyRegistryError,
)
from .recovery_policy import RecoveryPolicy

_log   = get_logger(__name__)
_audit = get_audit_logger(__name__)


class RecoveryPolicyRegistry(LifecycleAwareMixin):
    """
    Thread-safe registry for RecoveryPolicy instances.

    Policies are stored by name.  Duplicate names are rejected.  The
    registry must be started before any write operations.
    """

    def __init__(self, max_policies: int = DEFAULT_MAX_POLICIES) -> None:
        super().__init__()
        self._max_policies = max_policies
        self._lock: threading.Lock = threading.Lock()
        self._policies: Dict[str, RecoveryPolicy] = {}

    def _on_start(self) -> None:
        _audit.log_lifecycle_event(REGISTRY_ID, EngineState.STOPPED, EngineState.RUNNING, VERSION)
        _log.info("RecoveryPolicyRegistry started", max_policies=self._max_policies)

    def _on_stop(self) -> None:
        _audit.log_lifecycle_event(REGISTRY_ID, EngineState.RUNNING, EngineState.STOPPED, VERSION)
        _log.info("RecoveryPolicyRegistry stopped")
        with self._lock:
            self._policies.clear()

    # ── Internal guard ────────────────────────────────────────────────────────

    def _assert_running(self) -> None:
        if self.lifecycle_state() not in (EngineState.RUNNING, "running"):
            raise RecoveryPolicyNotRunningError()

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def register(self, policy: RecoveryPolicy) -> None:
        """Register *policy*.  Raises if the registry is full or name conflicts."""
        self._assert_running()
        with self._lock:
            if len(self._policies) >= self._max_policies:
                raise RecoveryPolicyRegistryError(
                    f"Registry capacity reached ({self._max_policies})"
                )
            if policy.name in self._policies:
                raise RecoveryPolicyConflictError(policy.name, self._policies[policy.name].name)
            self._policies[policy.name] = policy
            _log.debug(
                "Policy registered",
                policy_name=policy.name,
                policy_type=policy.policy_type.value,
            )

    def unregister(self, name: str) -> None:
        """Remove the policy with *name*.  Raises if not found."""
        self._assert_running()
        with self._lock:
            if name not in self._policies:
                raise RecoveryPolicyNotFoundError(name)
            del self._policies[name]
            _log.debug("Policy unregistered", policy_name=name)

    def get(self, name: str) -> RecoveryPolicy:
        """Return the policy with *name*.  Raises if not found."""
        with self._lock:
            if name not in self._policies:
                raise RecoveryPolicyNotFoundError(name)
            return self._policies[name]

    def find(self, name: str) -> Optional[RecoveryPolicy]:
        """Return the policy with *name*, or None if not found."""
        with self._lock:
            return self._policies.get(name)

    # ── Queries ───────────────────────────────────────────────────────────────

    def all(self) -> List[RecoveryPolicy]:
        """Return all registered policies (unsorted snapshot)."""
        with self._lock:
            return list(self._policies.values())

    def for_category(self, category: FailureCategory) -> List[RecoveryPolicy]:
        """Return policies applicable to *category*, sorted by priority descending."""
        with self._lock:
            return sorted(
                [
                    p for p in self._policies.values()
                    if not p.applicable_categories or category in p.applicable_categories
                ],
                key=lambda p: -p.priority,
            )

    def for_type(self, strategy_type: RecoveryStrategyType) -> List[RecoveryPolicy]:
        """Return policies whose policy_type matches *strategy_type*."""
        with self._lock:
            return [
                p for p in self._policies.values()
                if p.policy_type == strategy_type
            ]

    def find_fallback(self) -> Optional[RecoveryPolicy]:
        """Return the registered fallback policy, or None."""
        with self._lock:
            fallbacks = [p for p in self._policies.values() if p.is_fallback]
            if not fallbacks:
                return None
            # Pick the lowest-priority fallback
            return min(fallbacks, key=lambda p: p.priority)

    def contains(self, name: str) -> bool:
        with self._lock:
            return name in self._policies

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._policies)
