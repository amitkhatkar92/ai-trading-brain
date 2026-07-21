"""
portfolio_engine.py — iios.portfolio.engine
============================================
Primary public interface of the Portfolio Engine subsystem.

:class:`PortfolioEngine` is the ONLY interface external callers use to
interact with the Portfolio Intelligence platform.

Responsibilities
----------------
* Initialize portfolio sessions
* Manage portfolio lifecycle
* Coordinate portfolio workflows
* Collect institutional inputs
* Dispatch portfolio pipelines to M3 / M4
* Publish portfolio snapshots
* Maintain history and statistics

Non-Responsibilities (intentional exclusions)
---------------------------------------------
* Portfolio policy evaluation (delegated to M3)
* Portfolio optimisation (delegated to M4)
* Trade execution
* Broker communication

C10 Portfolio Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import threading
import time
from typing import Any, Callable, Dict, List, Optional

from iios.common.errors.exceptions import IIOSError
from iios.common.logging.logging_manager import get_logger
from iios.common.logging.audit_logger import get_audit_logger
from iios.investment.workflow.engine_lifecycle import LifecycleAwareMixin

from .constants import (
    ACTOR_ENGINE,
    DEFAULT_MAX_CONCURRENT_SESSIONS,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_PIPELINES,
    DEFAULT_MAX_SCHEDULER_QUEUE,
    ENGINE_SYSTEM_ID,
    VERSION,
    EngineState,
    PortfolioWorkflowType,
    ResponseStatus,
    SchedulerPriority,
)
from .exceptions import (
    PortfolioCapacityError,
    PortfolioEngineError,
    PortfolioEngineNotRunningError,
    PortfolioEngineValidationError,
)
from .portfolio_context import PortfolioContext
from .portfolio_dispatcher import PortfolioDispatcher
from .portfolio_events import (
    PortfolioEngineEvent,
    make_portfolio_stopped,
)
from .portfolio_factory import PortfolioEngineFactory
from .portfolio_health import PortfolioEngineHealth
from .portfolio_history import PortfolioEngineHistory
from .portfolio_manager import PortfolioManager
from .portfolio_pipeline import PortfolioPipeline
from .portfolio_registry import PortfolioEngineRegistry
from .portfolio_request import PortfolioRequest
from .portfolio_response import PortfolioResponse, PortfolioSnapshot
from .portfolio_scheduler import PortfolioScheduler
from .portfolio_session_manager import PortfolioSessionManager
from .portfolio_statistics import PortfolioEngineStatistics
from .portfolio_status import PortfolioEngineStatus
from .portfolio_validation import PortfolioEngineValidator, PortfolioValidationResult

_log   = get_logger(__name__)
_audit = get_audit_logger(__name__, engine_id=ENGINE_SYSTEM_ID)


class PortfolioEngine(LifecycleAwareMixin):
    """
    Institutional Portfolio Engine.

    This is the ONLY public interface external callers should use.

    The engine coordinates all institutional portfolio workflows across
    the IIOS platform. It orchestrates portfolio sessions, capital
    management workflows, allocation pipelines, rebalancing workflows,
    and portfolio publication.

    Parameters
    ----------
    max_concurrent_sessions :  Maximum concurrent portfolio sessions.
    max_archived_sessions :    Maximum archived sessions in memory.
    max_pipelines :            Maximum pipeline records retained.
    max_history :              Maximum history entries per collection.
    max_scheduler_queue :      Maximum pending requests in the scheduler.

    Examples
    --------
    ::

        engine = PortfolioEngine()
        engine.start()

        request = PortfolioRequest.create("pf-001", PortfolioWorkflowType.PORTFOLIO_CREATION)
        response = engine.submit(request)

        if response.is_success:
            snapshot = response.snapshot
        engine.stop()
    """

    def __init__(
        self,
        max_concurrent_sessions: int = DEFAULT_MAX_CONCURRENT_SESSIONS,
        max_archived_sessions:   int = 10_000,
        max_pipelines:           int = DEFAULT_MAX_PIPELINES,
        max_history:             int = DEFAULT_MAX_HISTORY,
        max_scheduler_queue:     int = DEFAULT_MAX_SCHEDULER_QUEUE,
    ) -> None:
        super().__init__()
        self._engine_state     = EngineState.IDLE
        self._engine_state_lock = threading.Lock()
        self._started_at: Optional[float] = None

        # Sub-components
        self._session_manager = PortfolioSessionManager(
            max_active_sessions   = max_concurrent_sessions,
            max_archived_sessions = max_archived_sessions,
        )
        self._scheduler  = PortfolioScheduler(max_queue_size=max_scheduler_queue)
        self._dispatcher = PortfolioDispatcher()
        self._registry   = PortfolioEngineRegistry(
            max_active_pipelines   = max_pipelines,
            max_archived_pipelines = max_pipelines,
        )
        self._factory    = PortfolioEngineFactory()
        self._validator  = PortfolioEngineValidator()
        self._health     = PortfolioEngineHealth()
        self._stats      = PortfolioEngineStatistics()
        self._history    = PortfolioEngineHistory(max_entries=max_history)
        self._manager    = PortfolioManager(
            session_manager = self._session_manager,
            dispatcher      = self._dispatcher,
            registry        = self._registry,
            factory         = self._factory,
            statistics      = self._stats,
            history         = self._history,
            dispatch_event  = self._dispatch_event,
        )

        self._listeners: List[Callable[[PortfolioEngineEvent], None]] = []
        self._listener_lock = threading.Lock()

    # ==================================================================
    # LifecycleAwareMixin hooks
    # ==================================================================

    def _on_start(self) -> None:
        self._started_at = time.time()
        _log.info(f"PortfolioEngine starting (version={VERSION})")
        _audit.log_lifecycle_event(
            engine_id  = ENGINE_SYSTEM_ID,
            from_state = "STOPPED",
            to_state   = "RUNNING",
            version    = VERSION,
            actor      = ACTOR_ENGINE,
        )

    def _on_stop(self) -> None:
        _log.info(f"PortfolioEngine stopping")
        self._session_manager.stop()
        _audit.log_lifecycle_event(
            engine_id  = ENGINE_SYSTEM_ID,
            from_state = "RUNNING",
            to_state   = "STOPPED",
            version    = VERSION,
            actor      = ACTOR_ENGINE,
        )
        event = make_portfolio_stopped(ENGINE_SYSTEM_ID)
        self._history.record_event(event)
        self._dispatch_event(event)

    # ==================================================================
    # Primary submission API
    # ==================================================================

    def submit(self, request: PortfolioRequest) -> PortfolioResponse:
        """
        Submit a portfolio workflow request for immediate processing.

        Validates the request, creates a pipeline, executes the workflow
        end-to-end, and returns a response with an optional snapshot.

        Parameters
        ----------
        request : Portfolio workflow request.

        Returns
        -------
        PortfolioResponse
            Always returns a response — failures are captured in the response
            rather than raised as exceptions (for predictable control flow).

        Raises
        ------
        PortfolioEngineNotRunningError
            When the engine has not been started.
        """
        self._assert_running()
        t0 = time.monotonic()

        # Record request
        self._registry.register_request(request)
        self._history.record_request(request)
        self._stats.record_request(request.workflow_type)

        # Validate
        validation = self._validator.validate_request(request)
        if not validation.is_valid:
            elapsed = time.monotonic() - t0
            response = self._factory.create_failure_response(
                request,
                error_message = "; ".join(validation.error_messages),
                elapsed_s     = elapsed,
            )
            self._history.record_response(response)
            return response

        # Create pipeline
        try:
            pipeline = self._factory.create_pipeline(request)
            self._registry.register_pipeline(pipeline)
        except PortfolioCapacityError as exc:
            response = self._factory.create_failure_response(
                request, error_message=str(exc), elapsed_s=time.monotonic() - t0
            )
            self._history.record_response(response)
            return response

        # Run workflow
        return self._manager.run_workflow(pipeline, request)

    # ==================================================================
    # Named workflow operations
    # ==================================================================

    def initialize_portfolio(
        self,
        portfolio_id: str,
        *,
        priority: SchedulerPriority = SchedulerPriority.NORMAL,
        inputs:   Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PortfolioResponse:
        """Initialize a new portfolio session via a PORTFOLIO_CREATION workflow."""
        self._assert_running()
        request = self._factory.create_request(
            portfolio_id,
            PortfolioWorkflowType.PORTFOLIO_CREATION,
            priority = priority,
            inputs   = inputs,
            metadata = metadata,
        )
        return self.submit(request)

    def start_portfolio(
        self,
        portfolio_id: str,
        *,
        workflow_type: PortfolioWorkflowType = PortfolioWorkflowType.PORTFOLIO_UPDATE,
        priority:      SchedulerPriority     = SchedulerPriority.NORMAL,
        inputs:        Optional[Dict[str, Any]] = None,
        metadata:      Optional[Dict[str, Any]] = None,
    ) -> PortfolioResponse:
        """Start a portfolio workflow session."""
        self._assert_running()
        request = self._factory.create_request(
            portfolio_id,
            workflow_type,
            priority = priority,
            inputs   = inputs,
            metadata = metadata,
        )
        return self.submit(request)

    def stop_portfolio(
        self,
        portfolio_id: str,
        *,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PortfolioResponse:
        """Stop a portfolio via a PORTFOLIO_CLOSURE workflow."""
        self._assert_running()
        request = self._factory.create_request(
            portfolio_id,
            PortfolioWorkflowType.PORTFOLIO_CLOSURE,
            metadata = metadata,
        )
        return self.submit(request)

    def collect(
        self,
        portfolio_id: str,
        inputs:       Dict[str, Any],
        *,
        workflow_type: PortfolioWorkflowType = PortfolioWorkflowType.PORTFOLIO_UPDATE,
        priority:      SchedulerPriority     = SchedulerPriority.NORMAL,
    ) -> PortfolioResponse:
        """Submit a workflow request with pre-collected inputs."""
        self._assert_running()
        request = self._factory.create_request(
            portfolio_id,
            workflow_type,
            priority = priority,
            inputs   = inputs,
        )
        return self.submit(request)

    def dispatch(
        self,
        portfolio_id:  str,
        workflow_type: PortfolioWorkflowType = PortfolioWorkflowType.PORTFOLIO_UPDATE,
        *,
        inputs:   Optional[Dict[str, Any]] = None,
        priority: SchedulerPriority        = SchedulerPriority.NORMAL,
    ) -> PortfolioResponse:
        """Dispatch a workflow without prior collection step."""
        return self.collect(
            portfolio_id, inputs or {},
            workflow_type = workflow_type,
            priority      = priority,
        )

    def publish(
        self,
        portfolio_id:  str,
        *,
        inputs:   Optional[Dict[str, Any]] = None,
        priority: SchedulerPriority        = SchedulerPriority.NORMAL,
    ) -> PortfolioResponse:
        """Publish a portfolio snapshot (PORTFOLIO_SYNCHRONIZATION workflow)."""
        return self.collect(
            portfolio_id, inputs or {},
            workflow_type = PortfolioWorkflowType.PORTFOLIO_SYNCHRONIZATION,
            priority      = priority,
        )

    # ==================================================================
    # Query API
    # ==================================================================

    def query(self, portfolio_id: str) -> PortfolioResponse:
        """
        Query the engine for information about a portfolio.

        Returns the most recent response for the given portfolio, or a
        synthetic success response if none exists.
        """
        self._assert_running()
        responses = self._history.responses_for_portfolio(portfolio_id)
        if responses:
            return responses[-1]
        # Return a synthetic informational response
        request = self._factory.create_request(
            portfolio_id, PortfolioWorkflowType.PORTFOLIO_VALIDATION
        )
        return PortfolioResponse.create_success(
            request_id    = request.request_id,
            portfolio_id  = portfolio_id,
            workflow_type = PortfolioWorkflowType.PORTFOLIO_VALIDATION,
            metadata      = {"query_result": "no_history"},
        )

    def validate(self, request: PortfolioRequest) -> PortfolioValidationResult:
        """Run structural validation on a request without executing it."""
        self._assert_running()
        return self._validator.validate_request(request)

    # ==================================================================
    # Status / Statistics / Health / History
    # ==================================================================

    def status(self) -> PortfolioEngineStatus:
        """Return a point-in-time engine status snapshot."""
        self._assert_running()
        uptime = time.time() - self._started_at if self._started_at else 0.0
        return PortfolioEngineStatus(
            engine_state        = self._engine_state,
            lifecycle_state     = self.lifecycle_state().value,
            active_pipelines    = self._registry.active_count(),
            completed_pipelines = self._registry.completed_count(),
            failed_pipelines    = self._registry.failed_count(),
            pending_requests    = self._scheduler.pending_count(),
            is_healthy          = self._health.is_healthy(),
            statistics_snapshot = self._stats.snapshot(),
            uptime_s            = uptime,
        )

    def statistics(self) -> Dict[str, Any]:
        """Return a statistics snapshot dict."""
        self._assert_running()
        snap = self._stats.snapshot()
        snap["active_pipelines"]    = self._registry.active_count()
        snap["completed_pipelines"] = self._registry.completed_count()
        snap["failed_pipelines"]    = self._registry.failed_count()
        snap["pending_requests"]    = self._scheduler.pending_count()
        return snap

    def health(self) -> Dict[str, Any]:
        """Return a health snapshot dict."""
        self._assert_running()
        h = self._health.snapshot()
        h["dispatcher"] = self._dispatcher.statistics()
        return h

    def history(self) -> Dict[str, Any]:
        """Return a history snapshot dict."""
        self._assert_running()
        return {
            "events":    [e.to_dict() for e in self._history.events()],
            "requests":  [r.to_dict() for r in self._history.requests()],
            "responses": [r.to_dict() for r in self._history.responses()],
            "pipelines": [p.to_dict() for p in self._history.pipelines()],
            "summary":   self._history.summary(),
        }

    # ==================================================================
    # Framework plugin registration
    # ==================================================================

    def register_policy_framework(self, framework: Callable) -> None:
        """Register the Portfolio Policy Framework (M3) with the dispatcher."""
        self._assert_running()
        self._dispatcher.register_policy_framework(framework)

    def register_optimization_framework(self, framework: Callable) -> None:
        """Register the Portfolio Optimization Framework (M4) with the dispatcher."""
        self._assert_running()
        self._dispatcher.register_optimization_framework(framework)

    # ==================================================================
    # Event listeners
    # ==================================================================

    def add_listener(self, listener: Callable[[PortfolioEngineEvent], None]) -> None:
        """Register a callable to receive portfolio engine events."""
        with self._listener_lock:
            if listener not in self._listeners:
                self._listeners.append(listener)

    def remove_listener(self, listener: Callable[[PortfolioEngineEvent], None]) -> None:
        """Deregister a previously registered event listener."""
        with self._listener_lock:
            try:
                self._listeners.remove(listener)
            except ValueError:
                pass

    # ==================================================================
    # Internal helpers
    # ==================================================================

    def _assert_running(self) -> None:
        """Guard: raise if the engine is not in RUNNING state."""
        if self.lifecycle_state().value != "running":
            raise PortfolioEngineNotRunningError()

    def _dispatch_event(self, event: PortfolioEngineEvent) -> None:
        """Deliver an event to all registered listeners (errors are absorbed)."""
        with self._listener_lock:
            listeners = list(self._listeners)
        for listener in listeners:
            try:
                listener(event)
            except Exception as exc:
                _log.warning(f"Portfolio engine listener error: {exc}")

    def _set_engine_state(self, state: EngineState) -> None:
        with self._engine_state_lock:
            self._engine_state = state
