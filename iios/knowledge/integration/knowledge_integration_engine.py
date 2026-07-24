"""
knowledge_integration_engine.py — iios.knowledge.integration
------------------------------------------------------------
KnowledgeIntegrationEngine — the ONLY public entry point for the
Enterprise Knowledge Intelligence subsystem.

External components MUST NOT directly access M1–M5.
All interactions MUST occur through this engine.

Public API:
    initialize()  → None
    start()       → None
    stop()        → None
    restart()     → None
    health()      → KnowledgeHealthSummary
    status()      → KnowledgeIntegrationStatus
    statistics()  → KnowledgeStatistics
    snapshot()    → KnowledgeIntegrationSnapshot
    history()     → List[KnowledgeIntegrationResponse]
    validate()    → IntegrationValidationReport
    submit()      → KnowledgeIntegrationResponse
    query()       → KnowledgeIntegrationResponse
    search()      → KnowledgeIntegrationResponse
    retrieve()    → KnowledgeIntegrationResponse

C14 Enterprise Knowledge Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

import threading
import time
from typing import Any, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import (
    INTEGRATION_SYSTEM_ID,
    VERSION,
    IntegrationEventType,
    IntegrationRequestType,
    IntegrationState,
)
from .exceptions import IntegrationStateError
from .knowledge_component_factory import KnowledgeComponentFactory
from .knowledge_component_registry import KnowledgeComponentRegistry
from .knowledge_integration_events import IntegrationEvent, IntegrationEventBus
from .knowledge_integration_health import (
    KnowledgeHealthSummary,
    KnowledgeIntegrationHealth,
)
from .knowledge_integration_history import KnowledgeIntegrationHistory
from .knowledge_integration_manager import KnowledgeIntegrationManager
from .knowledge_integration_registry import KnowledgeIntegrationRegistry
from .knowledge_integration_request import KnowledgeIntegrationRequest
from .knowledge_integration_response import KnowledgeIntegrationResponse
from .knowledge_integration_snapshot import KnowledgeIntegrationSnapshot
from .knowledge_integration_statistics import (
    KnowledgeIntegrationStatistics,
    KnowledgeStatistics,
)
from .knowledge_integration_status import (
    KnowledgeIntegrationStatus,
    KnowledgeIntegrationStatusTracker,
)
from .knowledge_integration_validation import (
    IntegrationValidationReport,
    KnowledgeIntegrationValidation,
)

_log = get_logger(__name__)

SYSTEM_ID = INTEGRATION_SYSTEM_ID
VERSION_   = VERSION


class KnowledgeIntegrationEngine:
    """
    The ONLY public interface to the Enterprise Knowledge Intelligence subsystem.

    Coordinates M1 (Lifecycle), M2 (Engine), M3 (Governance),
    M4 (Intelligence), and M5 (Snapshot).

    Does NOT perform lifecycle management, reasoning, semantic retrieval,
    embedding generation, or governance policy evaluation.  It only coordinates.

    Thread-safe.  Not a LifecycleAwareMixin — M6 is integration-only.
    """

    SYSTEM_ID = INTEGRATION_SYSTEM_ID
    VERSION   = VERSION_

    def __init__(
        self,
        *,
        component_factory: Optional[KnowledgeComponentFactory] = None,
        registry:          Optional[KnowledgeComponentRegistry] = None,
    ) -> None:
        self._lock           = threading.Lock()
        self._state          = IntegrationState.STOPPED
        self._factory        = component_factory or KnowledgeComponentFactory()
        self._registry:      Optional[KnowledgeComponentRegistry] = registry
        self._stats          = KnowledgeIntegrationStatistics()
        self._event_bus      = IntegrationEventBus()
        self._validator      = KnowledgeIntegrationValidation()
        self._health_tracker = KnowledgeIntegrationHealth()
        self._status_tracker = KnowledgeIntegrationStatusTracker()
        self._history        = KnowledgeIntegrationHistory()
        self._response_registry = KnowledgeIntegrationRegistry()
        self._manager:       Optional[KnowledgeIntegrationManager] = None

    # ----------------------------------------------------------------
    # Lifecycle
    # ----------------------------------------------------------------

    def initialize(self) -> None:
        """
        Initialize the integration engine without starting it.

        Creates the component registry (discovers M1–M5 components).
        Idempotent — safe to call multiple times.
        """
        with self._lock:
            if self._state not in (IntegrationState.STOPPED, IntegrationState.ERROR):
                return
            self._state = IntegrationState.INITIALIZING
            self._status_tracker.set_state(IntegrationState.INITIALIZING)
            self._health_tracker.update_state(IntegrationState.INITIALIZING)

        try:
            if self._registry is None:
                self._registry = self._factory.create_registry()
            self._manager = KnowledgeIntegrationManager(
                registry  = self._registry,
                stats     = self._stats,
                event_bus = self._event_bus,
                validator = self._validator,
            )
            with self._lock:
                self._state = IntegrationState.STOPPED
                self._status_tracker.set_state(IntegrationState.STOPPED)
                self._health_tracker.update_state(IntegrationState.STOPPED)
            _log.info(f"Integration engine initialized: version={VERSION!r}")
        except Exception as exc:
            with self._lock:
                self._state = IntegrationState.ERROR
                self._status_tracker.set_state(IntegrationState.ERROR)
                self._health_tracker.update_state(IntegrationState.ERROR)
            _log.warning(f"Integration engine init error: {exc!r}")
            raise

    def start(self) -> None:
        """
        Start the integration engine.  Calls initialize() if not done yet.
        """
        with self._lock:
            if self._state == IntegrationState.RUNNING:
                return
            if self._state not in (
                IntegrationState.STOPPED, IntegrationState.ERROR,
                IntegrationState.INITIALIZING,
            ):
                raise IntegrationStateError(
                    f"Cannot start from state {self._state.value!r}",
                    current_state=self._state.value,
                )

        if self._manager is None:
            self.initialize()

        with self._lock:
            self._state = IntegrationState.STARTING
            self._status_tracker.set_state(IntegrationState.STARTING)

        with self._lock:
            self._state = IntegrationState.RUNNING
            self._status_tracker.set_state(IntegrationState.RUNNING)
            self._health_tracker.update_state(IntegrationState.RUNNING)

        self._event_bus.emit(
            IntegrationEventType.INTEGRATION_STARTED,
            payload={"version": VERSION},
        )
        _log.info(f"Integration engine started: system_id={SYSTEM_ID!r}")

    def stop(self) -> None:
        """Stop the integration engine gracefully."""
        with self._lock:
            if self._state == IntegrationState.STOPPED:
                return
            self._state = IntegrationState.STOPPING
            self._status_tracker.set_state(IntegrationState.STOPPING)

        self._event_bus.emit(
            IntegrationEventType.INTEGRATION_STOPPED,
            payload={"reason": "stop()"},
        )

        with self._lock:
            self._state = IntegrationState.STOPPED
            self._status_tracker.set_state(IntegrationState.STOPPED)
            self._health_tracker.update_state(IntegrationState.STOPPED)

        _log.info(f"Integration engine stopped: system_id={SYSTEM_ID!r}")

    def restart(self) -> None:
        """Restart the integration engine."""
        with self._lock:
            self._state = IntegrationState.RESTARTING
            self._status_tracker.set_state(IntegrationState.RESTARTING)
        self.stop()
        self._registry = None
        self._manager  = None
        self.initialize()
        self.start()
        _log.info(f"Integration engine restarted: system_id={SYSTEM_ID!r}")

    # ----------------------------------------------------------------
    # Observability
    # ----------------------------------------------------------------

    def health(self) -> KnowledgeHealthSummary:
        """Return the current health of the integration engine and components."""
        registry = self._registry
        checks   = registry.health_checks() if registry else []
        return self._health_tracker.check(checks)

    def status(self) -> KnowledgeIntegrationStatus:
        """Return the current operational status."""
        return self._status_tracker.get()

    def statistics(self) -> KnowledgeStatistics:
        """Return the current integration statistics."""
        return self._stats.report()

    def snapshot(self) -> KnowledgeIntegrationSnapshot:
        """
        Return a point-in-time operational snapshot of the integration engine.

        Note: this is the engine's own state snapshot, not a M5 KnowledgeSnapshot.
        """
        status  = self._status_tracker.get()
        stats   = self._stats.report()
        health  = self.health()
        recent  = [r.to_dict() for r in self._history.recent(10)]
        return KnowledgeIntegrationSnapshot.capture(
            integration_state = status.state,
            statistics        = stats.to_dict(),
            health            = health.to_dict(),
            recent_responses  = recent,
            uptime_seconds    = status.uptime_seconds,
        )

    def history(self, n: int = 20) -> List[KnowledgeIntegrationResponse]:
        """Return the N most recent integration responses."""
        return self._history.recent(n)

    def validate(self, request: KnowledgeIntegrationRequest) -> IntegrationValidationReport:
        """
        Validate an integration request without executing it.
        """
        available = self._registry.available_names() if self._registry else []
        return self._validator.validate(request, available)

    # ----------------------------------------------------------------
    # Public API
    # ----------------------------------------------------------------

    def submit(self, request: KnowledgeIntegrationRequest) -> KnowledgeIntegrationResponse:
        """
        Submit an integration request for full 9-phase workflow execution.
        """
        self._require_running()
        assert self._manager is not None
        self._status_tracker.record_request(request.request_id)
        response = self._manager.execute(request)
        self._history.record(response)
        self._response_registry.register(response)
        if response.snapshot_id:
            self._status_tracker.record_snapshot(response.snapshot_id)
        return response

    def query(
        self,
        session_id:    str,
        workflow_id:   str,
        enterprise_id: str,
        query_text:    str,
        *,
        timeout_ms: int = 30_000,
    ) -> KnowledgeIntegrationResponse:
        """
        Submit a query request against the knowledge base.
        """
        request = KnowledgeIntegrationRequest.create(
            session_id    = session_id,
            workflow_id   = workflow_id,
            enterprise_id = enterprise_id,
            request_type  = IntegrationRequestType.QUERY,
            query_text    = query_text,
            timeout_ms    = timeout_ms,
        )
        return self.submit(request)

    def search(
        self,
        session_id:    str,
        workflow_id:   str,
        enterprise_id: str,
        query_text:    str,
        *,
        filters:    Optional[Dict[str, Any]] = None,
        timeout_ms: int = 30_000,
    ) -> KnowledgeIntegrationResponse:
        """
        Submit a search request against the knowledge base.
        """
        request = KnowledgeIntegrationRequest.create(
            session_id    = session_id,
            workflow_id   = workflow_id,
            enterprise_id = enterprise_id,
            request_type  = IntegrationRequestType.SEARCH,
            query_text    = query_text,
            search_filters = filters or {},
            timeout_ms    = timeout_ms,
        )
        return self.submit(request)

    def retrieve(
        self,
        session_id:    str,
        workflow_id:   str,
        enterprise_id: str,
        knowledge_id:  str,
        *,
        timeout_ms: int = 30_000,
    ) -> KnowledgeIntegrationResponse:
        """
        Retrieve a specific knowledge artifact by ID.
        """
        request = KnowledgeIntegrationRequest.create(
            session_id    = session_id,
            workflow_id   = workflow_id,
            enterprise_id = enterprise_id,
            request_type  = IntegrationRequestType.RETRIEVE,
            retrieve_id   = knowledge_id,
            timeout_ms    = timeout_ms,
        )
        return self.submit(request)

    # ----------------------------------------------------------------
    # Event listener registration
    # ----------------------------------------------------------------

    def add_listener(
        self, listener: Any
    ) -> None:
        self._event_bus.add_listener(listener)

    def remove_listener(
        self, listener: Any
    ) -> None:
        self._event_bus.remove_listener(listener)

    # ----------------------------------------------------------------
    # Internal helpers
    # ----------------------------------------------------------------

    def _require_running(self) -> None:
        with self._lock:
            state = self._state
        if state != IntegrationState.RUNNING:
            raise IntegrationStateError(
                f"Engine must be RUNNING (current: {state.value!r})",
                current_state=state.value,
            )
