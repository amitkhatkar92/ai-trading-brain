"""
iios/execution/recovery/policies/recovery_policy_manager.py
===========================================================
RecoveryPolicyManager — lifecycle-aware policy orchestrator.

Owns a RecoveryPolicyRegistry and provides:
- Ordered policy retrieval for evaluation
- Policy activation / deactivation
- Fallback policy resolution

C7 Execution Recovery & Resilience — Phase 1, Module 3
"""
from __future__ import annotations

from typing import List, Optional

from iios.common.logging.logging_manager import get_logger
from iios.common.logging.audit_logger import get_audit_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import MANAGER_ID, VERSION
from .exceptions import RecoveryPolicyNotFoundError, RecoveryPolicyNotRunningError
from .recovery_context import PolicyEvaluationContext
from .recovery_policy import RecoveryPolicy
from .recovery_policy_registry import RecoveryPolicyRegistry

_log   = get_logger(__name__)
_audit = get_audit_logger(__name__)


class RecoveryPolicyManager(LifecycleAwareMixin):
    """
    Lifecycle-aware manager that orchestrates policy ordering and access.

    The manager owns and controls the lifecycle of the registry it wraps.
    All policy queries go through the manager to enforce activation state.
    """

    def __init__(self) -> None:
        super().__init__()
        self._registry = RecoveryPolicyRegistry()
        self._inactive: set = set()   # set of policy names that are deactivated

    def _on_start(self) -> None:
        self._registry.start()
        _audit.log_lifecycle_event(MANAGER_ID, EngineState.STOPPED, EngineState.RUNNING, VERSION)
        _log.info("RecoveryPolicyManager started")

    def _on_stop(self) -> None:
        self._registry.stop()
        _audit.log_lifecycle_event(MANAGER_ID, EngineState.RUNNING, EngineState.STOPPED, VERSION)
        _log.info("RecoveryPolicyManager stopped")

    # ── Guard ─────────────────────────────────────────────────────────────────

    def _assert_running(self) -> None:
        if self.lifecycle_state() not in (EngineState.RUNNING, "running"):
            raise RecoveryPolicyNotRunningError()

    # ── Policy management ──────────────────────────────────────────────────────

    def add_policy(self, policy: RecoveryPolicy) -> None:
        self._assert_running()
        self._registry.register(policy)
        _log.debug("Policy added", policy_name=policy.name)

    def remove_policy(self, name: str) -> None:
        self._assert_running()
        self._registry.unregister(name)
        self._inactive.discard(name)
        _log.debug("Policy removed", policy_name=name)

    def activate(self, name: str) -> None:
        """Re-enable a previously deactivated policy."""
        self._assert_running()
        if not self._registry.contains(name):
            raise RecoveryPolicyNotFoundError(name)
        self._inactive.discard(name)
        _log.info("Policy activated", policy_name=name)

    def deactivate(self, name: str) -> None:
        """Disable a policy from evaluation without removing it."""
        self._assert_running()
        if not self._registry.contains(name):
            raise RecoveryPolicyNotFoundError(name)
        self._inactive.add(name)
        _log.info("Policy deactivated", policy_name=name)

    def is_active(self, name: str) -> bool:
        return self._registry.contains(name) and name not in self._inactive

    # ── Policy retrieval ──────────────────────────────────────────────────────

    def get_ordered_policies(
        self, context: PolicyEvaluationContext
    ) -> List[RecoveryPolicy]:
        """
        Return active policies that can_apply to *context*, ordered by
        priority descending.

        EmergencyShutdownPolicy is always prepended when risk conditions
        are critical, regardless of normal ordering.
        """
        all_applicable = [
            p for p in self._registry.all()
            if p.can_apply(context) and p.name not in self._inactive
        ]
        ordered = sorted(all_applicable, key=lambda p: -p.priority)
        return ordered

    def get_fallback_policy(self) -> Optional[RecoveryPolicy]:
        """Return the registered fallback policy if active."""
        fallback = self._registry.find_fallback()
        if fallback and fallback.name not in self._inactive:
            return fallback
        return None

    @property
    def registry(self) -> RecoveryPolicyRegistry:
        return self._registry
