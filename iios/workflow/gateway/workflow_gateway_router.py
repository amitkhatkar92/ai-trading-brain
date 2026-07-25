"""
workflow_gateway_router.py — iios.workflow.gateway
---------------------------------------------------
WorkflowGatewayRouter — routes gateway requests to appropriate handlers.

The router does NOT execute handlers.  It selects the routing target
based on the request type and returns a routing decision string.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 6
"""
from __future__ import annotations

from typing import Dict

from iios.common.logging.logging_manager import get_logger

from .constants import GatewayRequestType
from .exceptions import WorkflowGatewayRoutingError
from .workflow_gateway_request import WorkflowGatewayRequest

_log = get_logger(__name__)

# Routing targets — used by dispatcher to select the right handler
ROUTE_SUBMIT   = "submit"
ROUTE_QUERY    = "query"
ROUTE_CANCEL   = "cancel"
ROUTE_RETRY    = "retry"
ROUTE_VALIDATE = "validate"

_REQUEST_TYPE_TO_ROUTE: Dict[GatewayRequestType, str] = {
    GatewayRequestType.SUBMIT:   ROUTE_SUBMIT,
    GatewayRequestType.QUERY:    ROUTE_QUERY,
    GatewayRequestType.CANCEL:   ROUTE_CANCEL,
    GatewayRequestType.RETRY:    ROUTE_RETRY,
    GatewayRequestType.VALIDATE: ROUTE_VALIDATE,
}


class WorkflowGatewayRouter:
    """
    Stateless, thread-safe request router.

    Selects the routing target for each gateway request based on its
    request_type.  Returns a string route token used by the dispatcher.
    """

    def route(self, request: WorkflowGatewayRequest) -> str:
        """
        Determine the routing target for this request.

        Returns:
            A routing target string (ROUTE_* constant).

        Raises:
            WorkflowGatewayRoutingError if the request type is not supported.
        """
        route = _REQUEST_TYPE_TO_ROUTE.get(request.request_type)
        if route is None:
            raise WorkflowGatewayRoutingError(
                f"No route for request type: {request.request_type!r}"
            )
        _log.debug(
            f"Router: request={request.request_id!r} "
            f"type={request.request_type.value!r} → route={route!r}"
        )
        return route

    def supported_types(self) -> list:
        return list(_REQUEST_TYPE_TO_ROUTE.keys())
