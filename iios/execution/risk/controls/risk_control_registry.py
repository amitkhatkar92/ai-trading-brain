"""iios/execution/risk/controls/risk_control_registry.py
==================================================
ControlPolicyRegistry — LifecycleAwareMixin store for control policies.

C6 Execution Intelligence — Phase 4, Module 4
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin
from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger

from .constants import (
    REGISTRY_SYSTEM_ID,
    VERSION,
    PolicyType,
)
from .exceptions import (
    ControlNotRunningError,
    ControlRegistrationError,
    PolicyNotFoundError,
)
from .risk_control_events import (
    ControlEvent,
)
from .risk_control_policy import BasePolicy

_log   = get_logger(__name__, engine_id=REGISTRY_SYSTEM_ID)
_audit = get_audit_logger(__name__, engine_id=REGISTRY_SYSTEM_ID)


class ControlPolicyRegistry(LifecycleAwareMixin):
    """
    Lifecycle-aware registry for BasePolicy instances.

    One policy per PolicyType is allowed.  Attempting to register a second
    policy with the same type raises ControlRegistrationError.
    """

    def __init__(self) -> None:
        super().__init__()
        self._policies: Dict[PolicyType, BasePolicy] = {}
        self._lock = threading.Lock()

    # ── LifecycleAwareMixin ───────────────────────────────────────────────────

    def _assert_running(self) -> None:
        if self.lifecycle_state() != EngineState.RUNNING:
            raise ControlNotRunningError()

    def _on_start(self) -> None:
        _audit.log_lifecycle_event(
            REGISTRY_SYSTEM_ID, EngineState.STOPPED, EngineState.RUNNING, VERSION
        )
        _log.info("ControlPolicyRegistry started.")

    def _on_stop(self) -> None:
        _audit.log_lifecycle_event(
            REGISTRY_SYSTEM_ID, EngineState.RUNNING, EngineState.STOPPED, VERSION
        )
        _log.info("ControlPolicyRegistry stopped.", policy_count=self.count)

    # ── Registration ──────────────────────────────────────────────────────────

    def register(self, policy: BasePolicy) -> None:
        """Register a policy.  Raises if already registered."""
        self._assert_running()
        if not isinstance(policy, BasePolicy):
            raise ControlRegistrationError(
                f"policy must be a BasePolicy subclass; got {type(policy)}"
            )
        with self._lock:
            if policy.policy_type in self._policies:
                raise ControlRegistrationError(
                    f"Policy '{policy.policy_type.value}' is already registered. "
                    "Deregister it first."
                )
            self._policies[policy.policy_type] = policy
        _log.info("Policy registered.", policy_type=policy.policy_type.value)

    def deregister(self, policy_type: PolicyType) -> None:
        """Remove a policy by type."""
        self._assert_running()
        with self._lock:
            if policy_type not in self._policies:
                raise PolicyNotFoundError(policy_type.value)
            del self._policies[policy_type]
        _log.info("Policy deregistered.", policy_type=policy_type.value)

    def replace(self, policy: BasePolicy) -> None:
        """Register or replace a policy (no error if already present)."""
        self._assert_running()
        with self._lock:
            self._policies[policy.policy_type] = policy
        _log.info("Policy replaced.", policy_type=policy.policy_type.value)

    # ── Reads ─────────────────────────────────────────────────────────────────

    def get(self, policy_type: PolicyType) -> Optional[BasePolicy]:
        with self._lock:
            return self._policies.get(policy_type)

    def require(self, policy_type: PolicyType) -> BasePolicy:
        with self._lock:
            policy = self._policies.get(policy_type)
        if policy is None:
            raise PolicyNotFoundError(policy_type.value)
        return policy

    def contains(self, policy_type: PolicyType) -> bool:
        with self._lock:
            return policy_type in self._policies

    def all(self) -> List[BasePolicy]:
        with self._lock:
            return list(self._policies.values())

    def all_types(self) -> List[PolicyType]:
        with self._lock:
            return list(self._policies.keys())

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._policies)

    @property
    def is_empty(self) -> bool:
        with self._lock:
            return len(self._policies) == 0
