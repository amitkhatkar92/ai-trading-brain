"""
integration_gateway_factory.py — iios.integration.gateway
-----------------------------------------------------------
IntegrationGatewayFactory — convenience factory for gateway objects.

C15 Enterprise Integration & Connectivity — Phase 1, Module 6
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import DEFAULT_GATEWAY_ID, GatewayComponentType, GatewayOperationType
from .integration_component_registry import IntegrationComponentRegistry
from .integration_gateway_context import IntegrationGatewayContext
from .integration_gateway_request import IntegrationGatewayRequest
from .integration_gateway_response import IntegrationGatewayResponse

_log = get_logger(__name__)


class IntegrationGatewayFactory:
    """
    Convenience factory that creates gateway objects without exposing
    the construction details to callers.
    """

    # ─── gateway creation ─────────────────────────────────────────────

    @staticmethod
    def create(gateway_id: str = DEFAULT_GATEWAY_ID) -> "IntegrationGateway":  # type: ignore[name-defined]
        """
        Create and return a fully configured IntegrationGateway with
        default-constructed components.  Call ``initialize()`` and
        ``start()`` on the returned gateway before submitting requests.
        """
        from .integration_gateway import IntegrationGateway  # avoid circular at module level
        return IntegrationGateway(gateway_id=gateway_id)

    @staticmethod
    def create_with_components(
        components: Dict[GatewayComponentType, Any],
        gateway_id: str = DEFAULT_GATEWAY_ID,
    ) -> "IntegrationGateway":  # type: ignore[name-defined]
        """
        Create a gateway pre-loaded with the given component instances.
        Useful for testing or custom deployments.
        """
        from .integration_gateway import IntegrationGateway
        comp_registry = IntegrationComponentRegistry()
        for ct, comp in components.items():
            comp_registry.register(ct, comp)
        return IntegrationGateway(
            gateway_id         = gateway_id,
            component_registry = comp_registry,
        )

    # ─── request creation ─────────────────────────────────────────────

    @staticmethod
    def create_request(
        operation:     GatewayOperationType,
        workflow_id:   str,
        enterprise_id: str,
        **kwargs: Any,
    ) -> IntegrationGatewayRequest:
        """Create an IntegrationGatewayRequest."""
        return IntegrationGatewayRequest.create(
            operation     = operation,
            workflow_id   = workflow_id,
            enterprise_id = enterprise_id,
            **kwargs,
        )

    @staticmethod
    def create_submit_request(
        workflow_id:      str,
        enterprise_id:    str,
        payload:          Optional[Dict[str, Any]] = None,
        connector_config: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> IntegrationGatewayRequest:
        """Shortcut for SUBMIT operation request."""
        return IntegrationGatewayRequest.create(
            operation        = GatewayOperationType.SUBMIT,
            workflow_id      = workflow_id,
            enterprise_id    = enterprise_id,
            payload          = payload,
            connector_config = connector_config,
            **kwargs,
        )

    @staticmethod
    def create_connect_request(
        workflow_id:      str,
        enterprise_id:    str,
        connector_config: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> IntegrationGatewayRequest:
        """Shortcut for CONNECT operation request."""
        return IntegrationGatewayRequest.create(
            operation        = GatewayOperationType.CONNECT,
            workflow_id      = workflow_id,
            enterprise_id    = enterprise_id,
            connector_config = connector_config,
            **kwargs,
        )

    @staticmethod
    def create_disconnect_request(
        workflow_id:   str,
        enterprise_id: str,
        session_id:    str = "",
        **kwargs: Any,
    ) -> IntegrationGatewayRequest:
        """Shortcut for DISCONNECT operation request."""
        return IntegrationGatewayRequest.create(
            operation     = GatewayOperationType.DISCONNECT,
            workflow_id   = workflow_id,
            enterprise_id = enterprise_id,
            session_id    = session_id,
            **kwargs,
        )

    # ─── context creation ─────────────────────────────────────────────

    @staticmethod
    def create_context(
        request:    IntegrationGatewayRequest,
        gateway_id: str = DEFAULT_GATEWAY_ID,
    ) -> IntegrationGatewayContext:
        """Create an execution context for the given request."""
        return IntegrationGatewayContext(request=request, gateway_id=gateway_id)

    # ─── response creation ────────────────────────────────────────────

    @staticmethod
    def create_success_response(
        context: IntegrationGatewayContext,
        data:    Optional[Dict[str, Any]] = None,
    ) -> IntegrationGatewayResponse:
        """Build a success response from a completed context."""
        return IntegrationGatewayResponse.success(
            request_id           = context.request.request_id,
            operation            = context.request.operation,
            gateway_state        = context.gateway_state,
            lifecycle_session_id = context.lifecycle_session_id,
            engine_request_id    = context.engine_request_id,
            governance_decision  = context.governance_decision,
            snapshot_id          = context.snapshot_id,
            data                 = data,
            processing_time_ms   = context.elapsed_ms(),
        )

    @staticmethod
    def create_failure_response(
        context:    IntegrationGatewayContext,
        error:      str,
        error_code: str = "",
    ) -> IntegrationGatewayResponse:
        """Build a failure response from an errored context."""
        return IntegrationGatewayResponse.failure(
            request_id           = context.request.request_id,
            operation            = context.request.operation,
            gateway_state        = context.gateway_state,
            error                = error,
            error_code           = error_code,
            lifecycle_session_id = context.lifecycle_session_id,
            engine_request_id    = context.engine_request_id,
            governance_decision  = context.governance_decision,
            snapshot_id          = context.snapshot_id,
            processing_time_ms   = context.elapsed_ms(),
        )
