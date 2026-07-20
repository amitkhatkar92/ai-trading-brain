"""
decision_engine.py — iios.decision.engine
==========================================
PRIMARY PUBLIC INTERFACE for the Institutional Decision Engine subsystem.

:class:`DecisionEngine` is the ONLY entry point that external callers
(orchestrators, controllers, workflows) interact with.  All internal
components (session manager, scheduler, dispatcher, manager, registry) are
hidden behind this facade.

Usage example::

    engine = DecisionEngine()
    engine.start()

    request = DecisionRequest.create("decision-001")
    response = engine.submit(request)

    snapshot = response.snapshot          # DecisionSnapshot
    health   = engine.health()            # DecisionEngineHealth
    status   = engine.status()            # DecisionEngineStatus
    stats    = engine.statistics()        # DecisionEngineStatistics

    engine.stop()

This engine:
  * Orchestrates decision session lifecycle
  * Coordinates workflow pipelines
  * Collects institutional inputs
  * Dispatches to Policy Framework (M3) and Optimization Framework (M4)
  * Publishes decision snapshots
  * Maintains history and statistics

This engine does NOT:
  * Evaluate decision policies
  * Perform optimization
  * Execute trades
  * Communicate with brokers

C9 Decision Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import threading
import time
from typing import Any, Callable, Dict, List, Optional

from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin
from iios.common.logging.logging_manager import get_logger
from iios.common.logging.audit_logger import get_audit_logger
from iios.decision.lifecycle import DecisionLifecycle

from .constants import (
    ACTOR_ENGINE,
    ACTOR_SYSTEM,
    ENGINE_SYSTEM_ID,
    VERSION,
    DEFAULT_MAX_ACTIVE,
    DEFAULT_MAX_COMPLETED,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_QUEUE,
    DEFAULT_WORKER_THREADS,
    EngineOperationalStatus,
)
from .decision_dispatcher     import DecisionDispatcher, PolicyFrameworkProtocol, OptimizationFrameworkProtocol
from .decision_engine_worker  import DecisionEngineWorker
from .decision_events         import DecisionEngineEvent, DecisionEngineEventType
from .decision_factory        import DecisionEngineFactory
from .decision_health         import DecisionEngineHealth, assess_engine_health
from .decision_history        import DecisionEngineHistory
from .decision_manager        import DecisionManager
from .decision_registry       import DecisionEngineRegistry
from .decision_request        import DecisionRequest
from .decision_response       import DecisionResponse, DecisionSnapshot
from .decision_scheduler      import DecisionScheduler
from .decision_session_manager import DecisionSessionManager
from .decision_statistics     import DecisionEngineStatistics
from .decision_status         import DecisionEngineStatus, build_engine_status
from .decision_validation     import DecisionEngineValidator, EngineValidationResult
from .exceptions import (
    DecisionEngineNotRunningError,
    DecisionRequestNotFoundError,
)

_log   = get_logger(__name__)
_audit = get_audit_logger(__name__, engine_id=ENGINE_SYSTEM_ID)

_RUNNING = frozenset({EngineState.RUNNING, "running"})


class DecisionEngine(LifecycleAwareMixin):
    """
    Institutional Decision Engine — primary public entry point.

    Coordinates the complete decision intelligence workflow from request
    submission through snapshot publication.

    Parameters
    ----------
    max_active :        Maximum simultaneous active pipelines.
    max_completed :     Maximum completed pipelines retained in memory.
    max_history :       Maximum events and responses retained in history.
    max_queue :         Maximum queued requests.
    worker_threads :    Number of background worker threads.
    policy_framework :  Optional M3 policy framework instance.
    optimization_framework : Optional M4 optimization framework instance.
    """

    def __init__(
        self,
        max_active:             int = DEFAULT_MAX_ACTIVE,
        max_completed:          int = DEFAULT_MAX_COMPLETED,
        max_history:            int = DEFAULT_MAX_HISTORY,
        max_queue:              int = DEFAULT_MAX_QUEUE,
        worker_threads:         int = DEFAULT_WORKER_THREADS,
        policy_framework:       Optional[PolicyFrameworkProtocol]       = None,
        optimization_framework: Optional[OptimizationFrameworkProtocol] = None,
    ) -> None:
        super().__init__()
        self._lock = threading.RLock()

        # ── Shared infrastructure ────────────────────────────────────────
        self._statistics = DecisionEngineStatistics()
        self._history    = DecisionEngineHistory(
            max_events    = max_history,
            max_responses = max_history,
        )
        self._registry   = DecisionEngineRegistry(
            max_active    = max_active,
            max_completed = max_completed,
        )
        self._factory    = DecisionEngineFactory()
        self._validator  = DecisionEngineValidator()

        # ── Lifecycle (M1) ───────────────────────────────────────────────
        self._lifecycle = DecisionLifecycle(
            max_active_sessions = max_active,
        )

        # ── Session manager ──────────────────────────────────────────────
        self._session_mgr = DecisionSessionManager(self._lifecycle)

        # ── Scheduler ────────────────────────────────────────────────────
        self._scheduler = DecisionScheduler(max_queue=max_queue)

        # ── Dispatcher ───────────────────────────────────────────────────
        self._dispatcher = DecisionDispatcher(
            policy_framework       = policy_framework,
            optimization_framework = optimization_framework,
        )

        # ── Manager (internal workflow orchestrator) ─────────────────────
        self._manager = DecisionManager(
            session_manager = self._session_mgr,
            dispatcher      = self._dispatcher,
            registry        = self._registry,
            factory         = self._factory,
            statistics      = self._statistics,
            history         = self._history,
        )

        # ── Worker pool ──────────────────────────────────────────────────
        self._workers: List[DecisionEngineWorker] = []
        self._worker_threads  = max(1, worker_threads)

        # ── Listeners ────────────────────────────────────────────────────
        self._listeners: List[Callable[[DecisionEngineEvent], None]] = []

        # ── Startup bookkeeping ──────────────────────────────────────────
        self._started_at:    Optional[float] = None
        self._completed_total: int           = 0
        self._failed_total:    int           = 0

    # ==================================================================
    # LifecycleAwareMixin hooks
    # ==================================================================

    def _on_start(self) -> None:
        self._lifecycle.start()
        self._started_at = time.time()

        # Start background workers
        for i in range(self._worker_threads):
            w = DecisionEngineWorker(
                worker_id = f"worker-{i}",
                scheduler = self._scheduler,
                manager   = self._manager,
                on_complete = self._on_worker_complete,
                on_fail     = self._on_worker_fail,
            )
            w.start()
            self._workers.append(w)

        _audit.log_lifecycle_event(
            engine_id  = ENGINE_SYSTEM_ID,
            from_state = "stopped",
            to_state   = "running",
            version    = VERSION,
            actor      = ACTOR_SYSTEM,
        )
        _log.info("DecisionEngine: started")

    def _on_stop(self) -> None:
        # Stop background workers
        for w in self._workers:
            w.stop()
        self._workers.clear()

        # Stop the internal lifecycle
        try:
            self._lifecycle.stop()
        except Exception:
            pass

        _audit.log_lifecycle_event(
            engine_id  = ENGINE_SYSTEM_ID,
            from_state = "running",
            to_state   = "stopped",
            version    = VERSION,
            actor      = ACTOR_SYSTEM,
        )
        _log.info("DecisionEngine: stopped")

    # ==================================================================
    # Primary operations
    # ==================================================================

    def submit(self, request: DecisionRequest) -> DecisionResponse:
        """
        Submit a :class:`DecisionRequest` for immediate synchronous processing.

        The engine executes the complete nine-step workflow inline and returns
        a :class:`DecisionResponse` with the decision snapshot.

        Parameters
        ----------
        request : The decision request to process.

        Returns
        -------
        DecisionResponse

        Raises
        ------
        DecisionEngineNotRunningError
            When the engine has not been started.
        """
        self._assert_running()
        self._statistics.record_request_submitted()
        _log.debug(f"DecisionEngine: submit request {request.request_id!r}")

        self._registry.register_request(request)
        response = self._manager.process(request)

        if response.is_success:
            with self._lock:
                self._completed_total += 1
        else:
            with self._lock:
                self._failed_total += 1

        # Notify engine-level listeners with the latest event for this decision
        evt = self._history.latest_event()
        if evt is not None:
            with self._lock:
                listeners_copy = list(self._listeners)
            for cb in listeners_copy:
                try:
                    cb(evt)
                except Exception as exc:
                    _log.warning(
                        f"DecisionEngine: listener error for "
                        f"{evt.event_type.value}: {exc}"
                    )

        return response

    def schedule(self, request: DecisionRequest) -> None:
        """
        Enqueue *request* for asynchronous background processing.

        The request will be picked up by the next available worker.

        Raises
        ------
        DecisionEngineNotRunningError
        """
        self._assert_running()
        self._statistics.record_request_submitted()
        self._registry.register_request(request)
        self._scheduler.schedule(request)

    def cancel(self, request_id: str) -> bool:
        """
        Cancel a queued (not yet processing) request.

        Returns ``True`` if the request was found and cancelled.
        """
        self._assert_running()
        return self._scheduler.cancel(request_id)

    # ==================================================================
    # Queries
    # ==================================================================

    def query(self, session_id: str) -> Optional[DecisionResponse]:
        """
        Return the most recent response for *session_id*, or ``None``.
        """
        self._assert_running()
        responses = self._history.responses()
        for r in reversed(responses):
            if r.session_id == session_id:
                return r
        return None

    def history(self) -> DecisionEngineHistory:
        """Return the shared :class:`DecisionEngineHistory` instance."""
        return self._history

    def statistics(self) -> DecisionEngineStatistics:
        """Return the shared :class:`DecisionEngineStatistics` instance."""
        return self._statistics

    def validate(self, request: DecisionRequest) -> EngineValidationResult:
        """
        Validate *request* without processing it.

        Returns :class:`EngineValidationResult`.
        """
        return self._validator.validate_request(
            request,
            engine_running = self.lifecycle_state() in _RUNNING,
        )

    # ==================================================================
    # Observability
    # ==================================================================

    def health(self) -> DecisionEngineHealth:
        """Return a :class:`DecisionEngineHealth` snapshot."""
        is_running = self.lifecycle_state() in _RUNNING
        lc_ok = True
        try:
            lc_ok = self._lifecycle.lifecycle_state() in _RUNNING
        except Exception:
            lc_ok = False

        health = assess_engine_health(
            engine_running = is_running,
            lifecycle_ok   = lc_ok,
            scheduler_ok   = True,
            dispatcher_ok  = True,
            registry_ok    = True,
        )
        self._statistics.record_health_check(health.is_healthy)
        return health

    def status(self) -> DecisionEngineStatus:
        """Return a :class:`DecisionEngineStatus` snapshot."""
        is_running = self.lifecycle_state() in _RUNNING
        operational = (
            EngineOperationalStatus.RUNNING if is_running
            else EngineOperationalStatus.STOPPED
        )
        with self._lock:
            completed = self._completed_total
            failed    = self._failed_total

        return build_engine_status(
            operational      = operational,
            active_sessions  = self._session_mgr.session_count(),
            active_pipelines = self._registry.active_count(),
            queued_requests  = self._scheduler.pending_count(),
            completed_total  = completed,
            failed_total     = failed,
            started_at       = self._started_at or 0.0,
        )

    # ==================================================================
    # Framework injection
    # ==================================================================

    def set_policy_framework(self, framework: PolicyFrameworkProtocol) -> None:
        """Inject or replace the Decision Policy Framework (M3)."""
        self._dispatcher.set_policy_framework(framework)

    def set_optimization_framework(self, framework: OptimizationFrameworkProtocol) -> None:
        """Inject or replace the Decision Optimization Framework (M4)."""
        self._dispatcher.set_optimization_framework(framework)

    # ==================================================================
    # Event listeners
    # ==================================================================

    def add_listener(self, listener: Callable[[DecisionEngineEvent], None]) -> None:
        """Register a synchronous event listener."""
        with self._lock:
            if listener not in self._listeners:
                self._listeners.append(listener)

    def remove_listener(self, listener: Callable[[DecisionEngineEvent], None]) -> None:
        """Deregister an event listener."""
        with self._lock:
            try:
                self._listeners.remove(listener)
            except ValueError:
                pass

    # ==================================================================
    # Internal helpers
    # ==================================================================

    def _assert_running(self) -> None:
        if self.lifecycle_state() not in _RUNNING:
            raise DecisionEngineNotRunningError("submit")

    def _on_worker_complete(self, response: DecisionResponse) -> None:
        """Called by a background worker when a pipeline completes."""
        with self._lock:
            self._completed_total += 1
        self._history.record_response(response)

    def _on_worker_fail(self, response: DecisionResponse) -> None:
        """Called by a background worker when a pipeline fails."""
        with self._lock:
            self._failed_total += 1
        self._history.record_response(response)

    def _dispatch_event(self, event: DecisionEngineEvent) -> None:
        self._history.record_event(event)
        with self._lock:
            listeners = list(self._listeners)
        for listener in listeners:
            try:
                listener(event)
            except Exception as exc:
                _log.warning(
                    f"DecisionEngine: listener error for "
                    f"{event.event_type.value}: {exc}"
                )

    def __repr__(self) -> str:
        state = self.lifecycle_state()
        state_str = state.value if hasattr(state, "value") else str(state)
        return (
            f"DecisionEngine("
            f"state={state_str!r}, "
            f"active_pipelines={self._registry.active_count()}, "
            f"version={VERSION!r})"
        )
