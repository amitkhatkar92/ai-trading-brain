"""
risk_integration_engine.py — iios.risk.integration
====================================================
Primary public façade for the C11 Risk Intelligence subsystem.

RiskIntegrationEngine is a LifecycleAwareMixin that:
  - Wires together the M1-M5 subsystem components
  - Delegates all workflow processing to RiskIntegrationManager
  - Exposes a clean, stable API for all upstream callers

All downstream subsystems MUST communicate through this engine.
RiskSnapshot (M5) is the ONLY published artefact.
No internal component may be accessed directly.

C11 Risk Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Optional

from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import LifecycleAwareMixin

from .constants import (
    COMPONENT_ASSESSMENT,
    COMPONENT_ENGINE,
    COMPONENT_LIFECYCLE,
    COMPONENT_POLICIES,
    COMPONENT_SNAPSHOT,
    INTEGRATION_SYSTEM_ID,
    ComponentStatus,
    HealthStatus,
    VERSION,
)
from .exceptions import (
    RiskIntegrationNotRunningError,
    RiskIntegrationRequestError,
)
from .risk_component_factory import RiskComponentFactory
from .risk_component_registry import RiskComponentRegistry
from .risk_integration_events import (
    make_integration_started,
    make_integration_stopped,
)
from .risk_integration_health import RiskIntegrationHealth, RiskIntegrationHealthReport
from .risk_integration_history import RiskIntegrationHistory
from .risk_integration_manager import RiskIntegrationManager
from .risk_integration_registry import RiskIntegrationRegistry
from .risk_integration_request import RiskIntegrationRequest
from .risk_integration_response import RiskIntegrationResponse
from .risk_integration_snapshot import RiskIntegrationSnapshot
from .risk_integration_statistics import RiskIntegrationStatistics
from .risk_integration_status import RiskIntegrationStatus
from .risk_integration_validation import (
    IntegrationValidationResult,
    RiskIntegrationValidator,
)

_log      = get_logger(__name__)
_audit    = get_audit_logger(__name__)


class RiskIntegrationEngine(LifecycleAwareMixin):
    """
    Enterprise façade for the complete C11 Risk Intelligence subsystem.

    **Usage**::

        engine = RiskIntegrationEngine()
        engine.initialize()
        engine.start()

        response = engine.submit(request)

        engine.stop()

    Parameters
    ----------
    component_registry :
        Pre-populated component registry.  If *None*, defaults are created
        via :class:`~.risk_component_factory.RiskComponentFactory`.
    manager :
        Pre-built workflow coordinator.  Created automatically if *None*.
    validator :
        Injected validator.  Created automatically if *None*.
    statistics :
        Injected statistics tracker.  Created automatically if *None*.
    history :
        Injected history store.  Created automatically if *None*.
    registry :
        Injected request/response registry.  Created automatically if *None*.
    health_reporter :
        Injected health reporter.  Created automatically if *None*.
    environment :
        Deployment environment tag.  Passed to the component factory.
    """

    SYSTEM_ID: str = INTEGRATION_SYSTEM_ID
    VERSION:   str = VERSION

    def __init__(
        self,
        component_registry: Optional[RiskComponentRegistry]     = None,
        manager:            Optional[RiskIntegrationManager]    = None,
        validator:          Optional[RiskIntegrationValidator]  = None,
        statistics:         Optional[RiskIntegrationStatistics] = None,
        history:            Optional[RiskIntegrationHistory]    = None,
        registry:           Optional[RiskIntegrationRegistry]   = None,
        health_reporter:    Optional[RiskIntegrationHealth]     = None,
        environment:        str                                  = "production",
    ) -> None:
        super().__init__()
        self._environment  = environment
        self._initialized  = False
        self._started_at   = 0.0
        self._engine_id    = self.SYSTEM_ID

        # Build defaults if not injected
        self._components   = component_registry or self._create_default_registry()
        self._stats        = statistics or RiskIntegrationStatistics()
        self._history      = history    or RiskIntegrationHistory()
        self._registry     = registry   or RiskIntegrationRegistry()
        self._validator    = validator  or RiskIntegrationValidator()
        self._health       = health_reporter or RiskIntegrationHealth(self._engine_id)
        self._manager      = manager or RiskIntegrationManager(
            component_registry = self._components,
            validator          = self._validator,
            registry           = self._registry,
            statistics         = self._stats,
            history            = self._history,
            engine_id          = self._engine_id,
        )

    # ------------------------------------------------------------------
    # Lifecycle hooks
    # ------------------------------------------------------------------

    def _create_default_registry(self) -> RiskComponentRegistry:
        try:
            return RiskComponentFactory(self._environment).create_default_registry()
        except Exception as exc:
            _log.warning(f"RiskIntegrationEngine: component factory error — {exc}")
            return RiskComponentRegistry()

    def _on_start(self) -> None:
        self._started_at = time.time()
        self._stats.record_started()

        # Start available subsystem components
        for key in [COMPONENT_LIFECYCLE, COMPONENT_ENGINE, COMPONENT_POLICIES,
                    COMPONENT_ASSESSMENT, COMPONENT_SNAPSHOT]:
            comp = self._components.get_or_none(key)
            if comp is None:
                continue
            if hasattr(comp, "start"):
                try:
                    comp.start()
                except Exception as exc:
                    _log.warning(f"RiskIntegrationEngine: failed to start {key} — {exc}")
                    self._components.set_status(key, ComponentStatus.DEGRADED)

        _audit.log_lifecycle_event(
            self._engine_id,
            from_state = "created",
            to_state   = "running",
            version    = self.VERSION,
            actor      = self.SYSTEM_ID,
        )
        evt = make_integration_started(
            self._engine_id, "", actor=self.SYSTEM_ID, version=self.VERSION
        )
        self._history.record_event(evt)
        _log.info(f"RiskIntegrationEngine started — {self._engine_id}")

    def _on_stop(self) -> None:
        self._stats.record_stopped()

        # Stop available subsystem components in reverse order
        for key in reversed([COMPONENT_LIFECYCLE, COMPONENT_ENGINE, COMPONENT_POLICIES,
                              COMPONENT_ASSESSMENT, COMPONENT_SNAPSHOT]):
            comp = self._components.get_or_none(key)
            if comp is None:
                continue
            if hasattr(comp, "stop"):
                try:
                    comp.stop()
                except Exception as exc:
                    _log.warning(f"RiskIntegrationEngine: failed to stop {key} — {exc}")

        _audit.log_lifecycle_event(
            self._engine_id,
            from_state = "running",
            to_state   = "stopped",
            version    = self.VERSION,
            actor      = self.SYSTEM_ID,
        )
        evt = make_integration_stopped(
            self._engine_id, "", actor=self.SYSTEM_ID
        )
        self._history.record_event(evt)
        _log.info(f"RiskIntegrationEngine stopped — {self._engine_id}")

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """
        Pre-start initialization.

        Must be called before :meth:`start`.  Idempotent.
        """
        if self._initialized:
            _log.debug("RiskIntegrationEngine: already initialized")
            return
        self._stats.record_initialized()
        self._initialized = True
        _log.debug(f"RiskIntegrationEngine initialized — {self._engine_id}")

    # ------------------------------------------------------------------
    # Lifecycle (inherited start / stop)
    # ------------------------------------------------------------------

    def restart(self) -> None:
        """Stop and re-start the engine."""
        self.stop()
        self.initialize()
        self.start()

    # ------------------------------------------------------------------
    # Guard helper
    # ------------------------------------------------------------------

    def _assert_running(self) -> None:
        if self.lifecycle_state().value != "running":
            raise RiskIntegrationNotRunningError(
                f"RiskIntegrationEngine is not running (state="
                f"{self.lifecycle_state().value!r})"
            )

    # ------------------------------------------------------------------
    # Public Observability API
    # ------------------------------------------------------------------

    def health(self) -> RiskIntegrationHealthReport:
        """Return the current health report."""
        stats_snap    = self._stats.snapshot()
        is_running    = self.lifecycle_state().value == "running"
        return self._health.report(
            component_registry = self._components,
            is_running         = is_running,
            started_at         = self._started_at,
            requests_processed = stats_snap.get("requests_completed", 0),
            requests_failed    = stats_snap.get("requests_failed", 0),
        )

    def status(self) -> RiskIntegrationStatus:
        """Return a structured status value object."""
        snap          = self._stats.snapshot()
        health_report = self.health()
        is_running    = self.lifecycle_state().value == "running"
        uptime        = round(time.time() - self._started_at, 2) if self._started_at and is_running else 0.0
        comps         = self._components.health_summary()

        return RiskIntegrationStatus(
            engine_id            = self._engine_id,
            state                = self.lifecycle_state().value,
            health_status        = health_report.health_status,
            is_running           = is_running,
            requests_total       = snap.get("requests_received", 0),
            requests_completed   = snap.get("requests_completed", 0),
            requests_failed      = snap.get("requests_failed", 0),
            snapshots_published  = snap.get("snapshots_published", 0),
            components_available = sum(
                1 for v in comps.values()
                if v == ComponentStatus.AVAILABLE.value
            ),
            components_total     = len(comps),
            uptime_s             = uptime,
            started_at           = self._started_at,
        )

    def statistics(self) -> Dict[str, Any]:
        """Return a dict of running statistics."""
        return self._stats.snapshot()

    def snapshot(self) -> RiskIntegrationSnapshot:
        """Return a diagnostic snapshot of the integration layer."""
        stat = self.statistics()
        is_running = self.lifecycle_state().value == "running"
        uptime     = round(time.time() - self._started_at, 2) if self._started_at and is_running else 0.0
        return RiskIntegrationSnapshot.capture(
            engine_id           = self._engine_id,
            state               = self.lifecycle_state().value,
            health_status       = self.health().health_status,
            is_running          = is_running,
            requests_received   = stat.get("requests_received",   0),
            requests_completed  = stat.get("requests_completed",  0),
            requests_failed     = stat.get("requests_failed",     0),
            snapshots_published = stat.get("snapshots_published", 0),
            components          = self._components.health_summary(),
            uptime_s            = uptime,
            avg_processing_s    = stat.get("avg_processing_s", 0.0),
        )

    def history(self, n: int = 10) -> List[Any]:
        """Return the *n* most recent history artefacts (responses)."""
        return self._history.recent_responses(n)

    # ------------------------------------------------------------------
    # Validation API
    # ------------------------------------------------------------------

    def validate(self, request: RiskIntegrationRequest) -> IntegrationValidationResult:
        """Validate *request* without processing it."""
        return self._validator.validate(
            request, component_registry=self._components
        )

    # ------------------------------------------------------------------
    # Submission API
    # ------------------------------------------------------------------

    def submit(self, request: RiskIntegrationRequest) -> RiskIntegrationResponse:
        """
        Submit *request* for full integration processing.

        This is the primary entry point.

        Raises :class:`~.exceptions.RiskIntegrationNotRunningError`
        if the engine is not running.
        """
        self._assert_running()
        return self._manager.run_workflow(request)

    # ------------------------------------------------------------------
    # Query API
    # ------------------------------------------------------------------

    def query(self, request_id: str) -> Optional[RiskIntegrationResponse]:
        """
        Return the response for a previously submitted request_id,
        or *None* if not found.
        """
        return self._registry.get_response(request_id)

    # ------------------------------------------------------------------
    # Event listener API
    # ------------------------------------------------------------------

    def add_listener(self, fn: Callable) -> None:
        """Register a callable that will receive integration events."""
        self._manager.add_listener(fn)

    def remove_listener(self, fn: Callable) -> None:
        """De-register an event listener."""
        self._manager.remove_listener(fn)
