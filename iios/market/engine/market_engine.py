"""
market_engine.py — iios.market.engine
========================================
**Primary public interface** for the Institutional Market Engine subsystem.

The Market Engine orchestrates enterprise-wide market intelligence workflows.
It coordinates market sessions, collects institutional market inputs,
dispatches analytics pipelines, publishes market snapshots, and
maintains market operations.

It performs **NO** policy evaluation.
It performs **NO** market analytics.
It performs **NO** optimization.
It performs **NO** trade execution.
It performs **NO** broker communication.

C12 Market Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import threading
import time
from typing import Any, Callable, Dict, List, Optional

from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import LifecycleAwareMixin
from iios.market.lifecycle import MarketLifecycle

from .constants import (
    ENGINE_SYSTEM_ID,
    VERSION,
    EngineState,
    MarketWorkflowType,
    SchedulerPriority,
)
from .exceptions import MarketEngineNotRunningError
from .market_context import MarketEngineContext
from .market_dispatcher import MarketDispatcher
from .market_events import make_market_engine_started, make_market_engine_stopped
from .market_factory import MarketEngineFactory
from .market_health import MarketEngineHealth
from .market_history import MarketEngineHistory
from .market_manager import MarketManager
from .market_pipeline import MarketPipeline
from .market_registry import MarketEngineRegistry
from .market_request import MarketRequest
from .market_response import MarketResponse
from .market_scheduler import MarketScheduler
from .market_session_manager import MarketSessionManager
from .market_statistics import MarketEngineStatistics
from .market_status import MarketEngineStatus
from .market_validation import MarketEngineValidator

_log   = get_logger(__name__)
_audit = get_audit_logger(__name__, engine_id=ENGINE_SYSTEM_ID)


class MarketEngine(LifecycleAwareMixin):
    """
    Institutional Market Engine — primary public interface.

    Wires together all subsystems and provides the single entry point for
    all market workflow submissions.

    Parameters
    ----------
    session_manager : Optional injected session manager.
    scheduler :       Optional injected scheduler.
    dispatcher :      Optional injected dispatcher.
    registry :        Optional injected registry.
    factory :         Optional injected factory.
    validator :       Optional injected validator.
    health :          Optional injected health reporter.
    statistics :      Optional injected statistics.
    history :         Optional injected history.
    manager :         Optional injected workflow manager.
    max_sessions :    Max concurrent lifecycle sessions.
    max_pipelines :   Max concurrent active pipelines.
    max_queue :       Max scheduler queue depth.
    """

    def __init__(
        self,
        session_manager: Optional[MarketSessionManager]   = None,
        scheduler:       Optional[MarketScheduler]        = None,
        dispatcher:      Optional[MarketDispatcher]       = None,
        registry:        Optional[MarketEngineRegistry]   = None,
        factory:         Optional[MarketEngineFactory]    = None,
        validator:       Optional[MarketEngineValidator]  = None,
        health:          Optional[MarketEngineHealth]     = None,
        statistics:      Optional[MarketEngineStatistics] = None,
        history:         Optional[MarketEngineHistory]    = None,
        manager:         Optional[MarketManager]          = None,
        *,
        max_sessions:  int = 200,
        max_pipelines: int = 5_000,
        max_queue:     int = 10_000,
    ) -> None:
        super().__init__()

        self._max_sessions = max_sessions

        # ── Subsystems ───────────────────────────────────────────────
        self._session_manager = session_manager or MarketSessionManager()
        self._scheduler       = scheduler       or MarketScheduler(
            max_queue_size=max_queue
        )
        self._dispatcher      = dispatcher      or MarketDispatcher()
        self._registry        = registry        or MarketEngineRegistry(
            max_pipelines=max_pipelines,
        )
        self._factory   = factory    or MarketEngineFactory()
        self._stats     = statistics or MarketEngineStatistics()
        self._history   = history    or MarketEngineHistory()
        self._health_rp = health     or MarketEngineHealth(
            max_sessions=max_sessions
        )

        self._validator = validator or MarketEngineValidator(
            max_sessions    = max_sessions,
            active_count_fn = self._session_manager.active_session_count,
        )

        self._manager = manager or MarketManager(
            session_manager = self._session_manager,
            dispatcher      = self._dispatcher,
            registry        = self._registry,
            factory         = self._factory,
            validator       = self._validator,
            statistics      = self._stats,
            history         = self._history,
            listener_fn     = self._dispatch_event,
        )

        # ── State ────────────────────────────────────────────────────
        self._engine_state: EngineState = EngineState.IDLE
        self._started_at:   float       = 0.0

        # ── Listeners ────────────────────────────────────────────────
        self._listeners_lock = threading.Lock()
        self._listeners:  List[Callable] = []

    # ==================================================================
    # Lifecycle hooks (LifecycleAwareMixin)
    # ==================================================================

    def _on_start(self) -> None:
        self._started_at   = time.time()
        self._engine_state = EngineState.IDLE
        self._session_manager.start()
        _audit.log_lifecycle_event(
            engine_id  = ENGINE_SYSTEM_ID,
            from_state = "stopped",
            to_state   = "running",
            version    = VERSION,
            actor      = "system",
        )
        _log.info(f"MarketEngine started (version={VERSION})")

    def _on_stop(self) -> None:
        self._engine_state = EngineState.STOPPED
        self._session_manager.stop()
        _audit.log_lifecycle_event(
            engine_id  = ENGINE_SYSTEM_ID,
            from_state = "running",
            to_state   = "stopped",
            version    = VERSION,
            actor      = "system",
            uptime_s   = round(time.time() - self._started_at, 2),
        )
        _log.info("MarketEngine stopped")
        ev = make_market_engine_stopped("engine", ENGINE_SYSTEM_ID)
        self._dispatch_event(ev)

    # ==================================================================
    # Guard
    # ==================================================================

    def _assert_running(self) -> None:
        if self.lifecycle_state().value != "running":
            raise MarketEngineNotRunningError()

    # ==================================================================
    # Primary submission interface
    # ==================================================================

    def submit(self, request: MarketRequest) -> MarketResponse:
        """
        Submit a market workflow request for processing.

        This is the primary entry point for all market workflow submissions.

        Parameters
        ----------
        request : MarketRequest
            Fully constructed market workflow request.

        Returns
        -------
        MarketResponse
            Success or failure response with optional snapshot.
        """
        self._assert_running()

        # Record in history and registry
        self._history.record_request(request)
        self._registry.register_request(request)
        self._stats.record_request_submitted()

        # Schedule
        self._scheduler.schedule(request)

        # Create pipeline
        pipeline = self._factory.create_pipeline(request)
        pipeline.start()
        self._registry.register_pipeline(pipeline)
        self._stats.record_pipeline_started()
        self._history.record_pipeline(pipeline)

        # Emit started event
        ev = make_market_engine_started(
            request.market_analysis_id,
            request.exchange,
            "",  # session_id not yet known
        )
        self._history.record_event(ev)
        self._dispatch_event(ev)

        # Run workflow
        return self._manager.run_workflow(pipeline, request)

    # ==================================================================
    # Named workflow methods
    # ==================================================================

    def initialize_market(
        self,
        market_analysis_id: str,
        exchange:           str,
        *,
        workflow_type: MarketWorkflowType           = MarketWorkflowType.MARKET_OVERVIEW,
        priority:      SchedulerPriority             = SchedulerPriority.NORMAL,
        instrument_id: str                          = "",
        inputs:        Optional[Dict[str, Any]]     = None,
        metadata:      Optional[Dict[str, Any]]     = None,
    ) -> MarketResponse:
        """Initialise a new market analysis workflow."""
        self._assert_running()
        request = self._factory.create_request(
            market_analysis_id,
            exchange,
            workflow_type,
            priority      = priority,
            instrument_id = instrument_id,
            inputs        = inputs,
            metadata      = metadata,
        )
        return self.submit(request)

    def start_analysis(
        self,
        market_analysis_id: str,
        exchange:           str,
        **kwargs: Any,
    ) -> MarketResponse:
        """Launch a market overview analysis workflow."""
        return self.initialize_market(
            market_analysis_id,
            exchange,
            workflow_type = MarketWorkflowType.MARKET_OVERVIEW,
            **kwargs,
        )

    def stop_analysis(
        self,
        market_analysis_id: str,
        exchange:           str,
        **kwargs: Any,
    ) -> MarketResponse:
        """Stop an active market analysis (EOD review)."""
        return self.initialize_market(
            market_analysis_id,
            exchange,
            workflow_type = MarketWorkflowType.EOD_REVIEW,
            **kwargs,
        )

    def collect(
        self,
        market_analysis_id: str,
        exchange:           str,
        inputs:             Dict[str, Any],
        **kwargs: Any,
    ) -> MarketResponse:
        """Submit a market workflow with pre-collected market inputs."""
        self._assert_running()
        request = self._factory.create_request(
            market_analysis_id,
            exchange,
            inputs = inputs,
            **kwargs,
        )
        return self.submit(request)

    def dispatch(
        self,
        market_analysis_id: str,
        exchange:           str,
        **kwargs: Any,
    ) -> MarketResponse:
        """Trigger an intraday market monitoring dispatch."""
        return self.initialize_market(
            market_analysis_id,
            exchange,
            workflow_type = MarketWorkflowType.INTRADAY_MONITORING,
            **kwargs,
        )

    def publish(
        self,
        market_analysis_id: str,
        exchange:           str,
        **kwargs: Any,
    ) -> MarketResponse:
        """Trigger a market snapshot publication (EOD)."""
        return self.initialize_market(
            market_analysis_id,
            exchange,
            workflow_type = MarketWorkflowType.EOD_REVIEW,
            **kwargs,
        )

    # ==================================================================
    # Query
    # ==================================================================

    def query(self, **filters: Any) -> List[MarketPipeline]:
        """Query pipelines matching the supplied keyword filters."""
        self._assert_running()
        return self._registry.query(**filters)

    # ==================================================================
    # Validation
    # ==================================================================

    def validate(self, request: MarketRequest):
        """Run validation checks and return MarketEngineValidationResult."""
        self._assert_running()
        return self._validator.validate_request(request)

    # ==================================================================
    # Observability
    # ==================================================================

    def health(self) -> Dict[str, Any]:
        """Return the current health report."""
        return self._health_rp.report(self._session_manager, self._dispatcher)

    def status(self) -> MarketEngineStatus:
        """Return an immutable engine status snapshot."""
        return MarketEngineStatus(
            engine_id      = ENGINE_SYSTEM_ID,
            state          = self.lifecycle_state().value,
            engine_state   = self._engine_state,
            session_count  = self._session_manager.active_session_count(),
            pipeline_count = self._registry.active_pipeline_count(),
            health         = self.health(),
            statistics     = self._stats.snapshot(),
            started_at     = self._started_at,
        )

    def statistics(self) -> Dict[str, Any]:
        """Return a statistics snapshot."""
        return self._stats.snapshot()

    # ==================================================================
    # Framework registration (M3 / M4 pass-through)
    # ==================================================================

    def register_policy_framework(self, framework: Callable) -> None:
        """Register the Market Policy Framework (M3)."""
        self._dispatcher.register_policy_framework(framework)

    def register_analytics_framework(self, framework: Callable) -> None:
        """Register the Market Analytics & Intelligence Framework (M4)."""
        self._dispatcher.register_analytics_framework(framework)

    # ==================================================================
    # Listener management
    # ==================================================================

    def add_listener(self, fn: Callable) -> None:
        """Register a market-engine event listener."""
        with self._listeners_lock:
            if not any(l == fn for l in self._listeners):
                self._listeners.append(fn)

    def remove_listener(self, fn: Callable) -> None:
        """Unregister a market-engine event listener."""
        with self._listeners_lock:
            self._listeners = [l for l in self._listeners if l != fn]

    def _dispatch_event(self, event) -> None:
        with self._listeners_lock:
            listeners = list(self._listeners)
        for fn in listeners:
            try:
                fn(event)
            except Exception:   # noqa: BLE001
                pass
