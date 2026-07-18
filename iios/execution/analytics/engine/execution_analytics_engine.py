"""
iios/execution/analytics/engine/execution_analytics_engine.py
=============================================================
ExecutionAnalyticsEngine — PRIMARY PUBLIC INTERFACE for the C8 Execution
Analytics Engine.

The Analytics Engine coordinates all analytics activities across the
Execution Intelligence subsystem.  It orchestrates analytics workflows,
analytics sessions, and analytics pipelines.

RESPONSIBILITIES:
  - Accept and validate AnalyticsRequest objects.
  - Run analytics workflows via AnalyticsManager.
  - Coordinate with M1 AnalyticsLifecycle for session management.
  - Dispatch analytics pipelines to Performance Analytics (M3) and
    Predictive Intelligence (M4) frameworks.
  - Publish AnalyticsSnapshot objects after each successful cycle.
  - Maintain EngineAnalyticsStatistics and EngineAnalyticsHistory.
  - Expose health and status endpoints.
  - Support scheduler-driven analytics.

DOES NOT:
  - Perform performance calculations.
  - Execute predictive models.
  - Generate reports or visualizations.
  - Execute trades.

C8 Execution Analytics & Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import threading
import time
from typing import Any, Callable, List, Optional

from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import (
    ACTOR_SYSTEM,
    ENGINE_SYSTEM_ID,
    VERSION,
    AnalyticsRequestType,
    EngineAnalyticsState,
    EngineHealthStatus,
    ScheduleType,
)
from .exceptions import AnalyticsEngineNotRunningError, AnalyticsRequestNotFoundError
from .analytics_context import EngineAnalyticsContext
from .analytics_events import EngineAnalyticsEvent
from .analytics_health import AnalyticsEngineHealth, assess_engine_health
from .analytics_history import EngineAnalyticsHistory
from .analytics_manager import AnalyticsManager
from .analytics_request import AnalyticsRequest, make_analytics_request
from .analytics_response import AnalyticsResponse, AnalyticsSnapshot
from .analytics_statistics import EngineAnalyticsStatistics
from .analytics_status import AnalyticsEngineStatus

_log   = get_logger(__name__)
_audit = get_audit_logger(__name__, engine_id=ENGINE_SYSTEM_ID)

_RUNNING = frozenset({EngineState.RUNNING, "running"})


class ExecutionAnalyticsEngine(LifecycleAwareMixin):
    """
    Primary public interface for the Execution Analytics Engine.

    Usage::

        engine = ExecutionAnalyticsEngine()
        engine.start()

        # Simple submission
        response = engine.submit("exec-session-001")
        assert response.is_success

        # Full request
        request = make_analytics_request("exec-session-002", priority=1)
        response = engine.process(request)

        engine.stop()

    Framework registration (once available)::

        engine.register_performance_framework(perf_m3)
        engine.register_predictive_framework(predict_m4)
    """

    def __init__(
        self,
        max_sessions:    int = 5_000,
        max_requests:    int = 10_000,
        max_history:     int = 2_000,
        scheduler_queue: int = 1_000,
    ) -> None:
        super().__init__()
        self._manager = AnalyticsManager(
            max_sessions    = max_sessions,
            max_requests    = max_requests,
            max_history     = max_history,
            scheduler_queue = scheduler_queue,
        )
        self._cycle_state = EngineAnalyticsState.IDLE
        self._cycle_lock  = threading.RLock()

    # ── LifecycleAwareMixin hooks ──────────────────────────────────────────────

    def _on_start(self) -> None:
        self._manager.start()
        _audit.log_lifecycle_event(
            ENGINE_SYSTEM_ID, EngineState.STOPPED, EngineState.RUNNING, VERSION
        )
        _log.info(
            "ExecutionAnalyticsEngine started.",
            system_id = ENGINE_SYSTEM_ID,
            version   = VERSION,
        )

    def _on_stop(self) -> None:
        self._manager.stop()
        with self._cycle_lock:
            self._cycle_state = EngineAnalyticsState.STOPPED
        _audit.log_lifecycle_event(
            ENGINE_SYSTEM_ID, EngineState.RUNNING, EngineState.STOPPED, VERSION
        )
        _log.info("ExecutionAnalyticsEngine stopped.", system_id=ENGINE_SYSTEM_ID)

    def _assert_running(self) -> None:
        if self.lifecycle_state() not in _RUNNING:
            raise AnalyticsEngineNotRunningError()

    # ── Initialize ────────────────────────────────────────────────────────────

    def initialize(self) -> None:
        """
        Perform engine initialization.

        Sets the cycle state to IDLE, confirming the engine is ready to
        accept analytics requests.
        """
        self._assert_running()
        with self._cycle_lock:
            self._cycle_state = EngineAnalyticsState.IDLE
        _log.info("ExecutionAnalyticsEngine initialized.")

    # ── Core analytics operations ─────────────────────────────────────────────

    def process(
        self,
        request: AnalyticsRequest,
        context: Optional[EngineAnalyticsContext] = None,
    ) -> AnalyticsResponse:
        """
        Execute a complete analytics workflow cycle for the given request.

        Steps (delegated to AnalyticsManager):
          1. Validate request
          2. Register request
          3. Initialize analytics session (M1)
          4. Collect execution data
          5. Dispatch analytics pipeline (M3/M4)
          6. Publish analytics snapshot
          7. Complete session

        Returns AnalyticsResponse.  Never raises on analytics errors — errors
        are captured in the response.
        """
        self._assert_running()
        with self._cycle_lock:
            self._cycle_state = EngineAnalyticsState.INITIALIZING
        try:
            response = self._manager.process(request, context)
            with self._cycle_lock:
                self._cycle_state = (
                    EngineAnalyticsState.COMPLETED
                    if response.is_success
                    else EngineAnalyticsState.FAILED
                )
            return response
        except Exception:
            with self._cycle_lock:
                self._cycle_state = EngineAnalyticsState.FAILED
            raise

    def process_with_context(
        self,
        request: AnalyticsRequest,
        context: EngineAnalyticsContext,
    ) -> AnalyticsResponse:
        """Process a request with an explicit analytics context."""
        return self.process(request, context)

    def submit(
        self,
        execution_session_id: str,
        *,
        priority:  int  = 5,
        requester: str  = ACTOR_SYSTEM,
        reason:    str  = "",
    ) -> AnalyticsResponse:
        """
        Convenience method: create an on-demand request and process it.

        Equivalent to::

            request = make_analytics_request(execution_session_id, ...)
            engine.process(request)
        """
        self._assert_running()
        request = make_analytics_request(
            execution_session_id,
            request_type = AnalyticsRequestType.ON_DEMAND,
            requester    = requester,
            priority     = priority,
            reason       = reason,
        )
        return self.process(request)

    # ── Collect ───────────────────────────────────────────────────────────────

    def collect(
        self,
        execution_session_id: str,
        monitoring_snapshot:  Optional[Any] = None,
        recovery_snapshot:    Optional[Any] = None,
        gateway_snapshot:     Optional[Any] = None,
        risk_snapshot:        Optional[Any] = None,
        execution_context:    Optional[Any] = None,
    ) -> EngineAnalyticsContext:
        """
        Collect execution data into an EngineAnalyticsContext.

        Use this when you want to pre-build a context before calling process().
        """
        from .analytics_context import make_engine_analytics_context
        self._assert_running()
        request = make_analytics_request(execution_session_id)
        return make_engine_analytics_context(
            request.request_id,
            execution_session_id,
            monitoring_snapshot = monitoring_snapshot,
            recovery_snapshot   = recovery_snapshot,
            gateway_snapshot    = gateway_snapshot,
            risk_snapshot       = risk_snapshot,
            execution_context   = execution_context,
        )

    # ── Validate ──────────────────────────────────────────────────────────────

    def validate(self, request: AnalyticsRequest) -> bool:
        """
        Validate an analytics request without executing it.

        Returns True if the request passes all validation rules.
        """
        self._assert_running()
        from .analytics_validation import EngineAnalyticsValidator
        validator = EngineAnalyticsValidator()
        result = validator.validate_request(request)
        return result.is_valid

    # ── Scheduler integration ─────────────────────────────────────────────────

    def schedule(
        self,
        execution_session_id: str,
        *,
        priority:    int   = 5,
        requester:   str   = ACTOR_SYSTEM,
        reason:      str   = "",
        schedule_at: Optional[float] = None,
    ) -> str:
        """Queue an on-demand request in the scheduler.  Returns request_id."""
        self._assert_running()
        request = make_analytics_request(
            execution_session_id,
            request_type = AnalyticsRequestType.ON_DEMAND,
            requester    = requester,
            priority     = priority,
            reason       = reason,
            scheduled_at = schedule_at,
        )
        return self._manager.scheduler().schedule(
            request,
            schedule_type = ScheduleType.ON_DEMAND,
            schedule_at   = schedule_at,
        )

    def schedule_periodic(
        self,
        execution_session_id: str,
        interval_s:           float,
        *,
        priority:  int = 7,
        requester: str = ACTOR_SYSTEM,
    ) -> str:
        """Queue a periodic analytics request.  Returns request_id."""
        self._assert_running()
        return self._manager.scheduler().schedule_periodic(
            execution_session_id,
            interval_s,
            priority  = priority,
            requester = requester,
        )

    def dequeue_and_process(self) -> Optional[AnalyticsResponse]:
        """
        Dequeue one due request from the scheduler and process it.

        Returns None if no request is due.
        """
        self._assert_running()
        request = self._manager.scheduler().dequeue()
        if request is None:
            return None
        return self.process(request)

    def dequeue_and_process_all(self) -> List[AnalyticsResponse]:
        """Dequeue all due requests and process them in priority order."""
        self._assert_running()
        requests = self._manager.scheduler().dequeue_all_due()
        return [self.process(r) for r in requests]

    # ── Publish ───────────────────────────────────────────────────────────────

    def publish(self, snapshot: AnalyticsSnapshot) -> None:
        """
        Publish an analytics snapshot.

        Publishing is handled automatically by process(); this method is
        provided for manual publishing when needed.
        """
        self._assert_running()
        _log.info(
            "Analytics snapshot published.",
            snapshot_id  = snapshot.snapshot_id,
            engine_state = snapshot.engine_state.value,
            request_id   = snapshot.request_id,
        )

    # ── Query ─────────────────────────────────────────────────────────────────

    def query(self, request_id: str) -> Optional[AnalyticsResponse]:
        """
        Query the history for the most recent response for a request.

        Returns None if no response is found for the given request_id.
        """
        self._assert_running()
        responses = self._manager.history().responses_for_request(request_id)
        return responses[-1] if responses else None

    # ── Framework registration ────────────────────────────────────────────────

    def register_performance_framework(self, framework: Any) -> None:
        """Register the M3 Performance Analytics Framework."""
        self._manager.register_performance_framework(framework)

    def register_predictive_framework(self, framework: Any) -> None:
        """Register the M4 Predictive Intelligence Framework."""
        self._manager.register_predictive_framework(framework)

    # ── Listeners ─────────────────────────────────────────────────────────────

    def add_listener(self, listener: Callable[[EngineAnalyticsEvent], None]) -> None:
        """Register an event listener."""
        self._manager.add_listener(listener)

    def remove_listener(self, listener: Callable[[EngineAnalyticsEvent], None]) -> None:
        """Deregister an event listener."""
        self._manager.remove_listener(listener)

    # ── Statistics / History / Health / Status ────────────────────────────────

    def statistics(self) -> EngineAnalyticsStatistics:
        """Return an independent snapshot copy of current engine statistics."""
        self._assert_running()
        return self._manager.statistics()

    def history(self) -> EngineAnalyticsHistory:
        """Return a live reference to the engine history store."""
        self._assert_running()
        return self._manager.history()

    def health(self) -> AnalyticsEngineHealth:
        """Return a point-in-time health assessment of the engine."""
        self._assert_running()
        sched  = self._manager.scheduler()
        disp   = self._manager.dispatcher()
        return assess_engine_health(
            scheduler_queue_depth = sched.queue_depth,
            active_requests       = self._manager.statistics().requests_received
                                    - self._manager.statistics().requests_completed
                                    - self._manager.statistics().requests_failed
                                    - self._manager.statistics().requests_rejected,
            last_success_at       = self._manager.last_success_at,
            uptime_seconds        = self._manager.uptime_seconds,
            scheduler_running     = sched.lifecycle_state() in _RUNNING,
            dispatcher_running    = disp.lifecycle_state() in _RUNNING,
            session_mgr_running   = True,
            registry_running      = True,
        )

    def status(self) -> AnalyticsEngineStatus:
        """Return a point-in-time status snapshot."""
        self._assert_running()
        stats = self._manager.statistics()
        with self._cycle_lock:
            cycle_state = self._cycle_state
        health = self.health()
        return AnalyticsEngineStatus(
            engine_state          = cycle_state,
            health_status         = health.status,
            is_running            = True,
            active_requests       = max(
                0,
                stats.requests_received
                - stats.requests_completed
                - stats.requests_failed
                - stats.requests_rejected,
            ),
            completed_requests    = stats.requests_completed,
            failed_requests       = stats.requests_failed,
            scheduler_queue_depth = self._manager.scheduler().queue_depth,
            dispatcher_count      = self._manager.dispatcher().dispatch_count,
            uptime_seconds        = self._manager.uptime_seconds,
        )
