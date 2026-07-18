"""
iios/execution/recovery/failover/failover_strategy_registry.py
==============================================================
FailoverStrategyRegistry — lifecycle-aware store for FailoverPlan objects.

Plans are keyed by FailoverAction (primary action) so the controller
can quickly look up the plan for an incoming request.

C7 Execution Recovery & Resilience — Phase 1, Module 4
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from iios.common.logging.logging_manager import get_logger
from iios.common.logging.audit_logger import get_audit_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import REGISTRY_ID, VERSION, FailoverAction, FailoverType
from .exceptions import (
    FailoverNotRunningError,
    FailoverStrategyNotFoundError,
    FailoverRegistryError,
)
from .failover_plan import DEFAULT_PLAN_FACTORIES, FailoverPlan

_log   = get_logger(__name__)
_audit = get_audit_logger(__name__)


class FailoverStrategyRegistry(LifecycleAwareMixin):
    """
    Lifecycle-aware registry for FailoverPlan objects.

    At startup, all default plans are auto-registered.
    Additional plans may be registered at runtime.
    """

    def __init__(self) -> None:
        super().__init__()
        self._lock: threading.Lock = threading.Lock()
        self._plans: Dict[str, FailoverPlan] = {}   # keyed by primary_action.value

    def _on_start(self) -> None:
        _audit.log_lifecycle_event(REGISTRY_ID, EngineState.STOPPED, EngineState.RUNNING, VERSION)
        self._register_defaults()
        _log.info("FailoverStrategyRegistry started", plan_count=len(self._plans))

    def _on_stop(self) -> None:
        _audit.log_lifecycle_event(REGISTRY_ID, EngineState.RUNNING, EngineState.STOPPED, VERSION)
        _log.info("FailoverStrategyRegistry stopped")
        with self._lock:
            self._plans.clear()

    def _register_defaults(self) -> None:
        with self._lock:
            for action, factory in DEFAULT_PLAN_FACTORIES.items():
                plan = factory()
                self._plans[action.value] = plan

    # ── Guard ─────────────────────────────────────────────────────────────────

    def _assert_running(self) -> None:
        if self.lifecycle_state() not in (EngineState.RUNNING, "running"):
            raise FailoverNotRunningError()

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def register(self, plan: FailoverPlan) -> None:
        """Register *plan* (overwrites existing plan for the same action)."""
        self._assert_running()
        with self._lock:
            self._plans[plan.primary_action.value] = plan
            _log.debug("Failover plan registered", plan_name=plan.name, action=plan.primary_action.value)

    def get_plan(self, action: FailoverAction) -> FailoverPlan:
        """Return the plan for *action*.  Raises if not found."""
        with self._lock:
            plan = self._plans.get(action.value)
            if plan is None:
                raise FailoverStrategyNotFoundError(action.value)
            return plan

    def find_plan(self, action: FailoverAction) -> Optional[FailoverPlan]:
        """Return the plan for *action*, or None if not found."""
        with self._lock:
            return self._plans.get(action.value)

    def all(self) -> List[FailoverPlan]:
        with self._lock:
            return list(self._plans.values())

    def for_type(self, failover_type: FailoverType) -> List[FailoverPlan]:
        with self._lock:
            return [p for p in self._plans.values() if p.failover_type == failover_type]

    def contains(self, action: FailoverAction) -> bool:
        with self._lock:
            return action.value in self._plans

    @property
    def plan_count(self) -> int:
        with self._lock:
            return len(self._plans)
