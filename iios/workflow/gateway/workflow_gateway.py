"""
workflow_gateway.py — iios.workflow.gateway
--------------------------------------------
WorkflowGateway — THE ONLY public entry point for Enterprise
Workflow & Process Orchestration.

External IIOS modules MUST NOT directly access:
  - Workflow Lifecycle (M1)
  - Workflow Engine (M2)
  - Workflow Governance Policy Framework (M3)
  - Workflow Orchestration Framework (M4)
  - Workflow Snapshot (M5)

ALL communication MUST occur through this gateway.

Public API:
  initialize()   start()       stop()        restart()
  health()       status()      statistics()  snapshot()
  history()      validate()    submit()
  query()        cancel()      retry()

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 6
"""
from __future__ import annotations

import time
import threading
from typing import Any, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import (
    DEFAULT_GATEWAY_ID,
    GatewayEventType,
    GatewayRequestType,
    GatewayState,
    GATEWAY_VERSION,
    VERSION,
)
from .exceptions import (
    WorkflowGatewayNotInitializedError,
    WorkflowGatewayNotRunningError,
    WorkflowGatewayValidationError,
)
from .workflow_gateway_context import WorkflowGatewayContext
from .workflow_gateway_dispatcher import WorkflowGatewayDispatcher
from .workflow_gateway_events import WorkflowGatewayEvent, WorkflowGatewayEventBus
from .workflow_gateway_factory import WorkflowGatewayFactory
from .workflow_gateway_health import WorkflowHealthSummary
from .workflow_gateway_history import WorkflowGatewayHistory, WorkflowGatewayHistoryRecord
from .workflow_gateway_manager import WorkflowGatewayManager
from .workflow_gateway_registry import WorkflowGatewayRegistry
from .workflow_gateway_request import WorkflowGatewayRequest
from .workflow_gateway_response import WorkflowGatewayResponse
from .workflow_gateway_router import WorkflowGatewayRouter
from .workflow_gateway_statistics import WorkflowGatewayStatistics, WorkflowStatistics
from .workflow_gateway_status import WorkflowStatus
from .workflow_gateway_validation import GatewayValidationResult, WorkflowGatewayValidation

_log = get_logger(__name__)


class WorkflowGateway:
    """
    Enterprise Workflow Gateway — the ONLY public entry point for
    Enterprise Workflow & Process Orchestration (C16).

    Coordinates:
      M1 — Workflow Lifecycle
      M2 — Workflow Engine
      M3 — Workflow Governance Policy Framework
      M4 — Workflow Orchestration Framework
      M5 — Workflow Snapshot

    Performs NO execution, governance evaluation, lifecycle management,
    orchestration, or business processing.

    Thread-safe.
    """

    def __init__(
        self,
        gateway_id:  str                                 = DEFAULT_GATEWAY_ID,
        *,
        manager:     Optional[WorkflowGatewayManager]   = None,
        validator:   Optional[WorkflowGatewayValidation] = None,
        dispatcher:  Optional[WorkflowGatewayDispatcher] = None,
        router:      Optional[WorkflowGatewayRouter]     = None,
        registry:    Optional[WorkflowGatewayRegistry]   = None,
        event_bus:   Optional[WorkflowGatewayEventBus]   = None,
    ) -> None:
        self._gateway_id = gateway_id
        self._manager    = manager    or WorkflowGatewayManager(gateway_id=gateway_id)
        self._validator  = validator  or WorkflowGatewayValidation()
        self._router     = router     or WorkflowGatewayRouter()
        self._dispatcher = dispatcher or WorkflowGatewayDispatcher(router=self._router)
        self._registry   = registry   or WorkflowGatewayRegistry()
        self._event_bus  = event_bus  or self._manager.event_bus
        self._lock       = threading.Lock()

        _log.info(
            f"WorkflowGateway created: id={self._gateway_id!r} "
            f"version={VERSION!r} gateway_version={GATEWAY_VERSION!r}"
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # Lifecycle API
    # ═══════════════════════════════════════════════════════════════════════════

    def initialize(self) -> None:
        """Initialize the gateway and all M1–M5 components."""
        self._manager.initialize()

    def start(self) -> None:
        """Start the gateway — begin accepting requests."""
        self._manager.start()

    def stop(self) -> None:
        """Stop the gateway gracefully."""
        self._manager.stop()

    def restart(self) -> None:
        """Restart the gateway — re-creates all M1–M5 components."""
        self._manager.restart()

    # ═══════════════════════════════════════════════════════════════════════════
    # Observability API
    # ═══════════════════════════════════════════════════════════════════════════

    def health(self) -> WorkflowHealthSummary:
        """Return a point-in-time health summary for the gateway and all components."""
        return self._manager.health_summary()

    def status(self) -> WorkflowStatus:
        """Return a point-in-time operational status of the gateway."""
        return self._manager.status_snapshot()

    def statistics(self) -> WorkflowStatistics:
        """Return accumulated gateway statistics."""
        return self._manager.stats.report()

    def snapshot(self, workflow_id: str = "") -> Optional[Any]:
        """
        Return the latest WorkflowSnapshot for a workflow, or None.

        If workflow_id is empty, returns None (no global snapshot concept).
        """
        if not workflow_id:
            return None
        snap_factory = self._manager.component_registry.get_component_or_none(
            "snapshot_factory"
        )
        if snap_factory is None:
            return None
        from iios.workflow.snapshot import ExecutionStatus
        return snap_factory.create_completed(
            workflow_id,
            workflow_id,
        )

    def history(self, n: int = 20) -> List[WorkflowGatewayHistoryRecord]:
        """Return the N most recent gateway history records."""
        return self._manager.history.recent(n)

    # ═══════════════════════════════════════════════════════════════════════════
    # Request API
    # ═══════════════════════════════════════════════════════════════════════════

    def validate(self, request: WorkflowGatewayRequest) -> GatewayValidationResult:
        """
        Validate a gateway request without submitting it.

        Returns a GatewayValidationResult — never raises.
        """
        return self._validator.validate_request(request)

    def submit(self, request: WorkflowGatewayRequest) -> WorkflowGatewayResponse:
        """
        Submit a workflow for enterprise execution.

        This is the primary entry point for workflow submission.
        The gateway coordinates M1-M5 to fulfil the request.

        Returns:
            WorkflowGatewayResponse — always, even on error.
        """
        return self._process(request)

    def query(self, workflow_id: str, *, correlation_id: str = "") -> WorkflowGatewayResponse:
        """
        Query the current state of a workflow.

        Returns:
            WorkflowGatewayResponse — always, even on error.
        """
        request = WorkflowGatewayFactory.create_query_request(
            workflow_id,
            correlation_id = correlation_id,
        )
        return self._process(request)

    def cancel(self, workflow_id: str, *, correlation_id: str = "") -> WorkflowGatewayResponse:
        """
        Cancel an active workflow.

        Returns:
            WorkflowGatewayResponse — always, even on error.
        """
        request = WorkflowGatewayFactory.create_cancel_request(
            workflow_id,
            correlation_id = correlation_id,
        )
        return self._process(request)

    def retry(self, workflow_id: str, *, correlation_id: str = "", payload: Optional[Dict[str, Any]] = None) -> WorkflowGatewayResponse:
        """
        Retry a previously submitted workflow.

        Returns:
            WorkflowGatewayResponse — always, even on error.
        """
        request = WorkflowGatewayFactory.create_retry_request(
            workflow_id,
            correlation_id = correlation_id,
            payload        = payload,
        )
        return self._process(request)

    # ═══════════════════════════════════════════════════════════════════════════
    # Internal coordination
    # ═══════════════════════════════════════════════════════════════════════════

    def _process(self, request: WorkflowGatewayRequest) -> WorkflowGatewayResponse:
        """
        Full gateway processing pipeline:

          1. Guard — gateway must be RUNNING
          2. Validate request
          3. Create context
          4. Dispatch to subsystems (M1–M5 coordination)
          5. Validate response
          6. Record history + statistics + events
          7. Register response
          8. Return response
        """
        t0 = time.monotonic()

        # ── 1. Guard ──────────────────────────────────────────────────────────
        if not self._manager.is_running:
            _log.warning(
                f"Gateway: request={request.request_id!r} rejected — gateway not running"
            )
            latency = round((time.monotonic() - t0) * 1000, 3)
            resp    = WorkflowGatewayResponse.rejected_for(
                request,
                reason             = "Gateway is not running",
                gateway_latency_ms = latency,
            )
            self._manager.stats.record_request(
                rejected   = True,
                response_ms = latency,
            )
            return resp

        # ── 2. Validate request ───────────────────────────────────────────────
        val_result = self._validator.validate_request(request)
        if not val_result.valid:
            latency = round((time.monotonic() - t0) * 1000, 3)
            resp    = WorkflowGatewayResponse.rejected_for(
                request,
                reason             = f"Validation failed: {val_result.issues}",
                gateway_latency_ms = latency,
            )
            self._manager.stats.record_request(
                rejected    = True,
                response_ms = latency,
            )
            return resp

        # ── 3. Create context ─────────────────────────────────────────────────
        context = WorkflowGatewayContext.create(
            request    = request,
            gateway_id = self._gateway_id,
        )

        # ── 4. Dispatch ───────────────────────────────────────────────────────
        self._manager.increment_active()
        try:
            self._emit(GatewayEventType.WORKFLOW_SUBMITTED, request.workflow_id)
            response = self._dispatcher.dispatch(
                request    = request,
                context    = context,
                components = self._manager.component_registry,
            )
        finally:
            self._manager.decrement_active()

        # ── 5. Record ─────────────────────────────────────────────────────────
        latency = round((time.monotonic() - t0) * 1000, 3)
        self._manager.stats.record_request(
            success     = response.is_success,
            rejected    = response.is_rejected,
            response_ms = latency,
            processing_ms = response.processing_time_ms,
        )

        if response.is_success:
            self._emit(GatewayEventType.WORKFLOW_COMPLETED, request.workflow_id)
            if response.snapshot_id:
                self._manager.stats.record_snapshot_published()
                self._emit(GatewayEventType.SNAPSHOT_PUBLISHED, request.workflow_id)
            if request.request_type == GatewayRequestType.CANCEL:
                self._emit(GatewayEventType.WORKFLOW_CANCELLED, request.workflow_id)
            elif request.request_type == GatewayRequestType.RETRY:
                self._emit(GatewayEventType.WORKFLOW_RETRIED, request.workflow_id)

        if response.is_success:
            self._manager.stats.record_workflow_execution()

        # ── 6. History + registry ─────────────────────────────────────────────
        self._manager.history.record(request, response)
        self._registry.register(response)

        return response

    def _emit(self, event_type: GatewayEventType, workflow_id: str = "") -> None:
        evt = WorkflowGatewayEvent.create(
            event_type,
            gateway_id  = self._gateway_id,
            workflow_id = workflow_id,
        )
        self._event_bus.emit(evt)
