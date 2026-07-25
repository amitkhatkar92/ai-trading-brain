"""
workflow_engine.py — iios.workflow.engine
------------------------------------------
WorkflowEngine — central coordinator for enterprise workflow execution.

Responsibilities:
  - Initialize workflow sessions (via M1 lifecycle)
  - Validate workflow requests
  - Schedule workflows
  - Queue workflows
  - Dispatch workflows through the pipeline
  - Coordinate Workflow Governance Policy Framework (M3 — hook)
  - Coordinate Workflow Orchestration Framework (M4 — hook)
  - Generate Workflow Snapshot
  - Maintain history and statistics

Constraints:
  - NO business processing
  - NO governance evaluation
  - NO task execution
  - NO AI reasoning
  - Delegates governance to M3
  - Delegates orchestration to M4

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 2
"""
from __future__ import annotations

import time
import threading
from typing import Any, Callable, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import (
    ACTOR_ENGINE,
    ACTOR_SYSTEM,
    DEFAULT_ENGINE_ID,
    WorkflowEngineEventType,
    WorkflowEngineState,
)
from .exceptions import (
    WorkflowEngineNotReadyError,
    WorkflowGovernanceError,
    WorkflowOrchestrationError,
    WorkflowRequestValidationError,
)
from .workflow_context import WorkflowEngineContext
from .workflow_dispatcher import WorkflowDispatcher
from .workflow_events import WorkflowEngineEvent, WorkflowEngineEventBus
from .workflow_factory import WorkflowEngineFactory
from .workflow_health import WorkflowEngineHealth, WorkflowEngineHealthReport
from .workflow_history import WorkflowEngineHistory
from .workflow_monitor import WorkflowMonitor
from .workflow_pipeline import PipelineExecution
from .workflow_registry import WorkflowEngineRegistry
from .workflow_request import WorkflowEngineRequest
from .workflow_response import WorkflowEngineResponse
from .workflow_scheduler import WorkflowScheduler
from .workflow_session_manager import WorkflowSessionManager
from .workflow_statistics import WorkflowEngineStatistics, WorkflowEngineStatisticsReport
from .workflow_status import WorkflowEngineStatus, WorkflowEngineStatusTracker
from .workflow_validation import WorkflowEngineValidationReport, WorkflowEngineValidator

_log = get_logger(__name__)

_GovernanceHook    = Callable[[WorkflowEngineRequest, WorkflowEngineContext], Optional[Dict[str, Any]]]
_OrchestrationHook = Callable[[WorkflowEngineRequest, WorkflowEngineContext], Optional[Dict[str, Any]]]


class WorkflowEngine:
    """
    Central coordinator for enterprise workflow execution.

    Thread-safe.  Manages the full request lifecycle from receipt
    through validation, session creation, scheduling, dispatch,
    governance coordination, orchestration coordination, and publication.

    Does NOT implement business logic, governance evaluation,
    task execution, or AI reasoning.
    """

    def __init__(
        self,
        engine_id:       str                                      = DEFAULT_ENGINE_ID,
        scheduler:       Optional[WorkflowScheduler]             = None,
        dispatcher:      Optional[WorkflowDispatcher]            = None,
        session_manager: Optional[WorkflowSessionManager]        = None,
        validator:       Optional[WorkflowEngineValidator]        = None,
        event_bus:       Optional[WorkflowEngineEventBus]         = None,
        stats:           Optional[WorkflowEngineStatistics]       = None,
        history:         Optional[WorkflowEngineHistory]          = None,
        registry:        Optional[WorkflowEngineRegistry]         = None,
        monitor:         Optional[WorkflowMonitor]                = None,
    ) -> None:
        self._engine_id      = engine_id
        self._scheduler      = scheduler       or WorkflowScheduler()
        self._dispatcher     = dispatcher      or WorkflowDispatcher()
        self._session_mgr    = session_manager or WorkflowSessionManager(engine_id=engine_id)
        self._validator      = validator       or WorkflowEngineValidator()
        self._event_bus      = event_bus       or WorkflowEngineEventBus()
        self._stats          = stats           or WorkflowEngineStatistics()
        self._history        = history         or WorkflowEngineHistory()
        self._registry       = registry        or WorkflowEngineRegistry()
        self._monitor        = monitor         or WorkflowMonitor()
        self._health_monitor = WorkflowEngineHealth()
        self._status_tracker = WorkflowEngineStatusTracker()
        self._factory        = WorkflowEngineFactory()

        # M3 and M4 hooks (None = passthrough, no-op)
        self._governance_hook:    Optional[_GovernanceHook]    = None
        self._orchestration_hook: Optional[_OrchestrationHook]= None

        self._state        = WorkflowEngineState.IDLE
        self._active_count = 0
        self._started_at   = time.monotonic()
        self._lock         = threading.Lock()

    # ----------------------------------------------------------------
    # Hook registration (M3 / M4 delegation)
    # ----------------------------------------------------------------

    def register_governance_hook(self, hook: _GovernanceHook) -> None:
        """Register the M3 Governance Policy Framework delegation hook."""
        self._governance_hook = hook

    def register_orchestration_hook(self, hook: _OrchestrationHook) -> None:
        """Register the M4 Orchestration Framework delegation hook."""
        self._orchestration_hook = hook

    # ----------------------------------------------------------------
    # Engine lifecycle
    # ----------------------------------------------------------------

    def initialize(self) -> None:
        """Transition engine through startup sequence to IDLE."""
        with self._lock:
            if self._state == WorkflowEngineState.STOPPED:
                raise WorkflowEngineNotReadyError(
                    "Engine is stopped — create a new instance to restart"
                )
            self._state      = WorkflowEngineState.INITIALIZING
            self._started_at = time.monotonic()
        _log.info(f"WorkflowEngine initializing: id={self._engine_id!r}")

        with self._lock:
            self._state = WorkflowEngineState.VALIDATING
        with self._lock:
            self._state = WorkflowEngineState.IDLE

        _log.info(f"WorkflowEngine ready: id={self._engine_id!r}")

    def stop(self) -> None:
        """Stop the engine — no further requests will be accepted."""
        with self._lock:
            self._state = WorkflowEngineState.STOPPED
        _log.info(f"WorkflowEngine stopped: id={self._engine_id!r}")

    # ----------------------------------------------------------------
    # Execute — primary public method
    # ----------------------------------------------------------------

    def execute(self, request: WorkflowEngineRequest) -> WorkflowEngineResponse:
        """
        Coordinate a full workflow execution for a request.

        Always returns a WorkflowEngineResponse — never raises for
        workflow-level failures.

        Raises:
            WorkflowEngineNotReadyError if engine is STOPPED.
        """
        with self._lock:
            if self._state == WorkflowEngineState.STOPPED:
                raise WorkflowEngineNotReadyError(
                    f"WorkflowEngine {self._engine_id!r} is stopped"
                )
            self._active_count += 1
            if self._active_count == 1:
                self._state = WorkflowEngineState.DISPATCHING

        start_time = time.monotonic()
        session_id = ""

        try:
            response = self._execute_internal(request, start_time)
        except Exception as exc:
            latency_ms = (time.monotonic() - start_time) * 1000
            response   = WorkflowEngineResponse.failure_for(
                request, session_id, str(exc), latency_ms=latency_ms
            )
            self._event_bus.emit(
                WorkflowEngineEventType.WORKFLOW_FAILED,
                self._engine_id,
                request.request_id,
                session_id,
                payload={"error": str(exc)},
            )
            self._stats.record_failed()
            _log.warning(
                f"Engine execute failed: "
                f"request={request.request_id!r} error={exc!r}"
            )
        finally:
            with self._lock:
                self._active_count -= 1
                if self._active_count == 0:
                    self._state = WorkflowEngineState.IDLE

        return response

    def _execute_internal(
        self,
        request:    WorkflowEngineRequest,
        start_time: float,
    ) -> WorkflowEngineResponse:
        """Internal execution — may raise; caller wraps in try/except."""
        session_id = ""

        # ── 1. Record request ──────────────────────────────────────
        self._history.record_request(request)
        self._stats.record_executed()

        # ── 2. Validate ────────────────────────────────────────────
        with self._lock:
            self._state = WorkflowEngineState.VALIDATING

        validation = self._validator.validate(request)
        if not validation.passed:
            self._event_bus.emit(
                WorkflowEngineEventType.WORKFLOW_FAILED,
                self._engine_id,
                request.request_id,
                "",
                payload={"failed_checks": validation.failed_checks},
            )
            latency_ms = (time.monotonic() - start_time) * 1000
            response = WorkflowEngineResponse.failure_for(
                request, "",
                f"Validation failed: {validation.failed_checks}",
                latency_ms=latency_ms,
            )
            self._stats.record_failed()
            self._history.record_response(response)
            return response

        self._event_bus.emit(
            WorkflowEngineEventType.WORKFLOW_VALIDATED,
            self._engine_id,
            request.request_id,
            "",
        )

        # ── 3. Create lifecycle session ────────────────────────────
        session_id = self._session_mgr.create_session(request.workflow_id)
        self._registry.register(request, session_id)
        context = WorkflowEngineContext.create(
            request, session_id, engine_id=self._engine_id
        )
        self._session_mgr.initialize_session(session_id)
        self._session_mgr.validate_session(session_id)
        self._session_mgr.mark_ready(session_id)

        self._event_bus.emit(
            WorkflowEngineEventType.WORKFLOW_INITIALIZED,
            self._engine_id,
            request.request_id,
            session_id,
        )

        # ── 4. Schedule ────────────────────────────────────────────
        with self._lock:
            self._state = WorkflowEngineState.SCHEDULING

        queue_start = time.monotonic()
        job = self._scheduler.schedule(request)

        self._event_bus.emit(
            WorkflowEngineEventType.WORKFLOW_QUEUED,
            self._engine_id,
            request.request_id,
            session_id,
            payload={"job_id": job.job_id},
        )

        # ── 5. Consume from scheduler and dispatch ─────────────────
        with self._lock:
            self._state = WorkflowEngineState.QUEUING

        _ = self._scheduler.next()   # consume the job we just scheduled
        queue_time_ms = (time.monotonic() - queue_start) * 1000
        self._stats.record_queue_time(queue_time_ms)

        with self._lock:
            self._state = WorkflowEngineState.DISPATCHING

        self._session_mgr.start_session(session_id)
        self._monitor.register(request.request_id, session_id, request.workflow_id)

        self._event_bus.emit(
            WorkflowEngineEventType.WORKFLOW_DISPATCHED,
            self._engine_id,
            request.request_id,
            session_id,
        )

        # ── 6. Pipeline execution ──────────────────────────────────
        dispatch_start = time.monotonic()
        self._event_bus.emit(
            WorkflowEngineEventType.WORKFLOW_STARTED,
            self._engine_id,
            request.request_id,
            session_id,
        )

        execution = self._dispatcher.dispatch(request, context)
        processing_time_ms = (time.monotonic() - dispatch_start) * 1000
        self._stats.record_processing_time(processing_time_ms)

        # ── 7. Monitor ─────────────────────────────────────────────
        with self._lock:
            self._state = WorkflowEngineState.MONITORING
        self._monitor.deregister(request.request_id)

        # ── 8. Build response ──────────────────────────────────────
        latency_ms = (time.monotonic() - start_time) * 1000
        runtime_ms = latency_ms

        if execution.success:
            self._session_mgr.complete_session(
                session_id,
                runtime_ms=runtime_ms,
                lifecycle_duration_ms=latency_ms,
            )
            self._stats.record_completed(runtime_ms=runtime_ms)
            self._event_bus.emit(
                WorkflowEngineEventType.WORKFLOW_COMPLETED,
                self._engine_id,
                request.request_id,
                session_id,
            )
            # ── 9. Publish ─────────────────────────────────────────
            with self._lock:
                self._state = WorkflowEngineState.PUBLISHING
            self._event_bus.emit(
                WorkflowEngineEventType.WORKFLOW_SNAPSHOT_PUBLISHED,
                self._engine_id,
                request.request_id,
                session_id,
            )
            response = WorkflowEngineResponse.success_for(
                request,
                session_id,
                data=execution.stage_results,
                latency_ms=latency_ms,
                queue_time_ms=queue_time_ms,
                processing_time_ms=processing_time_ms,
            )
        else:
            self._session_mgr.fail_session(
                session_id,
                reason=execution.error_message or "pipeline failure",
            )
            self._stats.record_failed()
            self._event_bus.emit(
                WorkflowEngineEventType.WORKFLOW_FAILED,
                self._engine_id,
                request.request_id,
                session_id,
                payload={"error": execution.error_message},
            )
            response = WorkflowEngineResponse.failure_for(
                request,
                session_id,
                execution.error_message or "pipeline failure",
                latency_ms=latency_ms,
                queue_time_ms=queue_time_ms,
                processing_time_ms=processing_time_ms,
            )

        self._registry.record_response(request.request_id, response)
        self._history.record_response(response)
        self._registry.deregister(request.request_id)
        return response

    # ----------------------------------------------------------------
    # Validate (standalone)
    # ----------------------------------------------------------------

    def validate(self, request: WorkflowEngineRequest) -> WorkflowEngineValidationReport:
        return self._validator.validate(request)

    # ----------------------------------------------------------------
    # Cancel
    # ----------------------------------------------------------------

    def cancel(
        self,
        request_id: str,
        *,
        reason: str = "cancelled by engine",
    ) -> bool:
        """
        Attempt to cancel an active workflow.

        Returns True if the session was found and cancel attempted.
        """
        session_id = self._registry.get_session_id(request_id)
        if session_id is None:
            return False
        self._session_mgr.cancel_session(session_id, reason=reason)
        self._monitor.deregister(request_id)
        self._registry.deregister(request_id)
        self._event_bus.emit(
            WorkflowEngineEventType.WORKFLOW_CANCELLED,
            self._engine_id,
            request_id,
            session_id,
            payload={"reason": reason},
        )
        return True

    # ----------------------------------------------------------------
    # Batch execution
    # ----------------------------------------------------------------

    def execute_batch(
        self,
        requests: List[WorkflowEngineRequest],
    ) -> List[WorkflowEngineResponse]:
        """Execute multiple requests independently."""
        return [self.execute(req) for req in requests]

    # ----------------------------------------------------------------
    # Observability
    # ----------------------------------------------------------------

    def health(self) -> WorkflowEngineHealthReport:
        with self._lock:
            state = self._state
        return self._health_monitor.report(
            engine_state    = state,
            active_requests = self._monitor.active_count(),
            queue_size      = self._scheduler.queue_size(),
            started_at      = self._started_at,
        )

    def status(self) -> WorkflowEngineStatus:
        with self._lock:
            state = self._state
        return self._status_tracker.capture(
            engine_id       = self._engine_id,
            state           = state,
            active_requests = self._monitor.active_count(),
            queue_size      = self._scheduler.queue_size(),
            sessions_active = self._session_mgr.active_count(),
            started_at      = self._started_at,
        )

    def statistics(self) -> WorkflowEngineStatisticsReport:
        return self._stats.report(
            current_queue_size=self._scheduler.queue_size()
        )

    def history(self) -> WorkflowEngineHistory:
        return self._history

    def event_bus(self) -> WorkflowEngineEventBus:
        return self._event_bus

    def scheduler(self) -> WorkflowScheduler:
        return self._scheduler

    def monitor(self) -> WorkflowMonitor:
        return self._monitor

    def registry(self) -> WorkflowEngineRegistry:
        return self._registry

    @property
    def engine_id(self) -> str:
        return self._engine_id

    @property
    def state(self) -> WorkflowEngineState:
        with self._lock:
            return self._state
