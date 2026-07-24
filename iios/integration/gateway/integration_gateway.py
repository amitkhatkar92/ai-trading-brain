"""
integration_gateway.py — iios.integration.gateway
---------------------------------------------------
IntegrationGateway — the ONLY public entry point for the Enterprise
Integration & Connectivity subsystem.

Public API (13 methods):
  initialize()   start()       stop()         restart()
  health()       status()      statistics()   snapshot()
  history()      validate()    submit()       query()
  connect()      disconnect()

The gateway coordinates — it does NOT implement lifecycle management,
governance evaluation, connector execution, protocol logic, or any
business processing.

Thread-safe.  Enterprise-grade.

C15 Enterprise Integration & Connectivity — Phase 1, Module 6
"""
from __future__ import annotations

import time
import threading
import uuid
from typing import Any, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import (
    ACTOR_GATEWAY,
    ACTOR_SYSTEM,
    DEFAULT_GATEWAY_ID,
    DEFAULT_MAX_ACTIVE_REQUESTS,
    GATEWAY_ID_PREFIX,
    GatewayComponentType,
    GatewayEventType,
    GatewayOperationType,
    GatewayResponseStatus,
    GatewayState,
    GatewayWorkflowStep,
)
from .exceptions import (
    GatewayCapacityError,
    GatewayComponentError,
    GatewayEngineError,
    GatewayGovernanceError,
    GatewayLifecycleError,
    GatewayNotReadyError,
    GatewayRequestValidationError,
    GatewayServicesError,
    GatewaySnapshotError,
    GatewayWorkflowError,
    IntegrationGatewayError,
)
from .integration_component_registry import IntegrationComponentRegistry
from .integration_gateway_context import IntegrationGatewayContext
from .integration_gateway_dispatcher import IntegrationGatewayDispatcher
from .integration_gateway_events import IntegrationGatewayEventBus
from .integration_gateway_health import (
    IntegrationGatewayHealth,
    IntegrationHealthSummary,
)
from .integration_gateway_history import (
    GatewayHistoryEntry,
    IntegrationGatewayHistory,
)
from .integration_gateway_registry import IntegrationGatewayRegistry
from .integration_gateway_request import IntegrationGatewayRequest
from .integration_gateway_response import IntegrationGatewayResponse
from .integration_gateway_router import IntegrationGatewayRouter
from .integration_gateway_statistics import (
    IntegrationGatewayStatistics,
    IntegrationStatistics,
)
from .integration_gateway_status import (
    IntegrationGatewayStatusReport,
    IntegrationGatewayStatusTracker,
)
from .integration_gateway_validation import (
    GatewayValidationReport,
    IntegrationGatewayValidation,
)

_log = get_logger(__name__)


class IntegrationGateway:
    """
    Enterprise Integration Gateway.

    Stable public entry point for all Enterprise Integration &
    Connectivity operations.  Coordinates the five subsystem components
    (Lifecycle, Engine, Policies, Services, Snapshot) without
    implementing any of their responsibilities.
    """

    def __init__(
        self,
        gateway_id:         str                                       = DEFAULT_GATEWAY_ID,
        component_registry: Optional[IntegrationComponentRegistry]   = None,
        validator:          Optional[IntegrationGatewayValidation]   = None,
        router:             Optional[IntegrationGatewayRouter]       = None,
        event_bus:          Optional[IntegrationGatewayEventBus]     = None,
        stats:              Optional[IntegrationGatewayStatistics]   = None,
        history:            Optional[IntegrationGatewayHistory]      = None,
        request_registry:   Optional[IntegrationGatewayRegistry]    = None,
        health_monitor:     Optional[IntegrationGatewayHealth]       = None,
        status_tracker:     Optional[IntegrationGatewayStatusTracker] = None,
        max_active_requests: int                                     = DEFAULT_MAX_ACTIVE_REQUESTS,
    ) -> None:
        self._gateway_id    = gateway_id
        self._comp_registry = component_registry or IntegrationComponentRegistry()
        self._validator     = validator           or IntegrationGatewayValidation()
        self._router        = router              or IntegrationGatewayRouter()
        self._event_bus     = event_bus           or IntegrationGatewayEventBus()
        self._stats         = stats               or IntegrationGatewayStatistics()
        self._history       = history             or IntegrationGatewayHistory()
        self._req_registry  = request_registry    or IntegrationGatewayRegistry(
            max_size = max_active_requests * 10
        )
        self._health        = health_monitor      or IntegrationGatewayHealth()
        self._status        = status_tracker      or IntegrationGatewayStatusTracker()
        self._dispatcher    = IntegrationGatewayDispatcher(self._comp_registry)

        self._state          = GatewayState.IDLE
        self._started_at     = time.monotonic()
        self._max_active     = max_active_requests
        self._lock           = threading.Lock()

        _log.info(f"IntegrationGateway created: id={gateway_id!r}")

    # ════════════════════════════════════════════════════════════════════
    # Lifecycle control
    # ════════════════════════════════════════════════════════════════════

    def initialize(self) -> None:
        """
        Initialize the gateway and all registered subsystem components.

        If no components have been registered, creates defaults via
        IntegrationComponentFactory.
        Transitions state: IDLE → INITIALIZING → ACTIVE.
        """
        with self._lock:
            if self._state == GatewayState.ACTIVE:
                _log.info(f"Gateway {self._gateway_id!r} already ACTIVE — skipping initialize")
                return
            self._state = GatewayState.INITIALIZING
            self._status.update_state(GatewayState.INITIALIZING)

        try:
            # Auto-create components if none registered
            if self._comp_registry.count == 0:
                from .integration_component_factory import IntegrationComponentFactory
                components = IntegrationComponentFactory.create_all()
                for ct, comp in components.items():
                    self._comp_registry.register(ct, comp)
                    self._health.mark_healthy(ct, f"{ct.value} initialized")
                    self._status.set_component_state(ct.value, "healthy")
            else:
                for ct in self._comp_registry.available_types():
                    self._health.mark_healthy(ct, f"{ct.value} registered externally")
                    self._status.set_component_state(ct.value, "healthy")

            with self._lock:
                self._state = GatewayState.ACTIVE
                self._status.update_state(GatewayState.ACTIVE)

            self._event_bus.emit(
                GatewayEventType.GATEWAY_INITIALIZED,
                self._gateway_id,
                "",
                ACTOR_GATEWAY,
                {"component_count": self._comp_registry.count},
            )
            _log.info(
                f"Gateway {self._gateway_id!r} initialized: "
                f"components={self._comp_registry.count}"
            )
        except Exception as exc:
            with self._lock:
                self._state = GatewayState.ERROR
                self._status.update_state(GatewayState.ERROR)
            raise IntegrationGatewayError(f"Gateway initialization failed: {exc!s}") from exc

    def start(self) -> None:
        """
        Start accepting requests.  If not yet initialized, calls initialize().
        """
        with self._lock:
            if self._state == GatewayState.ACTIVE:
                return
            if self._state in (GatewayState.IDLE, GatewayState.STOPPED):
                pass  # will initialize below

        if self._state != GatewayState.ACTIVE:
            self.initialize()

        self._started_at = time.monotonic()
        self._event_bus.emit(
            GatewayEventType.GATEWAY_STARTED,
            self._gateway_id,
            "",
            ACTOR_GATEWAY,
            {},
        )
        _log.info(f"Gateway {self._gateway_id!r} started")

    def stop(self) -> None:
        """
        Stop accepting new requests.  In-flight requests are allowed to complete.
        Transitions state: ACTIVE → STOPPING → STOPPED.
        """
        with self._lock:
            if self._state == GatewayState.STOPPED:
                return
            self._state = GatewayState.STOPPING
            self._status.update_state(GatewayState.STOPPING)

        self._event_bus.emit(
            GatewayEventType.GATEWAY_STOPPED,
            self._gateway_id,
            "",
            ACTOR_GATEWAY,
            {},
        )

        with self._lock:
            self._state = GatewayState.STOPPED
            self._status.update_state(GatewayState.STOPPED)
        _log.info(f"Gateway {self._gateway_id!r} stopped")

    def restart(self) -> None:
        """Stop and then re-initialize the gateway."""
        _log.info(f"Gateway {self._gateway_id!r} restarting")
        self.stop()
        with self._lock:
            self._state = GatewayState.IDLE
            self._status.update_state(GatewayState.IDLE)
        self.initialize()

    # ════════════════════════════════════════════════════════════════════
    # Observability
    # ════════════════════════════════════════════════════════════════════

    def health(self) -> IntegrationHealthSummary:
        """Return the current health summary for the gateway and all components."""
        with self._lock:
            state  = self._state
            active = self._status.active_requests

        return self._health.check(
            gateway_id      = self._gateway_id,
            gateway_state   = state,
            active_requests = active,
            uptime_seconds  = self._uptime(),
        )

    def status(self) -> IntegrationGatewayStatusReport:
        """Return a current status report."""
        return self._status.status(
            gateway_id     = self._gateway_id,
            uptime_seconds = self._uptime(),
        )

    def statistics(self) -> IntegrationStatistics:
        """Return accumulated gateway statistics."""
        return self._stats.snapshot()

    def snapshot(self) -> Any:
        """
        Return the most recent IntegrationSnapshot registered with the
        snapshot component, or None if unavailable.
        """
        snap_registry = self._comp_registry.get(GatewayComponentType.SNAPSHOT)
        if snap_registry is None:
            return None
        all_ids = snap_registry.list_ids()
        if not all_ids:
            return None
        return snap_registry.get(all_ids[-1])

    def history(self, n: int = 100) -> List[GatewayHistoryEntry]:
        """Return the most recent *n* gateway history entries."""
        return self._history.recent(n)

    # ════════════════════════════════════════════════════════════════════
    # Validation
    # ════════════════════════════════════════════════════════════════════

    def validate(
        self,
        request: IntegrationGatewayRequest,
    ) -> GatewayValidationReport:
        """
        Validate *request* against all 7 gateway checks.
        Does NOT require the gateway to be ACTIVE.
        """
        with self._lock:
            state      = self._state
            available  = self._comp_registry.available_types()

        report = self._validator.validate_request(
            request,
            gateway_state        = state,
            available_components = available,
        )
        return report

    # ════════════════════════════════════════════════════════════════════
    # Core request operations
    # ════════════════════════════════════════════════════════════════════

    def submit(
        self,
        request: IntegrationGatewayRequest,
    ) -> IntegrationGatewayResponse:
        """
        Submit a full integration request through the gateway workflow.

        Workflow:
          1. Validate request
          2. Initialize lifecycle session
          3. Execute integration engine
          4. Evaluate governance policies
          5. Execute integration services
          6. Generate + register integration snapshot
          7. Build and return gateway response

        Returns IntegrationGatewayResponse (success or failure).
        Never raises — failures are returned as a response with FAILED status.
        """
        self._guard_active(request)
        self._stats.increment_request()
        self._status.record_request(request.request_id)
        self._req_registry.register(request)

        ctx = IntegrationGatewayContext(
            request     = request,
            gateway_id  = self._gateway_id,
            gateway_state = self._state,
        )
        ctx.advance_step(GatewayWorkflowStep.REQUEST_RECEIVED)

        try:
            # ── 1. Validate ─────────────────────────────────────────
            report = self._validator.validate_request(
                request,
                gateway_state        = self._state,
                available_components = self._comp_registry.available_types(),
            )
            if not report.passed:
                errs = "; ".join(i.message for i in report.errors)
                self._stats.increment_rejected()
                resp = IntegrationGatewayResponse.rejected(
                    request_id = request.request_id,
                    operation  = request.operation,
                    gateway_state = self._state,
                    reason     = f"Validation failed: {errs}",
                    error_code = "IGW-002",
                )
                self._finalize(ctx, resp)
                return resp
            ctx.advance_step(GatewayWorkflowStep.REQUEST_VALIDATED)

            # ── 2-6. Dispatch ────────────────────────────────────────
            route = self._router.route(request)
            self._dispatcher.dispatch(ctx, route)
            ctx.advance_step(GatewayWorkflowStep.COMPLETED)

            # ── 7. Build success response ────────────────────────────
            resp = IntegrationGatewayResponse.success(
                request_id           = request.request_id,
                operation            = request.operation,
                gateway_state        = self._state,
                lifecycle_session_id = ctx.lifecycle_session_id,
                engine_request_id    = ctx.engine_request_id,
                governance_decision  = ctx.governance_decision,
                snapshot_id          = ctx.snapshot_id,
                data                 = {
                    "step_timings": ctx.step_timings,
                    "warnings":     ctx.warnings,
                },
                processing_time_ms   = ctx.elapsed_ms(),
            )
            self._stats.increment_success()
            if ctx.snapshot_id:
                self._stats.increment_snapshot_publications()

        except (
            GatewayLifecycleError,
            GatewayEngineError,
            GatewayGovernanceError,
            GatewayServicesError,
            GatewaySnapshotError,
            GatewayWorkflowError,
        ) as exc:
            resp = IntegrationGatewayResponse.failure(
                request_id           = request.request_id,
                operation            = request.operation,
                gateway_state        = self._state,
                error                = str(exc),
                error_code           = getattr(exc, "code", "IGW-003"),
                lifecycle_session_id = ctx.lifecycle_session_id,
                engine_request_id    = ctx.engine_request_id,
                governance_decision  = ctx.governance_decision,
                snapshot_id          = ctx.snapshot_id,
                processing_time_ms   = ctx.elapsed_ms(),
            )
            self._stats.increment_failed()

        except Exception as exc:
            resp = IntegrationGatewayResponse.failure(
                request_id         = request.request_id,
                operation          = request.operation,
                gateway_state      = self._state,
                error              = f"Unexpected gateway error: {exc!s}",
                error_code         = "IGW-000",
                processing_time_ms = ctx.elapsed_ms(),
            )
            self._stats.increment_failed()
            _log.info(
                f"Gateway {self._gateway_id!r} unexpected error "
                f"request={request.request_id!r} exc={exc!r}"
            )

        self._finalize(ctx, resp)
        return resp

    def query(self, request_id: str) -> Optional[IntegrationGatewayResponse]:
        """
        Retrieve a previously completed response by request_id.
        Returns None if not found.
        """
        return self._req_registry.get_response(request_id)

    def connect(self, config: Dict[str, Any]) -> bool:
        """
        Establish a new integration connection.

        Creates a CONNECT request from *config* and submits it through
        the gateway workflow.  Returns True on success.
        """
        workflow_id   = str(config.get("workflow_id",   "connect-workflow"))
        enterprise_id = str(config.get("enterprise_id", "default-enterprise"))

        request = IntegrationGatewayRequest.create(
            operation        = GatewayOperationType.CONNECT,
            workflow_id      = workflow_id,
            enterprise_id    = enterprise_id,
            connector_config = dict(config.get("connector_config", {})),
            protocol_config  = dict(config.get("protocol_config",  {})),
            auth_config      = dict(config.get("auth_config",      {})),
            endpoint_config  = dict(config.get("endpoint_config",  {})),
            metadata         = dict(config.get("metadata",         {})),
        )
        response = self.submit(request)
        return response.is_successful

    def disconnect(self, session_id: str) -> bool:
        """
        Disconnect an existing integration session.

        Creates a DISCONNECT request and submits it through the gateway.
        Returns True on success.
        """
        request = IntegrationGatewayRequest.create(
            operation     = GatewayOperationType.DISCONNECT,
            workflow_id   = f"disconnect-{session_id[:16]}",
            enterprise_id = "default-enterprise",
            session_id    = session_id,
        )
        response = self.submit(request)
        return response.is_successful

    # ════════════════════════════════════════════════════════════════════
    # Internal helpers
    # ════════════════════════════════════════════════════════════════════

    def _guard_active(self, request: IntegrationGatewayRequest) -> None:
        """Raise GatewayNotReadyError if the gateway is not ACTIVE."""
        with self._lock:
            state = self._state
        if state != GatewayState.ACTIVE:
            raise GatewayNotReadyError(
                f"Gateway {self._gateway_id!r} is not ACTIVE (state={state.value!r})"
            )

    def _finalize(
        self,
        ctx:      IntegrationGatewayContext,
        response: IntegrationGatewayResponse,
    ) -> None:
        """Record the response, update history, emit completion event."""
        # Store response in registry
        self._req_registry.set_response(ctx.request.request_id, response)
        self._status.record_completion(ctx.request.request_id)

        # Record processing and response timings
        self._stats.record_processing_time(ctx.elapsed_ms())
        self._stats.record_response_time(response.processing_time_ms)

        # History entry
        self._history.record(
            gateway_id           = self._gateway_id,
            request_id           = response.request_id,
            operation            = response.operation,
            status               = response.status,
            processing_time_ms   = response.processing_time_ms,
            lifecycle_session_id = response.lifecycle_session_id,
            snapshot_id          = response.snapshot_id,
        )

        # Event
        if response.is_successful:
            self._event_bus.emit(
                GatewayEventType.GATEWAY_COMPLETED,
                self._gateway_id,
                response.request_id,
                ACTOR_GATEWAY,
                {
                    "status":     response.status.value,
                    "snapshot_id": response.snapshot_id,
                },
            )
        else:
            self._event_bus.emit(
                GatewayEventType.GATEWAY_FAILED,
                self._gateway_id,
                response.request_id,
                ACTOR_GATEWAY,
                {
                    "error":      response.error,
                    "error_code": response.error_code,
                },
            )

    def _uptime(self) -> float:
        """Seconds since the gateway was last started."""
        return time.monotonic() - self._started_at

    # ════════════════════════════════════════════════════════════════════
    # Properties
    # ════════════════════════════════════════════════════════════════════

    @property
    def gateway_id(self) -> str:
        return self._gateway_id

    @property
    def state(self) -> GatewayState:
        with self._lock:
            return self._state

    @property
    def is_active(self) -> bool:
        with self._lock:
            return self._state == GatewayState.ACTIVE

    @property
    def component_registry(self) -> IntegrationComponentRegistry:
        return self._comp_registry

    @property
    def event_bus(self) -> IntegrationGatewayEventBus:
        return self._event_bus

    def __repr__(self) -> str:
        return (
            f"IntegrationGateway("
            f"gateway_id={self._gateway_id!r}, "
            f"state={self._state.value!r})"
        )
