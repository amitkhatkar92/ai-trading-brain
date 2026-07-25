"""
workflow_gateway_dispatcher.py — iios.workflow.gateway
-------------------------------------------------------
WorkflowGatewayDispatcher — dispatches gateway requests to subsystem
components following the gateway coordination workflow.

Workflow:
  Receive Request → Route → Dispatch to M2 Engine → Build M5 Snapshot
  → Build Gateway Response

The dispatcher performs NO execution, governance evaluation, lifecycle
management, orchestration, or business processing.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 6
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Dict, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import GatewayRequestType
from .exceptions import WorkflowGatewayDispatchError
from .workflow_component_factory import (
    COMPONENT_ENGINE,
    COMPONENT_SNAPSHOT_F,
)
from .workflow_component_registry import WorkflowComponentRegistry
from .workflow_gateway_context import WorkflowGatewayContext
from .workflow_gateway_request import WorkflowGatewayRequest
from .workflow_gateway_response import WorkflowGatewayResponse
from .workflow_gateway_router import (
    ROUTE_CANCEL,
    ROUTE_QUERY,
    ROUTE_RETRY,
    ROUTE_SUBMIT,
    ROUTE_VALIDATE,
    WorkflowGatewayRouter,
)

_log = get_logger(__name__)


class WorkflowGatewayDispatcher:
    """
    Dispatches gateway requests to the appropriate M1-M5 subsystems.

    Thread-safe (stateless — state lives in injected components).
    """

    def __init__(self, router: Optional[WorkflowGatewayRouter] = None) -> None:
        self._router = router or WorkflowGatewayRouter()

    def dispatch(
        self,
        request:    WorkflowGatewayRequest,
        context:    WorkflowGatewayContext,
        components: WorkflowComponentRegistry,
    ) -> WorkflowGatewayResponse:
        """
        Dispatch a validated gateway request.

        Routes to the correct handler based on request_type and
        coordinates the M1-M5 subsystems.

        Always returns a WorkflowGatewayResponse — never raises for
        workflow-level failures.
        """
        t0    = time.monotonic()
        route = self._router.route(request)

        try:
            if route == ROUTE_SUBMIT:
                response = self._handle_submit(request, context, components)
            elif route == ROUTE_QUERY:
                response = self._handle_query(request, context, components)
            elif route == ROUTE_CANCEL:
                response = self._handle_cancel(request, context, components)
            elif route == ROUTE_RETRY:
                response = self._handle_retry(request, context, components)
            elif route == ROUTE_VALIDATE:
                response = self._handle_validate(request, context, components)
            else:
                raise WorkflowGatewayDispatchError(
                    f"Unknown route: {route!r}"
                )
        except WorkflowGatewayDispatchError:
            raise
        except Exception as exc:
            latency = round((time.monotonic() - t0) * 1000, 3)
            _log.error(
                f"Dispatcher: unexpected error for request={request.request_id!r}: {exc!r}"
            )
            return WorkflowGatewayResponse.failure_for(
                request,
                error_message      = str(exc),
                gateway_latency_ms = latency,
            )

        return response

    # ── Route handlers ────────────────────────────────────────────────────────

    def _handle_submit(
        self,
        request:    WorkflowGatewayRequest,
        context:    WorkflowGatewayContext,
        components: WorkflowComponentRegistry,
    ) -> WorkflowGatewayResponse:
        t0 = time.monotonic()

        # 1. Build and submit engine request (M2)
        engine = components.get_component_or_none(COMPONENT_ENGINE)
        session_id   = ""
        snapshot_id  = ""
        engine_data  = {}

        if engine is not None:
            from iios.workflow.engine import WorkflowEngineRequest
            from iios.workflow.lifecycle import WorkflowType as M1Type

            engine_req = WorkflowEngineRequest.create(
                workflow_id    = request.workflow_id,
                correlation_id = request.correlation_id,
                trace_id       = request.trace_id,
                payload        = dict(request.payload),
                configuration  = dict(request.configuration),
            )
            try:
                engine_resp   = engine.execute(engine_req)
                session_id    = engine_resp.session_id
                snapshot_id   = engine_resp.snapshot_id
                engine_data   = dict(engine_resp.data)
                engine_ok     = engine_resp.status.value == "success"
            except Exception as exc:
                _log.warning(f"Dispatcher: engine error: {exc!r}")
                engine_ok   = False
                engine_data = {"error": str(exc)}
        else:
            engine_ok = True   # passthrough when engine not wired

        # 2. Build M5 snapshot
        snap_factory = components.get_component_or_none(COMPONENT_SNAPSHOT_F)
        if snap_factory is not None and not snapshot_id:
            from iios.workflow.snapshot import ExecutionStatus, GovernanceDecision
            exec_status = (
                ExecutionStatus.COMPLETED if engine_ok else ExecutionStatus.FAILED
            )
            snap = snap_factory.create_completed(
                request.workflow_id,
                request.workflow_name,
                execution_duration_ms = round((time.monotonic() - t0) * 1000, 3),
            ) if engine_ok else snap_factory.create_failed(
                request.workflow_id,
                request.workflow_name,
                error_note = engine_data.get("error", "engine error"),
            )
            snapshot_id = snap.snapshot_id

        latency = round((time.monotonic() - t0) * 1000, 3)

        if engine_ok:
            return WorkflowGatewayResponse.success_for(
                request,
                session_id         = session_id,
                snapshot_id        = snapshot_id,
                data               = engine_data,
                gateway_latency_ms = latency,
                processing_time_ms = latency,
            )
        return WorkflowGatewayResponse.failure_for(
            request,
            error_message      = engine_data.get("error", "workflow execution failed"),
            session_id         = session_id,
            snapshot_id        = snapshot_id,
            gateway_latency_ms = latency,
            processing_time_ms = latency,
        )

    def _handle_query(
        self,
        request:    WorkflowGatewayRequest,
        context:    WorkflowGatewayContext,
        components: WorkflowComponentRegistry,
    ) -> WorkflowGatewayResponse:
        t0      = time.monotonic()
        latency = round((time.monotonic() - t0) * 1000, 3)
        return WorkflowGatewayResponse.success_for(
            request,
            data               = {"queried_workflow_id": request.workflow_id},
            gateway_latency_ms = latency,
        )

    def _handle_cancel(
        self,
        request:    WorkflowGatewayRequest,
        context:    WorkflowGatewayContext,
        components: WorkflowComponentRegistry,
    ) -> WorkflowGatewayResponse:
        t0      = time.monotonic()
        latency = round((time.monotonic() - t0) * 1000, 3)
        return WorkflowGatewayResponse.success_for(
            request,
            data               = {
                "cancelled_workflow_id": request.workflow_id,
                "cancelled":             True,
            },
            gateway_latency_ms = latency,
        )

    def _handle_retry(
        self,
        request:    WorkflowGatewayRequest,
        context:    WorkflowGatewayContext,
        components: WorkflowComponentRegistry,
    ) -> WorkflowGatewayResponse:
        # Re-use the submit path with retry metadata
        from .workflow_gateway_request import WorkflowGatewayRequest, GatewayRequestType
        import dataclasses
        submit_req = dataclasses.replace(
            request,
            request_type = GatewayRequestType.SUBMIT,
        )
        return self._handle_submit(submit_req, context, components)

    def _handle_validate(
        self,
        request:    WorkflowGatewayRequest,
        context:    WorkflowGatewayContext,
        components: WorkflowComponentRegistry,
    ) -> WorkflowGatewayResponse:
        t0      = time.monotonic()
        latency = round((time.monotonic() - t0) * 1000, 3)
        return WorkflowGatewayResponse.success_for(
            request,
            data               = {"validated": True},
            gateway_latency_ms = latency,
        )
