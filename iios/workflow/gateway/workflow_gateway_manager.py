"""
workflow_gateway_manager.py — iios.workflow.gateway
----------------------------------------------------
WorkflowGatewayManager — manages the gateway lifecycle:
initialize, start, stop, restart.

The manager owns the component registry, component factory,
health, status, statistics, history, and event bus.
It does NOT process requests — that is the gateway's job.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 6
"""
from __future__ import annotations

import time
import threading
from typing import Any, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import (
    DEFAULT_GATEWAY_ID,
    ACTOR_MANAGER,
    GatewayEventType,
    GatewayState,
)
from .exceptions import (
    WorkflowGatewayNotInitializedError,
    WorkflowGatewayNotRunningError,
)
from .workflow_component_factory import WorkflowComponentFactory
from .workflow_component_registry import WorkflowComponentRegistry
from .workflow_gateway_events import WorkflowGatewayEvent, WorkflowGatewayEventBus
from .workflow_gateway_health import WorkflowGatewayHealth
from .workflow_gateway_history import WorkflowGatewayHistory
from .workflow_gateway_statistics import WorkflowGatewayStatistics
from .workflow_gateway_status import WorkflowGatewayStatus, WorkflowStatus

_log = get_logger(__name__)


class WorkflowGatewayManager:
    """
    Manages the Enterprise Workflow Gateway lifecycle.

    Owns:
        - WorkflowComponentRegistry (M1–M5 instances)
        - WorkflowGatewayStatistics
        - WorkflowGatewayHistory
        - WorkflowGatewayEventBus
        - WorkflowGatewayHealth
        - WorkflowGatewayStatus

    Thread-safe.
    """

    def __init__(
        self,
        gateway_id:          str                                     = DEFAULT_GATEWAY_ID,
        component_factory:   Optional[WorkflowComponentFactory]      = None,
        component_registry:  Optional[WorkflowComponentRegistry]     = None,
        stats:               Optional[WorkflowGatewayStatistics]     = None,
        history:             Optional[WorkflowGatewayHistory]        = None,
        event_bus:           Optional[WorkflowGatewayEventBus]       = None,
        health_monitor:      Optional[WorkflowGatewayHealth]         = None,
        status_tracker:      Optional[WorkflowGatewayStatus]         = None,
    ) -> None:
        self._gateway_id     = gateway_id
        self._factory        = component_factory or WorkflowComponentFactory()
        self._registry       = component_registry or WorkflowComponentRegistry()
        self._stats          = stats          or WorkflowGatewayStatistics()
        self._history        = history        or WorkflowGatewayHistory()
        self._event_bus      = event_bus      or WorkflowGatewayEventBus()
        self._health_monitor = health_monitor or WorkflowGatewayHealth()
        self._status_tracker = status_tracker or WorkflowGatewayStatus()

        self._state          = GatewayState.UNINITIALIZED
        self._started_at     = time.monotonic()
        self._active_count   = 0
        self._total_count    = 0
        self._lock           = threading.Lock()

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def gateway_id(self) -> str:
        return self._gateway_id

    @property
    def state(self) -> GatewayState:
        with self._lock:
            return self._state

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self._state == GatewayState.RUNNING

    @property
    def component_registry(self) -> WorkflowComponentRegistry:
        return self._registry

    @property
    def stats(self) -> WorkflowGatewayStatistics:
        return self._stats

    @property
    def history(self) -> WorkflowGatewayHistory:
        return self._history

    @property
    def event_bus(self) -> WorkflowGatewayEventBus:
        return self._event_bus

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def initialize(self) -> None:
        """Initialize the gateway — create and register M1–M5 components."""
        with self._lock:
            if self._state not in (GatewayState.UNINITIALIZED, GatewayState.STOPPED):
                _log.warning(
                    f"Manager: initialize called in state={self._state.value!r} — skipped"
                )
                return
            self._state = GatewayState.INITIALIZED

        _log.info(f"Manager: initializing gateway={self._gateway_id!r}")
        self._factory.build_and_register_all(self._registry)
        self._emit(GatewayEventType.GATEWAY_INITIALIZED)
        _log.info(f"Manager: gateway={self._gateway_id!r} initialized")

    def start(self) -> None:
        """Start the gateway — transition to RUNNING."""
        with self._lock:
            if self._state == GatewayState.UNINITIALIZED:
                raise WorkflowGatewayNotInitializedError()
            if self._state == GatewayState.RUNNING:
                return
            self._state      = GatewayState.RUNNING
            self._started_at = time.monotonic()

        self._emit(GatewayEventType.GATEWAY_STARTED)
        _log.info(f"Manager: gateway={self._gateway_id!r} RUNNING")

    def stop(self) -> None:
        """Stop the gateway gracefully."""
        with self._lock:
            if self._state == GatewayState.STOPPED:
                return
            self._state = GatewayState.STOPPING

        _log.info(f"Manager: stopping gateway={self._gateway_id!r}")
        self._emit(GatewayEventType.GATEWAY_STOPPED)

        with self._lock:
            self._state = GatewayState.STOPPED

        _log.info(f"Manager: gateway={self._gateway_id!r} STOPPED")

    def restart(self) -> None:
        """Stop and re-initialize/start the gateway."""
        _log.info(f"Manager: restarting gateway={self._gateway_id!r}")
        self.stop()
        self._registry.clear()
        with self._lock:
            self._state = GatewayState.UNINITIALIZED
        self.initialize()
        self.start()

    # ── Counters (used by gateway during dispatch) ─────────────────────────────

    def increment_active(self) -> None:
        with self._lock:
            self._active_count += 1

    def decrement_active(self) -> None:
        with self._lock:
            self._active_count  = max(0, self._active_count - 1)
            self._total_count  += 1

    def active_count(self) -> int:
        with self._lock:
            return self._active_count

    def total_count(self) -> int:
        with self._lock:
            return self._total_count

    # ── Health & status ────────────────────────────────────────────────────────

    def health_summary(self):
        return self._health_monitor.report(
            gateway_id         = self._gateway_id,
            gateway_state      = self.state,
            component_statuses = self._registry.component_statuses(),
            started_at         = self._started_at,
            active_requests    = self.active_count(),
        )

    def status_snapshot(self) -> WorkflowStatus:
        return self._status_tracker.capture(
            gateway_id        = self._gateway_id,
            gateway_state     = self.state,
            active_workflows  = self.active_count(),
            pending_workflows = 0,
            total_processed   = self.total_count(),
            started_at        = self._started_at,
        )

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _emit(self, event_type: GatewayEventType, workflow_id: str = "") -> None:
        evt = WorkflowGatewayEvent.create(
            event_type,
            gateway_id  = self._gateway_id,
            workflow_id = workflow_id,
        )
        self._event_bus.emit(evt)
