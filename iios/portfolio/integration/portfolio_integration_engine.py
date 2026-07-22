"""
portfolio_integration_engine.py — iios.portfolio.integration
=============================================================
PortfolioIntegrationEngine — the ONLY public entry point into the
Portfolio Intelligence subsystem.

All external modules MUST communicate through PortfolioIntegrationEngine.
Internal components (Lifecycle, Engine, Policy, Optimization, Snapshot)
are NEVER exposed directly.

Public API
----------
initialize()   — prepare and start the integration engine.
start()        — start the engine and all subsystems.
stop()         — stop the engine and all subsystems.
restart()      — stop then start.
health()       — return health of all subsystems.
status()       — return full integration status.
statistics()   — return runtime statistics.
snapshot()     — return the latest snapshot for a portfolio.
history()      — return integration history for a portfolio.
validate()     — validate an integration request.
submit()       — submit a portfolio service request.
query()        — query published snapshots.

C10 Portfolio Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

import threading
import time
from typing import Any, Callable, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger
from iios.common.logging.audit_logger import get_audit_logger
from iios.investment.workflow.engine_lifecycle import LifecycleAwareMixin

from .constants import (
    INTEGRATION_SYSTEM_ID,
    VERSION,
    ACTOR_INTEGRATION,
    ComponentType,
    IntegrationEventType,
    IntegrationState,
)
from .exceptions import (
    IntegrationNotReadyError,
    IntegrationRequestError,
)
from .portfolio_component_factory import PortfolioComponentFactory
from .portfolio_component_registry import PortfolioComponentRegistry
from .portfolio_integration_context import IntegrationContext
from .portfolio_integration_events import (
    IntegrationEvent,
    make_portfolio_initialized,
    make_portfolio_started,
    make_portfolio_completed,
    make_portfolio_stopped,
    make_portfolio_restarted,
    make_portfolio_validated,
    make_portfolio_health_changed,
    make_snapshot_published,
)
from .portfolio_integration_health import PortfolioIntegrationHealth
from .portfolio_integration_history import PortfolioIntegrationHistory
from .portfolio_integration_manager import PortfolioIntegrationManager
from .portfolio_integration_registry import PortfolioIntegrationRegistry
from .portfolio_integration_request import PortfolioIntegrationRequest
from .portfolio_integration_response import PortfolioIntegrationResponse
from .portfolio_integration_statistics import PortfolioIntegrationStatistics
from .portfolio_integration_status import (
    IntegrationComponentStatus,
    PortfolioIntegrationStatus,
)
from .portfolio_integration_validation import (
    IntegrationValidationResult,
    PortfolioIntegrationValidator,
)

_log   = get_logger(__name__)
_audit = get_audit_logger(__name__, engine_id=INTEGRATION_SYSTEM_ID)


class PortfolioIntegrationEngine(LifecycleAwareMixin):
    """
    Institutional Portfolio Integration Engine.

    This is the ONLY public interface that external subsystems
    (Execution Intelligence, Risk Intelligence, AI Supervisor,
    Compliance, Reporting, Dashboard) use to interact with Portfolio
    Intelligence.

    The engine integrates:
    - Portfolio Lifecycle       (session management)
    - Portfolio Engine          (workflow orchestration)
    - Portfolio Policy Framework (governance)
    - Portfolio Optimization Framework (portfolio construction)
    - Portfolio Snapshot        (publication and delivery)

    Parameters
    ----------
    component_registry : Pre-built component registry (for testing /
                         dependency injection).  When None the factory
                         creates and wires all five components.
    auto_start_components : When True (default) all components are started
                            when the integration engine starts.

    Examples
    --------
    ::

        engine = PortfolioIntegrationEngine()
        engine.initialize()

        request = PortfolioIntegrationRequest.create(
            "pf-001",
            IntegrationServiceType.PORTFOLIO_CREATION,
            inputs={"portfolio_name": "NIFTY Momentum"},
        )
        response = engine.submit(request)

        if response.is_success:
            snap = response.snapshot

        engine.stop()
    """

    def __init__(
        self,
        *,
        component_registry:      Optional[PortfolioComponentRegistry] = None,
        auto_start_components:   bool = True,
    ) -> None:
        super().__init__()
        self._auto_start_components = auto_start_components
        self._component_registry    = component_registry or PortfolioComponentRegistry()
        self._factory               = PortfolioComponentFactory()
        self._statistics            = PortfolioIntegrationStatistics()
        self._int_history           = PortfolioIntegrationHistory()
        self._int_registry          = PortfolioIntegrationRegistry()
        self._health_monitor        = PortfolioIntegrationHealth()
        self._validator             = PortfolioIntegrationValidator()
        self._manager               = PortfolioIntegrationManager(
            component_registry = self._component_registry,
            statistics         = self._statistics,
        )
        self._listeners: List[Callable[[IntegrationEvent], None]] = []
        self._listener_lock = threading.Lock()
        self._started_at:   Optional[float] = None
        self._state         = IntegrationState.PENDING

    # ==================================================================
    # LifecycleAwareMixin hooks
    # ==================================================================

    def _on_start(self) -> None:
        self._state      = IntegrationState.INITIALIZING
        self._started_at = time.time()

        # Wire and start all five components if not already registered
        if self._component_registry.available_count() == 0:
            registry = self._factory.create_all()
            # Transfer registrations
            self._component_registry.register_lifecycle(registry.get_lifecycle())
            self._component_registry.register_engine(registry.get_engine())
            self._component_registry.register_policy(registry.get_policy())
            self._component_registry.register_optimization(registry.get_optimization())
            self._component_registry.register_snapshot(registry.get_snapshot_registry())

        if self._auto_start_components:
            PortfolioComponentFactory.start_all(self._component_registry)

        self._state = IntegrationState.RUNNING
        self._refresh_availability_stats()

        _audit.log_lifecycle_event(
            engine_id  = INTEGRATION_SYSTEM_ID,
            from_state = "STOPPED",
            to_state   = "RUNNING",
            version    = VERSION,
            actor      = ACTOR_INTEGRATION,
        )
        _log.info(f"PortfolioIntegrationEngine started (version={VERSION})")
        self._dispatch(make_portfolio_started("", INTEGRATION_SYSTEM_ID))

    def _on_stop(self) -> None:
        self._state = IntegrationState.STOPPING

        if self._auto_start_components:
            PortfolioComponentFactory.stop_all(self._component_registry)

        self._state = IntegrationState.STOPPED
        _audit.log_lifecycle_event(
            engine_id  = INTEGRATION_SYSTEM_ID,
            from_state = "RUNNING",
            to_state   = "STOPPED",
            version    = VERSION,
            actor      = ACTOR_INTEGRATION,
        )
        _log.info("PortfolioIntegrationEngine stopped")
        self._dispatch(make_portfolio_stopped("", INTEGRATION_SYSTEM_ID))

    # ==================================================================
    # Public lifecycle API
    # ==================================================================

    def initialize(self) -> None:
        """
        Prepare and start the integration engine (idempotent).

        Equivalent to ``start()`` for the integration engine.
        External callers may use either name.
        """
        if self.lifecycle_state().value != "running":
            self.start()
        self._dispatch(make_portfolio_initialized("", INTEGRATION_SYSTEM_ID))

    def restart(self) -> None:
        """Stop and immediately restart the engine and all subsystems."""
        if self.lifecycle_state().value == "running":
            self.stop()
        self.start()
        self._dispatch(make_portfolio_restarted("", INTEGRATION_SYSTEM_ID))
        _log.info("PortfolioIntegrationEngine restarted")

    # ==================================================================
    # Public service API
    # ==================================================================

    def submit(
        self, request: PortfolioIntegrationRequest
    ) -> PortfolioIntegrationResponse:
        """
        Submit a portfolio service request and execute the full workflow.

        Parameters
        ----------
        request : PortfolioIntegrationRequest

        Returns
        -------
        PortfolioIntegrationResponse

        Raises
        ------
        IntegrationNotReadyError   if the engine is not running.
        IntegrationRequestError    if the request is None or has no portfolio_id.
        """
        self._assert_running()
        if request is None:
            raise IntegrationRequestError(
                "request must not be None", portfolio_id=""
            )
        if not request.portfolio_id:
            raise IntegrationRequestError(
                "request.portfolio_id must not be empty", portfolio_id=""
            )

        self._statistics.record_request()
        self._int_registry.register_request(request)

        response = self._manager.execute(request)

        self._int_registry.register_response(response)
        self._int_history.record(response)

        if response.is_success and response.has_snapshot:
            self._dispatch(
                make_snapshot_published(
                    response.portfolio_id,
                    response.request_id,
                    snapshot_id = response.snapshot.snapshot_id,
                )
            )
            self._dispatch(
                make_portfolio_completed(
                    response.portfolio_id,
                    response.request_id,
                    service_type = response.service_type,
                )
            )

        return response

    def validate(
        self, request: PortfolioIntegrationRequest
    ) -> IntegrationValidationResult:
        """
        Validate an integration request without executing the workflow.

        The registry readiness check is skipped when called before
        ``initialize()``.
        """
        registry = (
            self._component_registry
            if self.lifecycle_state().value == "running"
            else None
        )
        result = self._validator.validate(request, registry)
        self._dispatch(
            make_portfolio_validated(
                request.portfolio_id,
                request.request_id,
                passed_checks = result.passed_count,
            )
        )
        return result

    def snapshot(self, portfolio_id: str) -> Optional[Any]:
        """
        Return the latest published snapshot for a portfolio.

        Returns None when no snapshot exists.
        """
        self._assert_running()
        snap_reg = self._component_registry.get_snapshot_registry()
        if snap_reg is None:
            return None
        return snap_reg.get_latest(portfolio_id)

    def history(
        self, portfolio_id: str, limit: int = 0
    ) -> List[PortfolioIntegrationResponse]:
        """Return integration response history for a portfolio."""
        return self._int_history.get_for_portfolio(portfolio_id, limit=limit)

    def query(self, **filters: Any) -> List[Any]:
        """
        Query published snapshots by field filters.

        Delegates to the snapshot registry's ``query()`` method.

        Examples::
            engine.query(portfolio_type="equity")
            engine.query(snapshot_status="published")
        """
        self._assert_running()
        snap_reg = self._component_registry.get_snapshot_registry()
        if snap_reg is None:
            return []
        return snap_reg.query(**filters)

    # ==================================================================
    # Observability
    # ==================================================================

    def health(self) -> Dict[str, Any]:
        """Return a health report for all subsystems."""
        self._assert_running()
        report = self._health_monitor.report(self._component_registry)
        return report

    def status(self) -> PortfolioIntegrationStatus:
        """Return full integration status."""
        lc   = self._health_monitor.check_lifecycle(self._component_registry)
        eng  = self._health_monitor.check_engine(self._component_registry)
        pol  = self._health_monitor.check_policy(self._component_registry)
        opt  = self._health_monitor.check_optimization(self._component_registry)
        snap = self._health_monitor.check_snapshot(self._component_registry)
        overall = self._health_monitor.overall_health([lc, eng, pol, opt, snap])
        return PortfolioIntegrationStatus(
            integration_id      = INTEGRATION_SYSTEM_ID,
            state               = self._state.value,
            lifecycle_status    = lc,
            engine_status       = eng,
            policy_status       = pol,
            optimization_status = opt,
            snapshot_status     = snap,
            overall_health      = overall,
            statistics          = self._statistics.snapshot(),
            started_at          = self._started_at or 0.0,
            captured_at         = time.time(),
            framework_version   = VERSION,
        )

    def statistics(self) -> Dict[str, Any]:
        """Return current runtime statistics."""
        return self._statistics.snapshot()

    # ==================================================================
    # Event listeners
    # ==================================================================

    def add_listener(
        self, listener: Callable[[IntegrationEvent], None]
    ) -> None:
        """Register a callable that will receive all integration events."""
        with self._listener_lock:
            if listener not in self._listeners:
                self._listeners.append(listener)

    def remove_listener(
        self, listener: Callable[[IntegrationEvent], None]
    ) -> None:
        """Remove a previously registered listener."""
        with self._listener_lock:
            try:
                self._listeners.remove(listener)
            except ValueError:
                pass

    # ==================================================================
    # Private helpers
    # ==================================================================

    def _assert_running(self) -> None:
        if self.lifecycle_state().value != "running":
            raise IntegrationNotReadyError()

    def _dispatch(self, event: IntegrationEvent) -> None:
        with self._listener_lock:
            listeners = list(self._listeners)
        for fn in listeners:
            try:
                fn(event)
            except Exception:
                pass

    def _refresh_availability_stats(self) -> None:
        reg = self._component_registry
        lc  = reg.get_lifecycle()
        eng = reg.get_engine()
        pol = reg.get_policy()
        opt = reg.get_optimization()
        snap = reg.get_snapshot_registry()
        self._statistics.set_component_availability(
            lifecycle    = lc is not None,
            engine       = eng is not None,
            policy       = pol is not None,
            optimization = opt is not None,
            snapshot     = snap is not None,
        )
