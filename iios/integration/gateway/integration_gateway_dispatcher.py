"""
integration_gateway_dispatcher.py — iios.integration.gateway
--------------------------------------------------------------
IntegrationGatewayDispatcher — orchestrates the workflow execution
by calling each subsystem component in the correct order.

The dispatcher coordinates; it does NOT implement any business logic.

Workflow (for SUBMIT):
  1. Lifecycle → create_session + initialize
  2. Engine    → dispatch(IntegrationRequest)
  3. Governance → evaluate(IntegrationPolicyRequest)
  4. Services  → execute(ConnectorRequest)
  5. Snapshot  → build + register

C15 Enterprise Integration & Connectivity — Phase 1, Module 6
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Dict, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import GatewayComponentType, GatewayWorkflowStep
from .exceptions import (
    GatewayEngineError,
    GatewayGovernanceError,
    GatewayLifecycleError,
    GatewayServicesError,
    GatewaySnapshotError,
)
from .integration_component_registry import IntegrationComponentRegistry
from .integration_gateway_context import IntegrationGatewayContext
from .integration_gateway_router import GatewayRouteDecision

_log = get_logger(__name__)


class IntegrationGatewayDispatcher:
    """
    Executes the ordered gateway workflow for a single request.

    Receives a context and a routing decision, invokes each required
    component in sequence, and updates the context in-place so the
    gateway can build the final response.
    """

    def __init__(self, component_registry: IntegrationComponentRegistry) -> None:
        self._registry = component_registry

    # ─── public dispatch ──────────────────────────────────────────────

    def dispatch(
        self,
        context: IntegrationGatewayContext,
        route:   GatewayRouteDecision,
    ) -> None:
        """
        Execute the workflow steps required by *route*.

        Each step updates *context* with its output.
        On failure, the context has the error recorded and the exception
        is re-raised so the gateway can build a failure response.
        """
        if route.requires_lifecycle:
            self._step_lifecycle(context)

        if route.requires_engine:
            self._step_engine(context, route)

        if route.requires_governance:
            self._step_governance(context, route)

        if route.requires_services:
            self._step_services(context, route)

        if route.requires_snapshot:
            self._step_snapshot(context)

    # ─── step: lifecycle ──────────────────────────────────────────────

    def _step_lifecycle(self, ctx: IntegrationGatewayContext) -> None:
        t0 = time.monotonic()
        ctx.advance_step(GatewayWorkflowStep.LIFECYCLE_INITIALIZED)
        try:
            lifecycle = self._registry.get_or_raise(GatewayComponentType.LIFECYCLE)
            req       = ctx.request

            # Reuse existing session or create new one
            if req.has_session:
                session_id = req.session_id
            else:
                session = lifecycle.create_session(
                    workflow_id = req.workflow_id,
                )
                session_id = session.session_id
                # Transition to INITIALIZING
                lifecycle.initialize(session_id, reason="gateway-dispatch")

            ctx.lifecycle_session_id = session_id
        except Exception as exc:
            ctx.add_error(f"Lifecycle step failed: {exc!s}")
            raise GatewayLifecycleError(f"Lifecycle step failed: {exc!s}") from exc
        finally:
            ctx.record_timing(GatewayWorkflowStep.LIFECYCLE_INITIALIZED,
                              (time.monotonic() - t0) * 1_000)

    # ─── step: engine ─────────────────────────────────────────────────

    def _step_engine(
        self,
        ctx:   IntegrationGatewayContext,
        route: GatewayRouteDecision,
    ) -> None:
        t0 = time.monotonic()
        ctx.advance_step(GatewayWorkflowStep.ENGINE_EXECUTED)
        try:
            from iios.integration.engine import (
                IntegrationRequest,
                ConnectorType,
                AdapterType,
                ProtocolType,
                DispatchMode,
            )
            engine = self._registry.get_or_raise(GatewayComponentType.ENGINE)
            req    = ctx.request

            # Derive connector/adapter/protocol from request config
            connector_type = ConnectorType(
                req.connector_config.get("type", ConnectorType.GENERIC.value)
                if hasattr(ConnectorType, "GENERIC") else
                list(ConnectorType)[0].value
            ) if req.connector_config else list(ConnectorType)[0]

            engine_req = IntegrationRequest.create(
                connector_type  = connector_type,
                adapter_type    = AdapterType.GENERIC,
                protocol_type   = ProtocolType.INTERNAL,
                dispatch_mode   = DispatchMode.IMMEDIATE,
                endpoint        = req.endpoint_config.get("url", "") if req.endpoint_config else "",
                payload         = dict(req.payload),
                headers         = {},
                auth_config     = dict(req.auth_config),
                metadata        = {
                    "gateway_id":  ctx.gateway_id,
                    "request_id":  req.request_id,
                    "session_id":  ctx.lifecycle_session_id,
                },
                correlation_id  = req.request_id,
                trace_id        = ctx.context_id,
            )
            response = engine.dispatch(engine_req)

            ctx.engine_request_id  = engine_req.request_id
            ctx.engine_response_id = getattr(response, "response_id", "")
        except (GatewayLifecycleError,):
            raise
        except Exception as exc:
            ctx.add_error(f"Engine step failed: {exc!s}")
            raise GatewayEngineError(f"Engine step failed: {exc!s}") from exc
        finally:
            ctx.record_timing(GatewayWorkflowStep.ENGINE_EXECUTED,
                              (time.monotonic() - t0) * 1_000)

    # ─── step: governance ─────────────────────────────────────────────

    def _step_governance(
        self,
        ctx:   IntegrationGatewayContext,
        route: GatewayRouteDecision,
    ) -> None:
        t0 = time.monotonic()
        ctx.advance_step(GatewayWorkflowStep.GOVERNANCE_EVALUATED)
        try:
            from iios.integration.policies import (
                IntegrationPolicyRequest,
                IntegrationPolicyContext,
            )
            policy_engine = self._registry.get_or_raise(GatewayComponentType.POLICIES)
            req           = ctx.request

            policy_ctx = IntegrationPolicyContext.create(
                engine_request_id = ctx.engine_request_id or req.request_id,
                engine_session_id = ctx.lifecycle_session_id,
                connector_type    = req.connector_config.get("type", "generic") if req.connector_config else "generic",
                adapter_type      = req.connector_config.get("adapter", "generic") if req.connector_config else "generic",
                protocol_type     = req.protocol_config.get("type", "http") if req.protocol_config else "http",
                endpoint          = req.endpoint_config.get("url", "") if req.endpoint_config else "",
                auth_config       = dict(req.auth_config),
                connector_config  = dict(req.connector_config),
                protocol_config   = dict(req.protocol_config),
                endpoint_config   = dict(req.endpoint_config),
                metadata          = {"gateway_request_id": req.request_id},
            )
            policy_req = IntegrationPolicyRequest.create(
                policy_context = policy_ctx,
                correlation_id = req.request_id,
                trace_id       = ctx.context_id,
            )
            policy_resp = policy_engine.evaluate(policy_req)

            ctx.governance_request_id = policy_req.request_id
            ctx.governance_decision   = getattr(policy_resp, "overall_action", "allow").value \
                if hasattr(getattr(policy_resp, "overall_action", "allow"), "value") \
                else str(getattr(policy_resp, "overall_action", "allow"))
        except (GatewayLifecycleError, GatewayEngineError):
            raise
        except Exception as exc:
            ctx.add_error(f"Governance step failed: {exc!s}")
            raise GatewayGovernanceError(f"Governance step failed: {exc!s}") from exc
        finally:
            ctx.record_timing(GatewayWorkflowStep.GOVERNANCE_EVALUATED,
                              (time.monotonic() - t0) * 1_000)

    # ─── step: services ───────────────────────────────────────────────

    def _step_services(
        self,
        ctx:   IntegrationGatewayContext,
        route: GatewayRouteDecision,
    ) -> None:
        t0 = time.monotonic()
        ctx.advance_step(GatewayWorkflowStep.SERVICES_EXECUTED)
        try:
            from iios.integration.services import (
                ConnectorRequest,
                ServiceType,
                TransportType,
                AuthScheme,
                RetryStrategy,
            )
            connector_engine = self._registry.get_or_raise(GatewayComponentType.SERVICES)
            req              = ctx.request

            # Derive ServiceType from request config
            svc_type_str = req.connector_config.get("service_type", "") if req.connector_config else ""
            try:
                svc_type = ServiceType(svc_type_str)
            except (ValueError, KeyError):
                svc_type = ServiceType("rest_api")

            connector_req = ConnectorRequest.create(
                approved_request_id = ctx.engine_request_id or req.request_id,
                service_type        = svc_type,
                transport_type      = TransportType.HTTP,
                auth_scheme         = AuthScheme.NONE,
                retry_strategy      = RetryStrategy.EXPONENTIAL_BACKOFF,
                endpoint            = req.endpoint_config.get("url", "") if req.endpoint_config else "",
                payload             = dict(req.payload),
                auth_config         = dict(req.auth_config),
                connector_config    = dict(req.connector_config),
                metadata            = {
                    "gateway_request_id": req.request_id,
                    "session_id":         ctx.lifecycle_session_id,
                },
            )
            connector_engine.execute(connector_req)
        except (GatewayLifecycleError, GatewayEngineError, GatewayGovernanceError):
            raise
        except Exception as exc:
            ctx.add_error(f"Services step failed: {exc!s}")
            raise GatewayServicesError(f"Services step failed: {exc!s}") from exc
        finally:
            ctx.record_timing(GatewayWorkflowStep.SERVICES_EXECUTED,
                              (time.monotonic() - t0) * 1_000)

    # ─── step: snapshot ───────────────────────────────────────────────

    def _step_snapshot(self, ctx: IntegrationGatewayContext) -> None:
        t0 = time.monotonic()
        ctx.advance_step(GatewayWorkflowStep.SNAPSHOT_GENERATED)
        try:
            from iios.integration.snapshot import (
                IntegrationSnapshotBuilder,
                IntegrationSnapshotRegistry,
                SnapshotStatus,
                LifecycleState,
                GovernanceState,
                ConnectivityState,
            )
            snap_registry = self._registry.get_or_raise(GatewayComponentType.SNAPSHOT)
            req           = ctx.request

            snap = (
                IntegrationSnapshotBuilder()
                .set_session_ids(
                    ctx.lifecycle_session_id or req.request_id,  # integration_session_id
                    req.workflow_id,                              # integration_workflow_id
                    req.enterprise_id,                           # enterprise_session_id
                )
                .set_lifecycle_state(LifecycleState.ACTIVE)
                .set_governance_state(
                    GovernanceState.COMPLIANT
                    if ctx.governance_decision in ("allow", "ALLOW", "", "compliant")
                    else GovernanceState.UNDER_REVIEW
                )
                .set_connectivity_state(ConnectivityState.CONNECTED)
                .set_status(SnapshotStatus.PUBLISHED)
                .set_metadata_fields(
                    tags = {
                        "gateway_id":  ctx.gateway_id,
                        "request_id":  req.request_id,
                        "operation":   req.operation.value,
                    },
                )
                .build()
            )

            snap_registry.register(snap)
            ctx.snapshot_id = snap.snapshot_id
            ctx.advance_step(GatewayWorkflowStep.SNAPSHOT_VALIDATED)
        except (GatewayLifecycleError, GatewayEngineError,
                GatewayGovernanceError, GatewayServicesError):
            raise
        except Exception as exc:
            ctx.add_error(f"Snapshot step failed: {exc!s}")
            raise GatewaySnapshotError(f"Snapshot step failed: {exc!s}") from exc
        finally:
            ctx.record_timing(GatewayWorkflowStep.SNAPSHOT_GENERATED,
                              (time.monotonic() - t0) * 1_000)
