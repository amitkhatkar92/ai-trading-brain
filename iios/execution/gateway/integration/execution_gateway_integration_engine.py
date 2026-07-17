"""iios/execution/gateway/integration/execution_gateway_integration_engine.py
==================================================
ExecutionGatewayIntegrationEngine — the ONLY public interface
to the Execution Gateway subsystem.

Responsibilities
----------------
  * Initialize, start, and stop all five gateway components.
  * Accept integration requests via submit().
  * Coordinate the eight-step gateway workflow (delegated to manager).
  * Publish GatewayIntegrationSnapshots.
  * Expose health, status, statistics, and history.
  * Fire domain events to registered listeners.

Non-responsibilities
--------------------
  * No routing algorithms.
  * No broker communication.
  * No order execution.
  * No business-logic duplication.

Usage
-----
  engine = ExecutionGatewayIntegrationEngine()
  engine.initialize()
  engine.start()

  ctx = make_integration_context(
      "EX-001", "ORD-001", "PORT-A", "STRAT-1",
      symbol="RELIANCE", side="BUY", quantity=50,
  )
  request  = make_integration_request(ctx, engine.integration_id)
  response = engine.submit(request)

  snap  = engine.snapshot()
  stats = engine.statistics()
  engine.stop()

C6 Execution Intelligence — Phase 5, Module 6
"""
from __future__ import annotations

import threading
import time
import uuid
from typing import Any, Callable, Dict, List, Optional

from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import (
    ACTOR_INTEGRATION_ENGINE,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_REQUESTS,
    INTEGRATION_SYSTEM_ID,
    VERSION,
    ComponentHealth,
    IntegrationOutcome,
    IntegrationRequestStatus,
)
from .exceptions import (
    IntegrationNotRunningError,
    SubsystemNotInitializedError,
)
from .gateway_component_factory import GatewayComponentFactory
from .gateway_component_registry import GatewayComponentRegistry
from .gateway_integration_context import (
    GatewayIntegrationContext,
    make_integration_context,
)
from .gateway_integration_events import (
    IntegrationEvent,
    make_subsystem_initialized_event,
    make_subsystem_started_event,
    make_subsystem_stopped_event,
)
from .gateway_integration_health import (
    GatewayIntegrationHealthMonitor,
    IntegrationHealthReport,
)
from .gateway_integration_history import GatewayIntegrationHistory
from .gateway_integration_manager import GatewayIntegrationManager
from .gateway_integration_registry import GatewayIntegrationRegistry
from .gateway_integration_request import (
    GatewayIntegrationRequest,
    make_integration_request,
)
from .gateway_integration_response import GatewayIntegrationResponse
from .gateway_integration_snapshot import GatewayIntegrationSnapshot
from .gateway_integration_statistics import GatewayIntegrationStatistics
from .gateway_integration_status import GatewayIntegrationStatus
from .gateway_integration_validation import (
    GatewayIntegrationValidationResult,
    GatewayIntegrationValidator,
)

_log   = get_logger(__name__, engine_id=INTEGRATION_SYSTEM_ID)
_audit = get_audit_logger(__name__, engine_id=INTEGRATION_SYSTEM_ID)


class ExecutionGatewayIntegrationEngine(LifecycleAwareMixin):
    """
    Primary public API for the Execution Gateway subsystem.

    This is the ONLY entry point future modules should use.
    """

    SYSTEM_ID = INTEGRATION_SYSTEM_ID
    VERSION   = VERSION

    def __init__(
        self,
        max_requests:   int = DEFAULT_MAX_REQUESTS,
        max_history:    int = DEFAULT_MAX_HISTORY,
        max_brokers:    int = 20,
        max_policies:   int = 50,
        max_candidates: int = 100,
        max_snapshots:  int = 10_000,
        max_cache_size: int = 500,
    ) -> None:
        super().__init__()
        self._integration_id = str(uuid.uuid4())

        self._max_requests  = max_requests
        self._max_history   = max_history
        self._max_brokers   = max_brokers
        self._max_policies  = max_policies
        self._max_candidates = max_candidates
        self._max_snapshots  = max_snapshots
        self._max_cache_size = max_cache_size

        # Core components
        self._components:   Optional[GatewayComponentRegistry] = None
        self._manager:      Optional[GatewayIntegrationManager] = None
        self._initialized:  bool = False

        # Integration-level infrastructure
        self._registry  = GatewayIntegrationRegistry(max_requests=max_requests)
        self._history   = GatewayIntegrationHistory(
            max_requests=max_history,
            max_responses=max_history,
            max_events=max_history,
        )
        self._stats     = GatewayIntegrationStatistics()
        self._validator = GatewayIntegrationValidator()
        self._health_monitor = GatewayIntegrationHealthMonitor()
        self._lock      = threading.RLock()

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def integration_id(self) -> str:
        return self._integration_id

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def initialize(self, components: Optional[GatewayComponentRegistry] = None) -> None:
        """
        Wire all five gateway components.

        If ``components`` is None, GatewayComponentFactory creates
        a default set with this engine's configured limits.
        """
        with self._lock:
            if components is not None:
                self._components = components
            else:
                self._components = GatewayComponentFactory.create_all(
                    max_requests=self._max_requests,
                    max_history=self._max_history,
                    max_brokers=self._max_brokers,
                    max_policies=self._max_policies,
                    max_candidates=self._max_candidates,
                    max_snapshots=self._max_snapshots,
                    max_cache_size=self._max_cache_size,
                )
            self._manager = GatewayIntegrationManager(
                components=self._components,
                registry=self._registry,
                history=self._history,
                statistics=self._stats,
                integration_id=self._integration_id,
            )
            self._initialized = True

        event = make_subsystem_initialized_event(self._integration_id)
        self._history.append_event(event)
        _log.info(
            "ExecutionGatewayIntegrationEngine initialized.",
            integration_id=self._integration_id,
            version=VERSION,
        )

    def _on_start(self) -> None:
        if not self._initialized:
            self.initialize()

        self._components.start_all()

        _audit.log_lifecycle_event(
            INTEGRATION_SYSTEM_ID,
            EngineState.STOPPED,
            EngineState.RUNNING,
            VERSION,
        )

        event = make_subsystem_started_event(self._integration_id)
        self._history.append_event(event)
        _log.info(
            "ExecutionGatewayIntegrationEngine started.",
            integration_id=self._integration_id,
        )

    def _on_stop(self) -> None:
        _audit.log_lifecycle_event(
            INTEGRATION_SYSTEM_ID,
            EngineState.RUNNING,
            EngineState.STOPPED,
            VERSION,
        )
        if self._components:
            self._components.stop_all()

        event = make_subsystem_stopped_event(self._integration_id)
        self._history.append_event(event)
        _log.info(
            "ExecutionGatewayIntegrationEngine stopped.",
            integration_id=self._integration_id,
            completed=self._stats.requests_completed,
        )

    # ── Public API ────────────────────────────────────────────────────────────

    def submit(
        self, request: GatewayIntegrationRequest
    ) -> GatewayIntegrationResponse:
        """
        Submit a gateway integration request.

        Requires RUNNING state.  Returns a GatewayIntegrationResponse.

        Raises IntegrationNotRunningError when not running.
        """
        self._guard_running()
        return self._manager.execute(request)

    def query(
        self, execution_id: str
    ) -> List[GatewayIntegrationResponse]:
        """Return all responses for the given execution_id."""
        return self._registry.responses_for_execution(execution_id)

    def validate(
        self, request: GatewayIntegrationRequest
    ) -> GatewayIntegrationValidationResult:
        """Validate a request without submitting it."""
        return self._validator.validate_request(request)

    def health(self) -> IntegrationHealthReport:
        """Return a health report for all five gateway components."""
        if not self._initialized or self._components is None:
            from .gateway_integration_health import ComponentHealthRecord
            return IntegrationHealthReport(
                overall_health=ComponentHealth.OFFLINE,
                components=(),
            )
        with self._lock:
            self._stats.record_health_check()
        return self._health_monitor.check(self._components)

    def status(self) -> GatewayIntegrationStatus:
        """Return a lightweight status summary."""
        lc_state = self.lifecycle_state().value
        is_running = self.lifecycle_state() == EngineState.RUNNING

        completed = self._registry.completed_count
        failed    = self._registry.failed_count
        pending   = self._registry.pending_count

        health_report = self.health()
        healthy_count = sum(
            1 for c in health_report.components
            if c.health == ComponentHealth.HEALTHY
        )
        return GatewayIntegrationStatus(
            integration_id=self._integration_id,
            lifecycle_state=lc_state,
            is_running=is_running,
            is_initialized=self._initialized,
            component_count=len(health_report.components),
            healthy_component_count=healthy_count,
            overall_health=health_report.overall_health,
            pending_requests=pending,
            completed_requests=completed,
            failed_requests=failed,
            statistics_summary=self._stats.to_dict(),
        )

    def statistics(self) -> GatewayIntegrationStatistics:
        """Return a copy of the current integration statistics."""
        with self._lock:
            return self._stats.copy()

    def snapshot(self) -> GatewayIntegrationSnapshot:
        """Return an immutable snapshot of the subsystem state."""
        health_report = self.health()

        def _comp_state(attr: str) -> str:
            try:
                comp = getattr(self._components, attr)
                return comp.lifecycle_state().value
            except Exception:
                return "UNKNOWN"

        lc_state  = _comp_state("lifecycle")
        eng_state = _comp_state("engine")
        rt_state  = _comp_state("routing_engine")
        bm_state  = _comp_state("broker_manager")
        ss_state  = _comp_state("snapshot_store")

        return GatewayIntegrationSnapshot(
            snapshot_id=str(uuid.uuid4()),
            integration_id=self._integration_id,
            lifecycle_state=lc_state,
            engine_state=eng_state,
            routing_state=rt_state,
            broker_layer_state=bm_state,
            snapshot_store_state=ss_state,
            overall_health=health_report.overall_health,
            component_health=health_report.component_health_map,
            pending_requests=self._registry.pending_count,
            completed_requests=self._registry.completed_count,
            failed_requests=self._registry.failed_count,
            total_requests=self._registry.request_count,
            statistics_summary=self._stats.to_dict(),
        )

    def history(self) -> GatewayIntegrationHistory:
        """Return the integration history (live reference)."""
        return self._history

    # ── Event listeners ───────────────────────────────────────────────────────

    def add_event_listener(
        self, listener: Callable[[IntegrationEvent], None]
    ) -> None:
        if self._manager:
            self._manager.add_event_listener(listener)

    def remove_event_listener(
        self, listener: Callable[[IntegrationEvent], None]
    ) -> None:
        if self._manager:
            self._manager.remove_event_listener(listener)

    # ── Component registration (post-initialize overrides) ────────────────────

    def register_lifecycle(self, lifecycle) -> None:
        self._ensure_initialized()
        self._components.register_lifecycle(lifecycle)

    def register_engine(self, engine) -> None:
        self._ensure_initialized()
        self._components.register_engine(engine)

    def register_broker_manager(self, broker_manager) -> None:
        self._ensure_initialized()
        self._components.register_broker_manager(broker_manager)

    def register_routing_engine(self, routing_engine) -> None:
        self._ensure_initialized()
        self._components.register_routing_engine(routing_engine)

    def register_snapshot_store(self, snapshot_store) -> None:
        self._ensure_initialized()
        self._components.register_snapshot_store(snapshot_store)

    # ── Guards ────────────────────────────────────────────────────────────────

    def _guard_running(self) -> None:
        if self.lifecycle_state() != EngineState.RUNNING:
            raise IntegrationNotRunningError()

    def _ensure_initialized(self) -> None:
        if not self._initialized:
            raise SubsystemNotInitializedError()
