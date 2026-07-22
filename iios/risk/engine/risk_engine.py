"""
risk_engine.py — iios.risk.engine
====================================
**Primary public interface** for the Institutional Risk Engine subsystem.

The Risk Engine orchestrates enterprise-wide risk management workflows.
It coordinates risk sessions, collects institutional risk inputs,
dispatches assessment pipelines, publishes risk snapshots, and
maintains risk operations.

It performs **NO** policy evaluation.
It performs **NO** quantitative risk calculations.
It performs **NO** optimization.
It performs **NO** trade execution.
It performs **NO** broker communication.

C11 Risk Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import threading
import time
from typing import Any, Callable, Dict, List, Optional

from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import LifecycleAwareMixin
from iios.risk.lifecycle import RiskLifecycle, RiskType

from .constants import (
    ENGINE_SYSTEM_ID,
    VERSION,
    EngineState,
    RiskWorkflowType,
    SchedulerPriority,
)
from .exceptions import RiskEngineNotRunningError
from .risk_context import RiskEngineContext
from .risk_dispatcher import RiskDispatcher
from .risk_events import make_risk_started, make_risk_stopped
from .risk_factory import RiskEngineFactory
from .risk_health import RiskEngineHealth
from .risk_history import RiskEngineHistory
from .risk_manager import RiskManager
from .risk_pipeline import RiskPipeline
from .risk_registry import RiskEngineRegistry
from .risk_request import RiskRequest
from .risk_response import RiskResponse
from .risk_scheduler import RiskScheduler
from .risk_session_manager import RiskSessionManager
from .risk_statistics import RiskEngineStatistics
from .risk_status import RiskEngineStatus
from .risk_validation import RiskEngineValidator

_log   = get_logger(__name__)
_audit = get_audit_logger(__name__, engine_id=ENGINE_SYSTEM_ID)


class RiskEngine(LifecycleAwareMixin):
    """
    Institutional Risk Engine — primary public interface.

    Wires together all subsystems and provides the single entry point for
    all risk workflow submissions.

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
        session_manager: Optional[RiskSessionManager]    = None,
        scheduler:       Optional[RiskScheduler]         = None,
        dispatcher:      Optional[RiskDispatcher]        = None,
        registry:        Optional[RiskEngineRegistry]    = None,
        factory:         Optional[RiskEngineFactory]     = None,
        validator:       Optional[RiskEngineValidator]   = None,
        health:          Optional[RiskEngineHealth]      = None,
        statistics:      Optional[RiskEngineStatistics]  = None,
        history:         Optional[RiskEngineHistory]     = None,
        manager:         Optional[RiskManager]           = None,
        *,
        max_sessions:  int = 100,
        max_pipelines: int = 5_000,
        max_queue:     int = 10_000,
    ) -> None:
        super().__init__()

        self._max_sessions = max_sessions

        # ── Subsystems ───────────────────────────────────────────────
        self._session_manager = session_manager or RiskSessionManager()
        self._scheduler       = scheduler       or RiskScheduler(max_queue_size=max_queue)
        self._dispatcher      = dispatcher      or RiskDispatcher()
        self._registry        = registry        or RiskEngineRegistry(
            max_pipelines=max_pipelines,
        )
        self._factory   = factory    or RiskEngineFactory()
        self._stats     = statistics or RiskEngineStatistics()
        self._history   = history    or RiskEngineHistory()
        self._health_rp = health     or RiskEngineHealth(max_sessions=max_sessions)

        self._validator = validator or RiskEngineValidator(
            max_sessions    = max_sessions,
            active_count_fn = self._session_manager.active_session_count,
        )

        self._manager = manager or RiskManager(
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
        _log.info(f"RiskEngine started (version={VERSION})")

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
        _log.info("RiskEngine stopped")
        ev = make_risk_stopped("engine", ENGINE_SYSTEM_ID)
        self._dispatch_event(ev)

    # ==================================================================
    # Guard
    # ==================================================================

    def _assert_running(self) -> None:
        if self.lifecycle_state().value != "running":
            raise RiskEngineNotRunningError()

    # ==================================================================
    # Primary submission interface
    # ==================================================================

    def submit(self, request: RiskRequest) -> RiskResponse:
        """
        Submit a risk workflow request for processing.

        This is the primary entry point for all risk workflow submissions.

        Parameters
        ----------
        request : RiskRequest
            Fully constructed risk workflow request.

        Returns
        -------
        RiskResponse
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
        ev = make_risk_started(
            request.risk_id,
            request.portfolio_id,
            "",  # session_id not yet known
        )
        self._history.record_event(ev)
        self._dispatch_event(ev)

        # Run workflow
        return self._manager.run_workflow(pipeline, request)

    # ==================================================================
    # Named workflow methods
    # ==================================================================

    def initialize_risk(
        self,
        risk_id:       str,
        portfolio_id:  str,
        *,
        workflow_type: RiskWorkflowType             = RiskWorkflowType.PORTFOLIO_RISK_ASSESSMENT,
        priority:      SchedulerPriority             = SchedulerPriority.NORMAL,
        strategy_id:   str                          = "",
        inputs:        Optional[Dict[str, Any]]     = None,
        metadata:      Optional[Dict[str, Any]]     = None,
    ) -> RiskResponse:
        """Initialise a new risk assessment workflow."""
        self._assert_running()
        request = self._factory.create_request(
            risk_id,
            portfolio_id,
            workflow_type,
            priority    = priority,
            strategy_id = strategy_id,
            inputs      = inputs,
            metadata    = metadata,
        )
        return self.submit(request)

    def start_assessment(
        self,
        risk_id:      str,
        portfolio_id: str,
        **kwargs: Any,
    ) -> RiskResponse:
        """Launch a portfolio risk assessment workflow."""
        return self.initialize_risk(
            risk_id,
            portfolio_id,
            workflow_type = RiskWorkflowType.PORTFOLIO_RISK_ASSESSMENT,
            **kwargs,
        )

    def stop_assessment(
        self,
        risk_id:      str,
        portfolio_id: str,
        **kwargs: Any,
    ) -> RiskResponse:
        """Stop an active risk assessment (EOD review)."""
        return self.initialize_risk(
            risk_id,
            portfolio_id,
            workflow_type = RiskWorkflowType.EOD_RISK_REVIEW,
            **kwargs,
        )

    def collect(
        self,
        risk_id:      str,
        inputs:       Dict[str, Any],
        portfolio_id: str = "",
        **kwargs: Any,
    ) -> RiskResponse:
        """Submit a risk workflow with pre-collected inputs."""
        self._assert_running()
        request = self._factory.create_request(
            risk_id,
            portfolio_id or risk_id,
            inputs   = inputs,
            **kwargs,
        )
        return self.submit(request)

    def dispatch(
        self,
        risk_id:      str,
        portfolio_id: str = "",
        **kwargs: Any,
    ) -> RiskResponse:
        """Trigger an intraday risk dispatch."""
        return self.initialize_risk(
            risk_id,
            portfolio_id or risk_id,
            workflow_type = RiskWorkflowType.INTRADAY_RISK_REVIEW,
            **kwargs,
        )

    def publish(
        self,
        risk_id:      str,
        portfolio_id: str = "",
        **kwargs: Any,
    ) -> RiskResponse:
        """Trigger a risk snapshot publication (EOD)."""
        return self.initialize_risk(
            risk_id,
            portfolio_id or risk_id,
            workflow_type = RiskWorkflowType.EOD_RISK_REVIEW,
            **kwargs,
        )

    # ==================================================================
    # Query
    # ==================================================================

    def query(self, **filters: Any) -> List[RiskPipeline]:
        """Query pipelines matching the supplied keyword filters."""
        self._assert_running()
        return self._registry.query(**filters)

    # ==================================================================
    # Validation
    # ==================================================================

    def validate(self, request: RiskRequest):
        """Run validation checks and return RiskEngineValidationResult."""
        self._assert_running()
        return self._validator.validate_request(request)

    # ==================================================================
    # Observability
    # ==================================================================

    def health(self) -> Dict[str, Any]:
        """Return the current health report."""
        return self._health_rp.report(self._session_manager, self._dispatcher)

    def status(self) -> RiskEngineStatus:
        """Return an immutable engine status snapshot."""
        return RiskEngineStatus(
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
        """Register the Risk Policy Framework (M3)."""
        self._dispatcher.register_policy_framework(framework)

    def register_assessment_framework(self, framework: Callable) -> None:
        """Register the Risk Assessment & Optimization Framework (M4)."""
        self._dispatcher.register_assessment_framework(framework)

    # ==================================================================
    # Listener management
    # ==================================================================

    def add_listener(self, fn: Callable) -> None:
        """Register a risk-engine event listener."""
        with self._listeners_lock:
            if not any(l is fn for l in self._listeners):
                self._listeners.append(fn)

    def remove_listener(self, fn: Callable) -> None:
        """Unregister a risk-engine event listener."""
        with self._listeners_lock:
            self._listeners = [l for l in self._listeners if l is not fn]

    def _dispatch_event(self, event) -> None:
        with self._listeners_lock:
            snapshot = list(self._listeners)
        for fn in snapshot:
            try:
                fn(event)
            except Exception:  # noqa: BLE001
                pass
