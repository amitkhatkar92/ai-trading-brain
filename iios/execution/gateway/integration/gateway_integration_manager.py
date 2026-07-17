"""iios/execution/gateway/integration/gateway_integration_manager.py
==================================================
GatewayIntegrationManager — coordinates the eight-step gateway
integration workflow.

Workflow
--------
  1.  Validate request context.
  2.  Coordinate lifecycle: create → RECEIVED → VALIDATING → READY.
  3.  Route via RoutingEngine → RoutingDecision.
  4.  Coordinate lifecycle: QUEUED → ROUTING → DISPATCHED.
  5.  Submit to ExecutionGatewayEngine.
  6.  Check broker layer health for selected broker.
  7.  Build and publish ExecutionGatewaySnapshot.
  8.  Return GatewayIntegrationResponse.

On any step failure the manager advances the lifecycle request
to FAILED, records statistics, fires FAILED event, and returns
a failed GatewayIntegrationResponse (never raises).

C6 Execution Intelligence — Phase 5, Module 6
"""
from __future__ import annotations

import time
import uuid
import threading
from typing import Any, Callable, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger
from iios.execution.gateway.lifecycle import make_gateway_context
from iios.execution.gateway.engine import make_engine_gateway_context
from iios.execution.gateway.routing import make_routing_context
from iios.execution.gateway.snapshot import GatewaySnapshotFactory
from iios.execution.gateway.snapshot.constants import (
    DispatchStatus,
    GatewayState,
    GatewayStatus,
    QueueStatus,
)

from .constants import (
    INTEGRATION_MANAGER_SYSTEM_ID,
    VERSION,
    IntegrationOutcome,
    IntegrationRequestStatus,
)
from .gateway_component_registry import GatewayComponentRegistry
from .gateway_integration_events import (
    IntegrationEvent,
    make_request_completed_event,
    make_request_failed_event,
    make_request_received_event,
    make_request_routed_event,
    make_request_validated_event,
    make_snapshot_published_event,
)
from .gateway_integration_history import GatewayIntegrationHistory
from .gateway_integration_registry import GatewayIntegrationRegistry
from .gateway_integration_request import GatewayIntegrationRequest
from .gateway_integration_response import GatewayIntegrationResponse
from .gateway_integration_statistics import GatewayIntegrationStatistics
from .gateway_integration_validation import GatewayIntegrationValidator

_log = get_logger(__name__, engine_id=INTEGRATION_MANAGER_SYSTEM_ID)


class GatewayIntegrationManager:
    """
    Stateful coordinator for the gateway integration workflow.

    Owned exclusively by GatewayIntegrationEngine.  All public methods
    are thread-safe.
    """

    def __init__(
        self,
        components:     GatewayComponentRegistry,
        registry:       GatewayIntegrationRegistry,
        history:        GatewayIntegrationHistory,
        statistics:     GatewayIntegrationStatistics,
        integration_id: str,
    ) -> None:
        self._components     = components
        self._registry       = registry
        self._history        = history
        self._stats          = statistics
        self._integration_id = integration_id
        self._validator      = GatewayIntegrationValidator()
        self._listeners:     List[Callable[[IntegrationEvent], None]] = []
        self._lock           = threading.RLock()

    # ── Primary workflow ──────────────────────────────────────────────────────

    def execute(
        self, request: GatewayIntegrationRequest
    ) -> GatewayIntegrationResponse:
        """
        Execute the full gateway integration workflow.

        Always returns a GatewayIntegrationResponse — never raises.
        """
        t0 = time.time()
        self._registry.store_request(request)
        self._history.append_request(request)
        self._stats.record_received()
        self._fire(make_request_received_event(
            self._integration_id, request.request_id
        ))

        lc_gateway_id: Optional[str] = None

        try:
            # Step 1 — validate
            validation = self._validator.validate_request(request)
            if not validation.is_valid:
                self._stats.record_validation_failure()
                return self._fail_response(
                    request,
                    t0,
                    IntegrationOutcome.VALIDATION_FAILED,
                    "; ".join(validation.errors),
                    lc_gateway_id,
                )
            self._stats.record_validated()
            self._fire(make_request_validated_event(
                self._integration_id, request.request_id
            ))

            ctx = request.context

            # Step 2 — coordinate lifecycle (CREATED → READY)
            lc_ctx = make_gateway_context(
                ctx.execution_id,
                ctx.order_id,
                ctx.portfolio_id,
                ctx.strategy_id,
                symbol=ctx.symbol,
                side=ctx.side,
                quantity=ctx.quantity,
                price=ctx.price,
            )
            lc_req = self._components.lifecycle.create_from_context(lc_ctx)
            lc_gateway_id = lc_req.gateway_id
            self._components.lifecycle.receive(lc_gateway_id)
            self._components.lifecycle.start_validation(lc_gateway_id)
            self._components.lifecycle.mark_ready(lc_gateway_id)

            # Step 3 — route via RoutingEngine
            t_route = time.time()
            routing_ctx = make_routing_context(
                ctx.execution_id,
                ctx.order_id,
                ctx.portfolio_id,
                ctx.strategy_id,
                symbol=ctx.symbol,
                exchange=ctx.exchange,
                side=ctx.side,
                order_type=ctx.order_type,
                product=ctx.product,
                asset_class=ctx.asset_class,
                quantity=ctx.quantity,
                price=ctx.price,
                preferred_broker_id=ctx.preferred_broker_id,
            )
            routing_decision = self._components.routing_engine.route(routing_ctx)
            routing_ms = (time.time() - t_route) * 1000.0
            self._stats.record_routed(routing_ms)
            self._fire(make_request_routed_event(
                self._integration_id, request.request_id
            ))

            # Step 4 — advance lifecycle: QUEUED → ROUTING → DISPATCHED
            self._components.lifecycle.queue(lc_gateway_id)
            self._components.lifecycle.start_routing(lc_gateway_id)

            # Step 5 — submit to gateway engine
            engine_ctx = make_engine_gateway_context(
                ctx.execution_id,
                ctx.order_id,
                ctx.portfolio_id,
                ctx.strategy_id,
                symbol=ctx.symbol,
            )
            t_dispatch = time.time()
            engine_response = self._components.engine.submit_request(engine_ctx)
            dispatch_ms = (time.time() - t_dispatch) * 1000.0
            self._stats.record_dispatched(dispatch_ms)
            self._components.lifecycle.dispatch(lc_gateway_id)

            # Step 6 — check broker layer health (informational)
            broker_capabilities: tuple = ()
            if routing_decision.selected_broker_id:
                try:
                    health = self._components.broker_manager.get_health(
                        routing_decision.selected_broker_id
                    )
                    if hasattr(health, "capabilities"):
                        broker_capabilities = tuple(
                            str(c) for c in (health.capabilities or ())
                        )
                except Exception:
                    pass  # non-fatal; snapshot will omit capabilities

            # Step 7 — build and publish ExecutionGatewaySnapshot
            processing_ms = (time.time() - t0) * 1000.0
            gw_state = (
                GatewayState.COMPLETED
                if routing_decision.is_routed
                else GatewayState.FAILED
            )
            gw_status = (
                GatewayStatus.HEALTHY
                if routing_decision.is_routed
                else GatewayStatus.DEGRADED
            )
            dispatch_status = (
                DispatchStatus.DISPATCHED
                if routing_decision.is_routed
                else DispatchStatus.FAILED
            )
            snap_version = self._components.snapshot_store.next_version_for(
                ctx.execution_id
            )
            gw_snapshot = GatewaySnapshotFactory.create_snapshot(
                gateway_id=lc_gateway_id,
                execution_id=ctx.execution_id,
                order_id=ctx.order_id,
                portfolio_id=ctx.portfolio_id,
                strategy_id=ctx.strategy_id,
                gateway_state=gw_state,
                lifecycle_state=engine_response.status,
                gateway_status=gw_status,
                dispatch_status=dispatch_status,
                queue_status=QueueStatus.PROCESSING,
                position_id=ctx.position_id,
                workflow_id=ctx.workflow_id,
                decision_id=routing_decision.decision_id,
                selected_broker_id=routing_decision.selected_broker_id,
                selected_broker_name=routing_decision.selected_broker_name,
                routing_policy_id=routing_decision.policy_id,
                routing_decision_outcome=routing_decision.outcome.value,
                processing_duration_ms=processing_ms,
                broker_capability_summary=broker_capabilities,
                snapshot_version=snap_version,
                gateway_statistics={
                    "engine_elapsed_ms": engine_response.elapsed_ms,
                    "routing_ms":        routing_ms,
                    "dispatch_ms":       dispatch_ms,
                },
                audit_metadata={
                    "integration_id":    self._integration_id,
                    "request_id":        request.request_id,
                },
            )
            self._components.snapshot_store.publish(gw_snapshot)
            self._stats.record_snapshot_published()
            self._fire(make_snapshot_published_event(
                self._integration_id,
                request_id=request.request_id,
            ))

            # Advance lifecycle to COMPLETED
            self._components.lifecycle.complete(lc_gateway_id)

            # Step 8 — build success response
            outcome = (
                IntegrationOutcome.SUCCESS
                if routing_decision.is_routed
                else IntegrationOutcome.ROUTING_FAILED
            )
            response = GatewayIntegrationResponse(
                response_id=str(uuid.uuid4()),
                request_id=request.request_id,
                integration_id=self._integration_id,
                status=IntegrationRequestStatus.COMPLETED,
                outcome=outcome,
                execution_id=ctx.execution_id,
                order_id=ctx.order_id,
                portfolio_id=ctx.portfolio_id,
                strategy_id=ctx.strategy_id,
                gateway_snapshot_id=gw_snapshot.snapshot_id,
                routing_decision_id=routing_decision.decision_id,
                selected_broker_id=routing_decision.selected_broker_id,
                selected_broker_name=routing_decision.selected_broker_name,
                failure_reason=None,
                processing_duration_ms=processing_ms,
            )
            self._registry.store_response(response)
            self._history.append_response(response)
            self._stats.record_completed(processing_ms)
            self._fire(make_request_completed_event(
                self._integration_id, request.request_id
            ))

            _log.debug(
                "Integration request completed.",
                request_id=request.request_id,
                outcome=outcome.value,
                broker=routing_decision.selected_broker_id,
            )
            return response

        except Exception as exc:
            _log.error(
                "Integration workflow error.",
                request_id=request.request_id,
                error=str(exc),
            )
            if lc_gateway_id:
                try:
                    self._components.lifecycle.fail(lc_gateway_id)
                except Exception:
                    pass
            return self._fail_response(
                request,
                t0,
                IntegrationOutcome.COMPONENT_ERROR,
                str(exc),
                lc_gateway_id,
            )

    # ── Event management ──────────────────────────────────────────────────────

    def add_event_listener(
        self, listener: Callable[[IntegrationEvent], None]
    ) -> None:
        with self._lock:
            if listener not in self._listeners:
                self._listeners.append(listener)

    def remove_event_listener(
        self, listener: Callable[[IntegrationEvent], None]
    ) -> None:
        with self._lock:
            if listener in self._listeners:
                self._listeners.remove(listener)

    def _fire(self, event: IntegrationEvent) -> None:
        self._history.append_event(event)
        with self._lock:
            listeners = list(self._listeners)
        for listener in listeners:
            try:
                listener(event)
            except Exception:
                _log.exception(
                    "Event listener raised.",
                    event_type=event.event_type.value,
                )

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _fail_response(
        self,
        request: GatewayIntegrationRequest,
        t0: float,
        outcome: IntegrationOutcome,
        reason: str,
        lc_gateway_id: Optional[str],
    ) -> GatewayIntegrationResponse:
        processing_ms = (time.time() - t0) * 1000.0
        response = GatewayIntegrationResponse(
            response_id=str(uuid.uuid4()),
            request_id=request.request_id,
            integration_id=self._integration_id,
            status=IntegrationRequestStatus.FAILED,
            outcome=outcome,
            execution_id=request.execution_id,
            order_id=request.order_id,
            portfolio_id=request.portfolio_id,
            strategy_id=request.strategy_id,
            gateway_snapshot_id=None,
            routing_decision_id=None,
            selected_broker_id=None,
            selected_broker_name=None,
            failure_reason=reason,
            processing_duration_ms=processing_ms,
        )
        self._registry.store_response(response)
        self._history.append_response(response)
        self._stats.record_failed()
        self._fire(make_request_failed_event(
            self._integration_id, request.request_id
        ))
        return response
