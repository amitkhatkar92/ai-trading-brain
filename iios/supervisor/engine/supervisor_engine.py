"""
supervisor_engine.py — iios.supervisor.engine
----------------------------------------------
PRIMARY PUBLIC INTERFACE for the AI Supervisor Engine.

Responsibilities (this module ONLY):
  - Accept supervisor workflow requests via submit() / supervise()
  - Wire and coordinate all engine subsystems
  - Expose health(), status(), statistics(), query() introspection
  - Fire engine lifecycle audit events

This module NEVER:
  - Evaluates governance policies (M3 responsibility)
  - Performs AI reasoning or autonomous governance (M4 responsibility)
  - Makes trading decisions
  - Executes trades
  - Communicates with brokers

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 2
"""
from __future__ import annotations

import threading
from typing import Any, Callable, Dict, List, Optional

from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import LifecycleAwareMixin

from .constants import (
    ACTOR_ENGINE,
    ACTOR_OPERATOR,
    ACTOR_SYSTEM,
    DEFAULT_MAX_CONCURRENT_SESSIONS,
    DEFAULT_MAX_PIPELINES,
    DEFAULT_MAX_SCHEDULER_QUEUE,
    ENGINE_SYSTEM_ID,
    EngineState,
    SchedulerPriority,
    SupervisorWorkflowType,
    VERSION,
)
from .supervisor_context import SupervisorEngineContext
from .supervisor_dispatcher import SupervisorDispatcher
from .supervisor_events import make_supervisor_engine_stopped
from .supervisor_factory import SupervisorEngineFactory
from .supervisor_health import SupervisorEngineHealth
from .supervisor_history import SupervisorEngineHistory
from .supervisor_manager import SupervisorWorkflowManager
from .supervisor_registry import SupervisorEngineRegistry
from .supervisor_request import SupervisorRequest
from .supervisor_response import SupervisorResponse
from .supervisor_scheduler import SupervisorScheduler
from .supervisor_session_manager import SupervisorSessionManager
from .supervisor_statistics import SupervisorEngineStatistics
from .supervisor_status import SupervisorEngineStatus
from .supervisor_validation import SupervisorEngineValidator
from .exceptions import (
    SupervisorEngineNotRunningError,
    SupervisorEngineValidationError,
    SupervisorSessionError,
)

_log   = get_logger(__name__)
_audit = get_audit_logger(__name__, engine_id=ENGINE_SYSTEM_ID)


class SupervisorEngine(LifecycleAwareMixin):
    """
    Institutional AI Supervisor Engine.

    Orchestrates supervisor workflows through an 8-phase pipeline:
    Initialize → Discover → Collect → Validate → Dispatch →
    Supervise/Monitor → Publish → Complete.

    Parameters
    ----------
    session_manager :  Injected SupervisorSessionManager (optional).
    scheduler :        Injected SupervisorScheduler (optional).
    dispatcher :       Injected SupervisorDispatcher (optional).
    registry :         Injected SupervisorEngineRegistry (optional).
    factory :          Injected SupervisorEngineFactory (optional).
    validator :        Injected SupervisorEngineValidator (optional).
    health :           Injected SupervisorEngineHealth (optional).
    statistics :       Injected SupervisorEngineStatistics (optional).
    history :          Injected SupervisorEngineHistory (optional).
    manager :          Injected SupervisorWorkflowManager (optional).
    max_sessions :     Maximum concurrent lifecycle sessions.
    max_pipelines :    Maximum active pipelines.
    max_queue :        Maximum scheduler queue depth.
    """

    def __init__(
        self,
        session_manager: Optional[SupervisorSessionManager]  = None,
        scheduler:       Optional[SupervisorScheduler]        = None,
        dispatcher:      Optional[SupervisorDispatcher]       = None,
        registry:        Optional[SupervisorEngineRegistry]   = None,
        factory:         Optional[SupervisorEngineFactory]    = None,
        validator:       Optional[SupervisorEngineValidator]  = None,
        health:          Optional[SupervisorEngineHealth]     = None,
        statistics:      Optional[SupervisorEngineStatistics] = None,
        history:         Optional[SupervisorEngineHistory]    = None,
        manager:         Optional[SupervisorWorkflowManager]  = None,
        *,
        max_sessions:  int = DEFAULT_MAX_CONCURRENT_SESSIONS,
        max_pipelines: int = DEFAULT_MAX_PIPELINES,
        max_queue:     int = DEFAULT_MAX_SCHEDULER_QUEUE,
    ) -> None:
        super().__init__()
        self._max_sessions  = max_sessions
        self._max_pipelines = max_pipelines
        self._max_queue     = max_queue

        # -- Subsystem construction (defaults used when not injected) ----------
        self._session_mgr  = session_manager or SupervisorSessionManager()
        self._scheduler    = scheduler       or SupervisorScheduler(max_queue_size=max_queue)
        self._dispatcher   = dispatcher      or SupervisorDispatcher()
        self._registry     = registry        or SupervisorEngineRegistry(
            max_pipelines=max_pipelines
        )
        self._factory      = factory         or SupervisorEngineFactory()
        self._validator    = validator        or SupervisorEngineValidator(
            max_sessions    = max_sessions,
            active_count_fn = self._active_session_count,
        )
        self._health_rep   = health or SupervisorEngineHealth(
            session_manager = self._session_mgr,
            dispatcher      = self._dispatcher,
            scheduler       = self._scheduler,
            registry        = self._registry,
        )
        self._stats        = statistics or SupervisorEngineStatistics()
        self._hist         = history    or SupervisorEngineHistory()

        # -- Listeners --------------------------------------------------------
        self._listeners: List[Callable] = []
        self._listener_lock = threading.Lock()

        # -- Workflow manager -------------------------------------------------
        self._manager = manager or SupervisorWorkflowManager(
            session_manager = self._session_mgr,
            dispatcher      = self._dispatcher,
            factory         = self._factory,
            health_reporter = self._health_rep,
            statistics      = self._stats,
            history         = self._hist,
            event_listeners = self._listeners,
        )

        # -- Internal engine state --------------------------------------------
        self._engine_state = EngineState.IDLE
        self._state_lock   = threading.Lock()

    # ------------------------------------------------------------------
    # LifecycleAwareMixin hooks
    # ------------------------------------------------------------------

    def _on_start(self) -> None:
        self._session_mgr.start()
        with self._state_lock:
            self._engine_state = EngineState.IDLE
        _audit.log_lifecycle_event(
            ENGINE_SYSTEM_ID, "stopped", "running", VERSION, actor=ACTOR_SYSTEM
        )
        _log.info(f"SupervisorEngine started (max_sessions={self._max_sessions})")

    def _on_stop(self) -> None:
        with self._state_lock:
            prev_state         = self._engine_state
            self._engine_state = EngineState.STOPPED
        self._session_mgr.stop()
        _audit.log_lifecycle_event(
            ENGINE_SYSTEM_ID, "running", "stopped", VERSION, actor=ACTOR_SYSTEM
        )
        event = make_supervisor_engine_stopped("engine", pipeline_id="")
        self._hist.record_event(event)
        self._notify_listeners(event)
        _log.info("SupervisorEngine stopped")

    # ------------------------------------------------------------------
    # Guard
    # ------------------------------------------------------------------

    def _assert_running(self) -> None:
        if self.lifecycle_state().value != "running":
            raise SupervisorEngineNotRunningError()

    def _active_session_count(self) -> int:
        return self._session_mgr.active_session_count()

    # ------------------------------------------------------------------
    # Primary public interface
    # ------------------------------------------------------------------

    def submit(self, request: SupervisorRequest) -> SupervisorResponse:
        """
        Submit a pre-built SupervisorRequest for execution.

        This is the PRIMARY entry point for the supervisor engine.

        Parameters
        ----------
        request : A fully constructed SupervisorRequest.

        Returns
        -------
        SupervisorResponse
            Always returned (never raises).
        """
        self._assert_running()
        self._stats.record_request()
        self._hist.record_request(request)
        self._registry.register_request(request)

        # Validate
        try:
            self._validator.validate_or_raise(request)
        except SupervisorEngineValidationError as exc:
            response = self._factory.create_failure_response(
                request, error_message=str(exc)
            )
            self._registry.register_response(response)
            self._hist.record_response(response)
            self._stats.record_response(success=False)
            return response

        # Build pipeline
        pipeline = self._factory.create_pipeline(request)
        self._registry.register_pipeline(pipeline)
        self._hist.record_pipeline(pipeline)
        self._stats.record_pipeline()

        # Run workflow
        response = self._manager.run_workflow(pipeline, request)

        # Archive pipeline and store response
        self._registry.archive_pipeline(pipeline)
        self._registry.register_response(response)
        self._hist.record_response(response)

        return response

    def supervise(
        self,
        supervision_id: str,
        subsystem_id:   str,
        *,
        workflow_type: SupervisorWorkflowType = SupervisorWorkflowType.ENTERPRISE_HEALTH_REVIEW,
        priority:      SchedulerPriority       = SchedulerPriority.NORMAL,
        inputs:        Optional[Dict[str, Any]] = None,
        metadata:      Optional[Dict[str, Any]] = None,
    ) -> SupervisorResponse:
        """
        Convenience method — build and submit a request in one call.

        Parameters
        ----------
        supervision_id : Supervision run identifier.
        subsystem_id :   Target subsystem identifier.
        workflow_type :  Supervisor workflow classification.
        priority :       Scheduling priority.
        inputs :         Pre-collected enterprise snapshot data.
        metadata :       Supplementary metadata.

        Returns
        -------
        SupervisorResponse
        """
        request = self._factory.create_request(
            supervision_id,
            subsystem_id,
            workflow_type,
            priority = priority,
            inputs   = dict(inputs or {}),
            metadata = dict(metadata or {}),
        )
        return self.submit(request)

    # ------------------------------------------------------------------
    # Governance framework registration (M3 / M4)
    # ------------------------------------------------------------------

    def register_governance_framework(self, framework: Callable) -> None:
        """Register the AI Governance Policy Framework (M3)."""
        self._dispatcher.register_governance_framework(framework)

    def register_autonomous_framework(self, framework: Callable) -> None:
        """Register the Autonomous Governance Framework (M4)."""
        self._dispatcher.register_autonomous_framework(framework)

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def health(self) -> Dict[str, Any]:
        """Return current engine health report."""
        self._stats.record_health_check()
        with self._state_lock:
            state = self._engine_state.value
        return self._health_rep.report(engine_state=state)

    def status(self) -> SupervisorEngineStatus:
        """Return a point-in-time immutable engine status snapshot."""
        with self._state_lock:
            eng_state = self._engine_state
        health_report = self._health_rep.report(engine_state=eng_state.value)
        stats         = self._stats.snapshot()
        return SupervisorEngineStatus(
            engine_state          = eng_state,
            engine_lifecycle      = self.lifecycle_state().value,
            active_pipelines      = self._registry.active_pipeline_count(),
            archived_pipelines    = self._registry.archived_pipeline_count(),
            scheduler_queue_depth = self._scheduler.queue_depth(),
            active_sessions       = self._session_mgr.active_session_count(),
            total_requests        = stats["total_requests"],
            total_responses       = stats["total_responses"],
            health                = health_report.get("overall", "unknown"),
            issues                = list(health_report.get("issues", [])),
        )

    def statistics(self) -> Dict[str, Any]:
        """Return running statistics snapshot."""
        return self._stats.snapshot()

    def query(
        self,
        *,
        supervision_id: Optional[str] = None,
        n:              int            = 20,
    ) -> List[SupervisorResponse]:
        """
        Query recent responses, optionally filtered by supervision_id.

        Parameters
        ----------
        supervision_id : Filter to a specific supervision run.
        n :              Maximum number of responses returned.
        """
        responses = self._registry.recent_responses(n * 2)
        if supervision_id is not None:
            responses = [
                r for r in responses if r.supervision_id == supervision_id
            ]
        return responses[-n:] if len(responses) > n else responses

    # ------------------------------------------------------------------
    # Event listeners
    # ------------------------------------------------------------------

    def add_listener(self, fn: Callable) -> None:
        """Register an event listener."""
        with self._listener_lock:
            if fn not in self._listeners:
                self._listeners.append(fn)

    def remove_listener(self, fn: Callable) -> None:
        """Unregister an event listener."""
        with self._listener_lock:
            # Modify in-place so the manager's aliased reference stays valid.
            self._listeners[:] = [l for l in self._listeners if l != fn]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _notify_listeners(self, event) -> None:
        for fn in list(self._listeners):
            try:
                fn(event)
            except Exception:      # noqa: BLE001
                pass
