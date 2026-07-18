"""
iios/execution/analytics/engine/analytics_manager.py
====================================================
AnalyticsManager — coordinates the complete analytics workflow for the
Execution Analytics Engine.

Responsibilities:
  - Orchestrate the full analytics workflow per request.
  - Validate requests and contexts.
  - Coordinate with M1 AnalyticsSessionManager for session lifecycle.
  - Coordinate with AnalyticsDispatcher for pipeline dispatch.
  - Publish AnalyticsSnapshot after successful dispatch.
  - Maintain statistics and history.
  - Emit domain events to registered listeners.

DOES NOT:
  - Perform performance calculations.
  - Execute predictive models.
  - Generate reports.
  - Execute trades.

C8 Execution Analytics & Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import threading
import time
from typing import Any, Callable, Dict, List, Optional

from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import (
    ACTOR_ENGINE,
    ACTOR_SYSTEM,
    ENGINE_SYSTEM_ID,
    MANAGER_SYSTEM_ID,
    VERSION,
    AnalyticsRequestType,
    EngineAnalyticsState,
    EngineEventType,
    ResponseStatus,
)
from .exceptions import (
    AnalyticsDispatchError,
    AnalyticsEngineNotRunningError,
    AnalyticsRequestNotFoundError,
    AnalyticsRequestValidationError,
    AnalyticsSessionManagerError,
)
from .analytics_context import EngineAnalyticsContext, make_engine_analytics_context
from .analytics_dispatcher import AnalyticsDispatcher
from .analytics_events import (
    EngineAnalyticsEvent,
    make_analytics_engine_collected,
    make_analytics_engine_completed,
    make_analytics_engine_dispatched,
    make_analytics_engine_failed,
    make_analytics_engine_initialized,
    make_analytics_engine_published,
    make_analytics_engine_started,
)
from .analytics_factory import EngineAnalyticsFactory
from .analytics_history import EngineAnalyticsHistory
from .analytics_pipeline import AnalyticsPipeline, make_analytics_pipeline
from .analytics_registry import EngineAnalyticsRegistry
from .analytics_request import AnalyticsRequest
from .analytics_response import (
    AnalyticsResponse,
    AnalyticsSnapshot,
    make_analytics_response,
    make_analytics_snapshot,
)
from .analytics_scheduler import AnalyticsScheduler
from .analytics_session_manager import AnalyticsSessionManager
from .analytics_statistics import EngineAnalyticsStatistics
from .analytics_validation import EngineAnalyticsValidator

_log   = get_logger(__name__)
_audit = get_audit_logger(__name__, engine_id=ENGINE_SYSTEM_ID)

_RUNNING = frozenset({EngineState.RUNNING, "running"})


class AnalyticsManager(LifecycleAwareMixin):
    """
    Core workflow coordinator for the Execution Analytics Engine.

    Owns all sub-components and implements the analytics workflow:
      1. Validate request
      2. Register request
      3. Initialize analytics session (M1)
      4. Collect execution data
      5. Validate context
      6. Dispatch analytics pipeline (M3/M4)
      7. Publish analytics snapshot
      8. Complete session
      9. Record statistics and history
      10. Emit domain event

    Thread-safe.  Must be started before use.
    """

    def __init__(
        self,
        max_sessions:    int = 5_000,
        max_requests:    int = 10_000,
        max_history:     int = 2_000,
        scheduler_queue: int = 1_000,
    ) -> None:
        super().__init__()
        self._session_manager = AnalyticsSessionManager(max_sessions=max_sessions)
        self._dispatcher      = AnalyticsDispatcher()
        self._scheduler       = AnalyticsScheduler(max_queue=scheduler_queue)
        self._registry        = EngineAnalyticsRegistry(max_requests=max_requests)
        self._factory         = EngineAnalyticsFactory()
        self._validator       = EngineAnalyticsValidator()
        self._stats           = EngineAnalyticsStatistics()
        self._history         = EngineAnalyticsHistory(
            max_requests  = max_history,
            max_responses = max_history,
            max_pipelines = max_history,
            max_events    = max_history * 10,
        )
        self._listeners:      List[Callable[[EngineAnalyticsEvent], None]] = []
        self._listeners_lock  = threading.Lock()
        self._started_at:     Optional[float] = None
        self._last_success_at: Optional[float] = None

    # ── LifecycleAwareMixin hooks ──────────────────────────────────────────────

    def _on_start(self) -> None:
        self._session_manager.start()
        self._dispatcher.start()
        self._scheduler.start()
        self._registry.start()
        self._factory.start()
        self._started_at = time.time()
        _audit.log_lifecycle_event(
            ENGINE_SYSTEM_ID, EngineState.STOPPED, EngineState.RUNNING, VERSION
        )
        _log.info("AnalyticsManager started.", system_id=MANAGER_SYSTEM_ID, version=VERSION)

    def _on_stop(self) -> None:
        self._session_manager.stop()
        self._dispatcher.stop()
        self._scheduler.stop()
        self._registry.stop()
        self._factory.stop()
        _audit.log_lifecycle_event(
            ENGINE_SYSTEM_ID, EngineState.RUNNING, EngineState.STOPPED, VERSION
        )
        _log.info("AnalyticsManager stopped.", system_id=MANAGER_SYSTEM_ID)

    def _assert_running(self) -> None:
        if self.lifecycle_state() not in _RUNNING:
            raise AnalyticsEngineNotRunningError()

    # ── Primary workflow ──────────────────────────────────────────────────────

    def process(
        self,
        request: AnalyticsRequest,
        context: Optional[EngineAnalyticsContext] = None,
    ) -> AnalyticsResponse:
        """
        Execute a complete analytics workflow cycle for the given request.

        1. Validate request
        2. Store in registry
        3. Build context (if not supplied)
        4. Validate context
        5. Create analytics session (M1)
        6. Advance session: INITIALIZING → COLLECTING → ANALYZING → READY → ACTIVE
        7. Create and dispatch pipeline (→ M3/M4)
        8. Publish analytics snapshot
        9. Complete session (COMPLETED → ARCHIVED)
        10. Record stats + history
        11. Emit COMPLETED event

        Returns AnalyticsResponse with status SUCCESS on success, FAILED on error.
        """
        self._assert_running()
        start_time = time.time()

        # ── Step 1: Validate request ──────────────────────────────────────────
        validation = self._validator.validate_request(request)
        if not validation.is_valid:
            self._stats.record_received()
            self._stats.record_rejected()
            return self._make_rejected_response(
                request.request_id,
                errors=list(validation.errors),
            )

        self._stats.record_received()
        self._history.record_request(request)

        # ── Step 2: Register request ──────────────────────────────────────────
        self._registry.store(request)

        # ── Step 3: Build context ─────────────────────────────────────────────
        if context is None:
            context = make_engine_analytics_context(
                request.request_id,
                request.execution_session_id,
                requester = request.requester,
                priority  = request.priority,
            )

        # ── Step 4: Validate context ──────────────────────────────────────────
        ctx_validation = self._validator.validate_context(context)
        if not ctx_validation.is_valid:
            self._registry.fail(request.request_id)
            self._stats.record_failed()
            return self._make_failed_response(
                request.request_id,
                error_message="Context validation failed: " + "; ".join(ctx_validation.errors),
                start_time=start_time,
            )

        session_id:  str = ""
        pipeline_id: str = ""

        try:
            # ── Step 5: Create analytics session ─────────────────────────────
            session = self._session_manager.create_session(
                request.request_id,
                request.execution_session_id,
                actor = ACTOR_ENGINE,
            )
            session_id = session.session_id
            self._emit(make_analytics_engine_initialized(request.request_id))

            # ── Step 6: Advance session through workflow states ───────────────
            collect_start = time.time()
            self._session_manager.initialize_session(request.request_id, actor=ACTOR_ENGINE)
            self._emit(make_analytics_engine_started(request.request_id))

            self._session_manager.collect_session(request.request_id, actor=ACTOR_ENGINE)
            collect_ms = (time.time() - collect_start) * 1000.0
            self._emit(make_analytics_engine_collected(request.request_id))

            self._session_manager.analyze_session(request.request_id, actor=ACTOR_ENGINE)
            self._session_manager.ready_session(request.request_id, actor=ACTOR_ENGINE)
            self._session_manager.activate_session(request.request_id, actor=ACTOR_ENGINE)

            # ── Step 7: Create and dispatch pipeline ──────────────────────────
            dispatch_start = time.time()
            pipeline = make_analytics_pipeline(request.request_id, session_id)
            pipeline_id = pipeline.pipeline_id
            self._stats.record_pipeline_dispatched()
            self._dispatcher.dispatch(pipeline)
            dispatch_ms = (time.time() - dispatch_start) * 1000.0
            self._stats.record_pipeline_completed()
            self._history.record_pipeline(pipeline)
            self._emit(make_analytics_engine_dispatched(request.request_id))

            # ── Step 8: Publish analytics snapshot ───────────────────────────
            snapshot = make_analytics_snapshot(
                EngineAnalyticsState.PUBLISHING,
                request_id  = request.request_id,
                session_id  = session_id,
                pipeline_id = pipeline_id,
            )
            self._emit(make_analytics_engine_published(request.request_id))

            # ── Step 9: Complete session ──────────────────────────────────────
            self._session_manager.complete_session(request.request_id, actor=ACTOR_ENGINE)
            self._session_manager.remove_mapping(request.request_id)

            # ── Step 10: Record stats and registry ────────────────────────────
            processing_ms = (time.time() - start_time) * 1000.0
            self._stats.record_completed(
                processing_ms = processing_ms,
                collection_ms = collect_ms,
                dispatch_ms   = dispatch_ms,
            )
            self._registry.complete(request.request_id)
            self._last_success_at = time.time()

            # ── Step 11: Build and record response ────────────────────────────
            response = make_analytics_response(
                request.request_id,
                ResponseStatus.SUCCESS,
                session_id    = session_id,
                pipeline_id   = pipeline_id,
                snapshot      = snapshot,
                processing_ms = processing_ms,
                collection_ms = collect_ms,
                dispatch_ms   = dispatch_ms,
            )
            self._history.record_response(response)
            self._emit(make_analytics_engine_completed(request.request_id))

            _log.info(
                "Analytics workflow completed.",
                request_id    = request.request_id,
                session_id    = session_id,
                pipeline_id   = pipeline_id,
                processing_ms = round(processing_ms, 2),
            )
            return response

        except Exception as exc:
            # Fail the session if it was created
            if session_id:
                try:
                    self._session_manager.fail_session(
                        request.request_id, reason=str(exc), actor=ACTOR_ENGINE
                    )
                    self._session_manager.remove_mapping(request.request_id)
                except Exception:
                    pass
            # Fail the registry entry if it is still active
            try:
                if self._registry.find(request.request_id):
                    self._registry.fail(request.request_id)
            except Exception:
                pass
            if pipeline_id:
                self._stats.record_pipeline_failed()
            self._stats.record_failed()
            self._emit(make_analytics_engine_failed(request.request_id, reason=str(exc)))
            response = self._make_failed_response(
                request.request_id,
                error_message=str(exc),
                start_time=start_time,
                session_id=session_id,
                pipeline_id=pipeline_id,
            )
            self._history.record_response(response)
            _log.error(
                "Analytics workflow failed.",
                request_id = request.request_id,
                error      = str(exc),
            )
            return response

    # ── Framework registration ────────────────────────────────────────────────

    def register_performance_framework(self, framework: Any) -> None:
        """Register the M3 Performance Analytics Framework with the dispatcher."""
        self._dispatcher.register_performance_framework(framework)

    def register_predictive_framework(self, framework: Any) -> None:
        """Register the M4 Predictive Intelligence Framework with the dispatcher."""
        self._dispatcher.register_predictive_framework(framework)

    # ── Query ─────────────────────────────────────────────────────────────────

    def statistics(self) -> EngineAnalyticsStatistics:
        """Return an independent copy of current statistics."""
        return self._stats.copy()

    def history(self) -> EngineAnalyticsHistory:
        """Return a reference to the live history store."""
        return self._history

    def scheduler(self) -> AnalyticsScheduler:
        return self._scheduler

    def dispatcher(self) -> AnalyticsDispatcher:
        return self._dispatcher

    @property
    def uptime_seconds(self) -> float:
        if self._started_at is None:
            return 0.0
        return time.time() - self._started_at

    @property
    def last_success_at(self) -> Optional[float]:
        return self._last_success_at

    # ── Listeners ─────────────────────────────────────────────────────────────

    def add_listener(self, listener: Callable[[EngineAnalyticsEvent], None]) -> None:
        with self._listeners_lock:
            if listener not in self._listeners:
                self._listeners.append(listener)

    def remove_listener(self, listener: Callable[[EngineAnalyticsEvent], None]) -> None:
        with self._listeners_lock:
            try:
                self._listeners.remove(listener)
            except ValueError:
                pass

    # ── Private helpers ───────────────────────────────────────────────────────

    def _emit(self, event: EngineAnalyticsEvent) -> None:
        self._history.record_event(event)
        with self._listeners_lock:
            listeners = list(self._listeners)
        for listener in listeners:
            try:
                listener(event)
            except Exception as exc:
                _log.warning(
                    "Listener raised an exception; skipping.",
                    error = str(exc),
                )

    def _make_rejected_response(
        self,
        request_id: str,
        *,
        errors: List[str],
    ) -> AnalyticsResponse:
        return make_analytics_response(
            request_id,
            ResponseStatus.REJECTED,
            error_message = "Validation failed: " + "; ".join(errors),
        )

    def _make_failed_response(
        self,
        request_id:   str,
        *,
        error_message: str  = "",
        start_time:    float,
        session_id:    str  = "",
        pipeline_id:   str  = "",
    ) -> AnalyticsResponse:
        processing_ms = (time.time() - start_time) * 1000.0
        return make_analytics_response(
            request_id,
            ResponseStatus.FAILED,
            session_id    = session_id,
            pipeline_id   = pipeline_id,
            error_message = error_message,
            processing_ms = processing_ms,
        )
