"""iios/execution/monitoring/integration/monitoring_integration_manager.py
==================================================
MonitoringIntegrationManager — lifecycle-aware orchestration layer
that owns the registry, history, statistics, and event dispatch for
the integration subsystem.

C6 Execution Intelligence — Phase 6, Module 6
"""
from __future__ import annotations

import threading
from typing import Callable, List, Optional

from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import (
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_REQUESTS,
    DEFAULT_MAX_SESSIONS,
    MANAGER_SYSTEM_ID,
    VERSION,
)
from .exceptions import IntegrationNotRunningError
from .monitoring_integration_events import IntegrationEvent
from .monitoring_integration_history import IntegrationHistory
from .monitoring_integration_registry import IntegrationRegistry
from .monitoring_integration_response import MonitoringIntegrationResponse
from .monitoring_integration_snapshot import MonitoringIntegrationSnapshot
from .monitoring_integration_statistics import IntegrationStatistics

_log = get_logger(__name__)


class MonitoringIntegrationManager(LifecycleAwareMixin):
    """
    Orchestrates the integration sub-system's storage and event layer.

    Owns:
    - ``IntegrationRegistry``    — response + snapshot CRUD
    - ``IntegrationHistory``     — bounded deque history
    - ``IntegrationStatistics``  — runtime counters (shared reference)

    Responsibilities:
    - Start/stop registry alongside its own lifecycle.
    - Provide convenience query methods over registry and history.
    - Fan-out domain events to registered listeners.
    """

    def __init__(
        self,
        max_requests: int = DEFAULT_MAX_REQUESTS,
        max_history:  int = DEFAULT_MAX_HISTORY,
    ) -> None:
        super().__init__()
        self._max_requests = max(1, max_requests)
        self._max_history  = max(1, max_history)

        self._registry  = IntegrationRegistry(
            max_responses = self._max_requests,
            max_snapshots = DEFAULT_MAX_SESSIONS,
        )
        self._history   = IntegrationHistory(
            max_responses = self._max_history,
            max_snapshots = self._max_history,
            max_events    = self._max_history,
        )
        self._stats = IntegrationStatistics()

        self._listeners: List[Callable[[IntegrationEvent], None]] = []
        self._listeners_lock = threading.Lock()

    # ── LifecycleAwareMixin hooks ──────────────────────────────────────────────

    def _on_start(self) -> None:
        self._registry.start()
        _log.info(
            "MonitoringIntegrationManager started.",
            system_id=MANAGER_SYSTEM_ID,
            version=VERSION,
        )

    def _on_stop(self) -> None:
        self._registry.stop()
        _log.info(
            "MonitoringIntegrationManager stopped.",
            system_id=MANAGER_SYSTEM_ID,
            total_requests=self._stats.requests_received,
        )

    # ── Guard ─────────────────────────────────────────────────────────────────

    def _assert_running(self) -> None:
        if self.lifecycle_state() not in (EngineState.RUNNING, "running"):
            raise IntegrationNotRunningError()

    # ── Response API ──────────────────────────────────────────────────────────

    def store_response(self, response: MonitoringIntegrationResponse) -> None:
        self._assert_running()
        self._registry.store_response(response)
        self._history.append_response(response)
        self._stats.record_request_received()

    def get_response(self, response_id: str) -> MonitoringIntegrationResponse:
        self._assert_running()
        return self._registry.get_response(response_id)

    def find_response(
        self, response_id: str
    ) -> Optional[MonitoringIntegrationResponse]:
        return self._registry.find_response(response_id)

    def responses_for_session(
        self, session_id: str
    ) -> List[MonitoringIntegrationResponse]:
        self._assert_running()
        return self._registry.responses_for_session(session_id)

    def all_responses(self) -> List[MonitoringIntegrationResponse]:
        self._assert_running()
        return self._registry.all_responses()

    # ── Snapshot API ──────────────────────────────────────────────────────────

    def store_snapshot(self, snapshot: MonitoringIntegrationSnapshot) -> None:
        self._assert_running()
        self._registry.store_snapshot(snapshot)
        self._history.append_snapshot(snapshot)

    def latest_snapshot_for_session(
        self, session_id: str
    ) -> Optional[MonitoringIntegrationSnapshot]:
        return self._registry.latest_snapshot_for_session(session_id)

    # ── Statistics ────────────────────────────────────────────────────────────

    def statistics(self) -> IntegrationStatistics:
        """Return a copy of the integration statistics."""
        return self._stats.copy()

    def raw_statistics(self) -> IntegrationStatistics:
        """Return the live (mutable) statistics object."""
        return self._stats

    # ── History ───────────────────────────────────────────────────────────────

    def history(self) -> IntegrationHistory:
        """Return the integration history."""
        return self._history

    # ── Event dispatch ────────────────────────────────────────────────────────

    def add_event_listener(
        self, listener: Callable[[IntegrationEvent], None]
    ) -> None:
        with self._listeners_lock:
            self._listeners.append(listener)

    def remove_event_listener(
        self, listener: Callable[[IntegrationEvent], None]
    ) -> None:
        with self._listeners_lock:
            self._listeners = [l for l in self._listeners if l != listener]

    def emit(self, event: IntegrationEvent) -> None:
        with self._listeners_lock:
            listeners = list(self._listeners)
        for listener in listeners:
            try:
                listener(event)
            except Exception as exc:  # noqa: BLE001
                _log.warning(
                    "Integration event listener raised.",
                    listener=repr(listener),
                    error=str(exc),
                )
