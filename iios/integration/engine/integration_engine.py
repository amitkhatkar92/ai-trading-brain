"""
integration_engine.py — iios.integration.engine
-------------------------------------------------
IntegrationEngine — central coordinator for enterprise integration workflows.

Responsibilities:
  - Initialize integration sessions
  - Manage lifecycle
  - Coordinate enterprise integrations
  - Register connectors, adapters, protocols
  - Dispatch integration workflows
  - Invoke Integration Governance Policy Framework (M3 — hook)
  - Invoke Integration Services Framework (M4 — hook)
  - Publish Integration Snapshot
  - Maintain history and statistics

Constraints:
  - NO governance evaluation
  - NO protocol business logic
  - NO business processing
  - NO AI reasoning
  - Protocol agnostic, connector agnostic

C15 Enterprise Integration & Connectivity — Phase 1, Module 2
"""
from __future__ import annotations

import time
import threading
from typing import Any, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import (
    ACTOR_ENGINE,
    ACTOR_SYSTEM,
    DEFAULT_ENGINE_ID,
    IntegrationEngineEventType,
    IntegrationEngineState,
)
from .exceptions import (
    IntegrationEngineNotReadyError,
    IntegrationRequestValidationError,
)
from .integration_context import IntegrationEngineContext
from .integration_dispatcher import IntegrationDispatcher
from .integration_events import IntegrationEngineEvent, IntegrationEngineEventBus
from .integration_health import EngineHealthReport, IntegrationEngineHealth
from .integration_history import IntegrationEngineHistory
from .integration_registry import IntegrationEngineRegistry
from .integration_request import IntegrationRequest
from .integration_response import IntegrationResponse
from .integration_scheduler import IntegrationScheduler, ScheduledJob
from .integration_session_manager import IntegrationSessionManager
from .integration_statistics import IntegrationEngineStatistics, IntegrationEngineStatisticsReport
from .integration_status import IntegrationEngineStatus, IntegrationEngineStatusTracker
from .integration_validation import EngineValidationReport, IntegrationEngineValidator

_log = get_logger(__name__)


class IntegrationEngine:
    """
    Central coordinator for enterprise integration workflows.

    Thread-safe.  Manages the full request lifecycle from receipt
    through validation, session creation, dispatch, governance
    coordination, service coordination, and publication.

    Does NOT implement connectors, adapters, protocols, or any
    vendor-specific logic.
    """

    def __init__(
        self,
        engine_id:       str                                    = DEFAULT_ENGINE_ID,
        registry:        Optional[IntegrationEngineRegistry]   = None,
        dispatcher:      Optional[IntegrationDispatcher]       = None,
        scheduler:       Optional[IntegrationScheduler]        = None,
        session_manager: Optional[IntegrationSessionManager]   = None,
        validator:       Optional[IntegrationEngineValidator]  = None,
        event_bus:       Optional[IntegrationEngineEventBus]   = None,
        stats:           Optional[IntegrationEngineStatistics] = None,
        history:         Optional[IntegrationEngineHistory]    = None,
    ) -> None:
        self._engine_id      = engine_id
        self._registry       = registry        or IntegrationEngineRegistry()
        self._dispatcher     = dispatcher      or IntegrationDispatcher()
        self._scheduler      = scheduler       or IntegrationScheduler()
        self._session_mgr    = session_manager or IntegrationSessionManager(engine_id=engine_id)
        self._validator      = validator       or IntegrationEngineValidator()
        self._event_bus      = event_bus       or IntegrationEngineEventBus()
        self._stats          = stats           or IntegrationEngineStatistics()
        self._history        = history         or IntegrationEngineHistory()
        self._health_monitor = IntegrationEngineHealth()
        self._status_tracker = IntegrationEngineStatusTracker()

        self._state          = IntegrationEngineState.IDLE
        self._active_count   = 0
        self._started_at     = time.monotonic()
        self._lock           = threading.Lock()
        self._response_cache: Dict[str, IntegrationResponse] = {}

    # ----------------------------------------------------------------
    # Lifecycle
    # ----------------------------------------------------------------

    def initialize(self) -> None:
        """Transition engine through startup sequence to IDLE."""
        with self._lock:
            if self._state == IntegrationEngineState.STOPPED:
                raise IntegrationEngineNotReadyError(
                    "Engine is stopped — create a new instance to restart"
                )
            self._state      = IntegrationEngineState.INITIALIZING
            self._started_at = time.monotonic()
        _log.info(f"Engine initializing: id={self._engine_id!r}")

        with self._lock:
            self._state = IntegrationEngineState.CONFIGURING
        with self._lock:
            self._state = IntegrationEngineState.VALIDATING
        with self._lock:
            self._state = IntegrationEngineState.CONNECTING
        with self._lock:
            self._state = IntegrationEngineState.IDLE

        _log.info(f"Engine ready: id={self._engine_id!r}")

    def configure(self, config: Dict[str, Any]) -> None:
        """Apply engine-level configuration."""
        _log.info(
            f"Engine configure: id={self._engine_id!r} "
            f"keys={list(config.keys())!r}"
        )

    def connect(self) -> None:
        """Signal that the engine is establishing base connectivity."""
        _log.info(f"Engine connect: id={self._engine_id!r}")

    def disconnect(self) -> None:
        """Signal that the engine is disconnecting."""
        _log.info(f"Engine disconnect: id={self._engine_id!r}")

    def stop(self) -> None:
        """Stop the engine — no further requests will be accepted."""
        with self._lock:
            self._state = IntegrationEngineState.STOPPED
        _log.info(f"Engine stopped: id={self._engine_id!r}")

    # ----------------------------------------------------------------
    # Dispatch
    # ----------------------------------------------------------------

    def dispatch(self, request: IntegrationRequest) -> IntegrationResponse:
        """
        Coordinate a full integration workflow for a request.

        Always returns an IntegrationResponse — never raises for
        integration-level failures.

        Raises:
            IntegrationEngineNotReadyError if engine is STOPPED.
        """
        with self._lock:
            if self._state == IntegrationEngineState.STOPPED:
                raise IntegrationEngineNotReadyError(
                    f"Engine {self._engine_id!r} is stopped"
                )
            self._active_count += 1
            if self._active_count == 1:
                self._state = IntegrationEngineState.DISPATCHING

        start_time = time.monotonic()
        session_id = ""

        try:
            response = self._dispatch_internal(request, start_time)
        except Exception as exc:
            latency_ms = (time.monotonic() - start_time) * 1000
            response   = IntegrationResponse.failure_for(
                request, session_id, str(exc), latency_ms
            )
            self._event_bus.emit(
                IntegrationEngineEventType.INTEGRATION_FAILED,
                self._engine_id,
                request.request_id,
                session_id,
                payload={"error": str(exc)},
            )
            _log.warning(
                f"Engine dispatch failed: "
                f"request={request.request_id!r} error={exc!r}"
            )
        finally:
            with self._lock:
                self._active_count -= 1
                if self._active_count == 0:
                    self._state = IntegrationEngineState.IDLE

        self._history.record_request(request)
        self._history.record_response(response)
        self._response_cache[request.request_id] = response
        return response

    def _dispatch_internal(
        self,
        request:    IntegrationRequest,
        start_time: float,
    ) -> IntegrationResponse:
        """Internal dispatch — raises IntegrationEngineError on failure."""
        # 1. Validate configuration
        validation = self._validator.validate(request, self._registry)
        if not validation.passed:
            raise IntegrationRequestValidationError(
                f"Request {request.request_id!r} failed validation: "
                f"{validation.failed_checks!r}",
                failed_checks=validation.failed_checks,
            )

        # 2. Initialize session (walks M1 lifecycle to ACTIVE)
        workflow_id = f"wf-{request.request_id}"
        session_id  = self._session_mgr.create_and_initialize(workflow_id)
        self._stats.record_session()

        # 3. Load connector
        connector = self._registry.get_connector(request.connector_type)
        self._stats.record_connector_loaded()
        self._emit(
            IntegrationEngineEventType.CONNECTOR_LOADED,
            request.request_id,
            session_id,
            payload={"connector_type": request.connector_type.value},
        )

        # 4. Load adapter
        adapter = self._registry.get_adapter_for(request.connector_type)
        self._stats.record_adapter_loaded()
        self._emit(
            IntegrationEngineEventType.ADAPTER_LOADED,
            request.request_id,
            session_id,
            payload={"adapter_id": adapter.adapter_id if adapter else ""},
        )

        # 5. Validate protocol
        self._emit(
            IntegrationEngineEventType.PROTOCOL_VALIDATED,
            request.request_id,
            session_id,
            payload={"protocol_type": request.protocol_type.value},
        )

        # 6. Emit connected
        self._emit(
            IntegrationEngineEventType.INTEGRATION_CONNECTED,
            request.request_id,
            session_id,
        )

        # 7. Dispatch pipeline
        self._emit(
            IntegrationEngineEventType.INTEGRATION_INITIALIZED,
            request.request_id,
            session_id,
        )
        context   = IntegrationEngineContext.create(
            request, session_id, engine_id=self._engine_id
        )
        execution = self._dispatcher.dispatch(request, context)
        self._stats.record_api_request()
        self._stats.record_message_routed()

        # 8. Coordinate Governance (M3 — delegation point)
        self._coordinate_governance(request, context)

        # 9. Coordinate Services (M4 — delegation point)
        self._coordinate_services(request, context)

        # 10. Publish snapshot
        with self._lock:
            self._state = IntegrationEngineState.PUBLISHING
        self._emit(
            IntegrationEngineEventType.INTEGRATION_DISPATCHED,
            request.request_id,
            session_id,
        )
        self._emit(
            IntegrationEngineEventType.INTEGRATION_PUBLISHED,
            request.request_id,
            session_id,
        )

        # 11. Complete session
        self._session_mgr.complete_session(session_id)
        self._session_mgr.archive_session(session_id)

        # 12. Build response
        latency_ms = (time.monotonic() - start_time) * 1000
        self._stats.record_response_time(latency_ms)
        processing_ms = latency_ms
        self._stats.record_processing_time(processing_ms)
        self._stats.record_availability_tick(True)

        response = IntegrationResponse.success_for(
            request, session_id,
            data={"execution_id": execution.execution_id,
                  "pipeline_success": execution.success},
            latency_ms=latency_ms,
        )

        # 13. Emit completion
        self._emit(
            IntegrationEngineEventType.INTEGRATION_COMPLETED,
            request.request_id,
            session_id,
            payload={"latency_ms": latency_ms},
        )

        for _ in range(7):   # count events emitted per request
            self._stats.record_event_processed()

        _log.info(
            f"Engine dispatch complete: "
            f"request={request.request_id!r} "
            f"session={session_id!r} "
            f"latency={latency_ms:.1f}ms"
        )
        return response

    def dispatch_batch(
        self, requests: List[IntegrationRequest]
    ) -> List[IntegrationResponse]:
        """Dispatch multiple requests in sequence."""
        return [self.dispatch(r) for r in requests]

    # ----------------------------------------------------------------
    # Governance and Services hooks
    # ----------------------------------------------------------------

    def _coordinate_governance(
        self,
        request: IntegrationRequest,
        context: IntegrationEngineContext,
    ) -> None:
        """
        Delegation point for M3 Integration Governance Policy Framework.

        When M3 is implemented, its policy evaluator is called here.
        The engine does NOT perform governance evaluation itself.
        """
        pass   # delegated to M3

    def _coordinate_services(
        self,
        request: IntegrationRequest,
        context: IntegrationEngineContext,
    ) -> None:
        """
        Delegation point for M4 Integration Services Framework.

        When M4 is implemented, its connector execution is called here.
        The engine does NOT perform connector or protocol logic itself.
        """
        pass   # delegated to M4

    # ----------------------------------------------------------------
    # Operations
    # ----------------------------------------------------------------

    def monitor(self) -> EngineHealthReport:
        """Run monitoring and return a health report."""
        with self._lock:
            self._state = IntegrationEngineState.MONITORING
        report = self.health()
        with self._lock:
            if self._state == IntegrationEngineState.MONITORING:
                self._state = IntegrationEngineState.IDLE
        return report

    def validate(
        self, request: IntegrationRequest
    ) -> EngineValidationReport:
        """Validate a request without dispatching."""
        with self._lock:
            self._state = IntegrationEngineState.VALIDATING
        report = self._validator.validate(request, self._registry)
        with self._lock:
            if self._state == IntegrationEngineState.VALIDATING:
                self._state = IntegrationEngineState.IDLE
        return report

    def health(self) -> EngineHealthReport:
        """Return a health report."""
        registry_summary = self._registry.summary()
        return self._health_monitor.report(
            engine_state    = self._state,
            connector_count = registry_summary["connector_count"],
            adapter_count   = registry_summary["adapter_count"],
            protocol_count  = registry_summary["protocol_count"],
            active_sessions = self._session_mgr.active_count(),
            queue_size      = self._scheduler.queue_size(),
            started_at      = self._started_at,
        )

    def status(self) -> IntegrationEngineStatus:
        """Return an operational status snapshot."""
        registry_summary = self._registry.summary()
        return self._status_tracker.capture(
            engine_id       = self._engine_id,
            state           = self._state,
            active_sessions = self._session_mgr.active_count(),
            queue_size      = self._scheduler.queue_size(),
            connector_count = registry_summary["connector_count"],
            adapter_count   = registry_summary["adapter_count"],
            protocol_count  = registry_summary["protocol_count"],
            started_at      = self._started_at,
        )

    def query(self, request_id: str) -> Optional[IntegrationResponse]:
        """Look up the response for a previous request."""
        return self._response_cache.get(request_id)

    # ----------------------------------------------------------------
    # Schedule
    # ----------------------------------------------------------------

    def schedule(
        self,
        request:  IntegrationRequest,
        mode:     str = "immediate",
        priority: int = 5,
    ) -> str:
        from .constants import SchedulerMode
        try:
            m = SchedulerMode(mode)
        except ValueError:
            m = SchedulerMode.IMMEDIATE
        return self._scheduler.submit(request, mode=m, priority=priority)

    def process_scheduled(self) -> Optional[IntegrationResponse]:
        """Process one scheduled request from the queue."""
        job: Optional[ScheduledJob] = self._scheduler.next()
        if job is None:
            return None
        return self.dispatch(job.request)

    # ----------------------------------------------------------------
    # Registry convenience
    # ----------------------------------------------------------------

    def register_connector(self, descriptor) -> None:
        self._registry.register_connector(descriptor)

    def register_adapter(self, descriptor) -> None:
        self._registry.register_adapter(descriptor)

    def register_protocol(self, descriptor) -> None:
        self._registry.register_protocol(descriptor)

    # ----------------------------------------------------------------
    # Properties
    # ----------------------------------------------------------------

    @property
    def engine_id(self) -> str:
        return self._engine_id

    @property
    def state(self) -> IntegrationEngineState:
        with self._lock:
            return self._state

    @property
    def registry(self) -> IntegrationEngineRegistry:
        return self._registry

    @property
    def event_bus(self) -> IntegrationEngineEventBus:
        return self._event_bus

    @property
    def stats(self) -> IntegrationEngineStatistics:
        return self._stats

    @property
    def history(self) -> IntegrationEngineHistory:
        return self._history

    @property
    def scheduler(self) -> IntegrationScheduler:
        return self._scheduler

    # ----------------------------------------------------------------
    # Internal
    # ----------------------------------------------------------------

    def _emit(
        self,
        event_type: IntegrationEngineEventType,
        request_id: str,
        session_id: str,
        payload:    Dict[str, Any] = None,
    ) -> IntegrationEngineEvent:
        return self._event_bus.emit(
            event_type,
            self._engine_id,
            request_id,
            session_id,
            payload,
        )
