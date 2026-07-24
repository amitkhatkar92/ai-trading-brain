"""
api_gateway_engine.py — iios.integration.services
---------------------------------------------------
ApiGatewayEngine — routes ConnectorRequests through the right
client adapter (REST / GraphQL / gRPC / WebSocket).

C15 Enterprise Integration & Connectivity — Phase 1, Module 4
"""
from __future__ import annotations

import threading
from typing import Any, Dict, Optional

from iios.common.logging.logging_manager import get_logger

from .connector_request import ConnectorRequest
from .connector_response import ConnectorResponse
from .constants import AdapterProtocol, ServiceType
from .graphql_client import SimulatedGraphqlClient
from .grpc_client import SimulatedGrpcClient
from .http_client import SimulatedHttpClient
from .rest_client import SimulatedRestClient
from .websocket_client import SimulatedWebSocketClient

_log = get_logger(__name__)

# Protocol → adapter class mapping
_ADAPTER_MAP = {
    AdapterProtocol.REST:      SimulatedRestClient,
    AdapterProtocol.GRAPHQL:   SimulatedGraphqlClient,
    AdapterProtocol.GRPC:      SimulatedGrpcClient,
    AdapterProtocol.WEBSOCKET: SimulatedWebSocketClient,
    AdapterProtocol.HTTP:      SimulatedHttpClient,
}


class ApiGatewayEngine:
    """
    Routes integration requests to the appropriate protocol client.

    Adapter instances are lazily instantiated and cached per protocol.
    """

    def __init__(self) -> None:
        self._lock      = threading.Lock()
        self._adapters: Dict[AdapterProtocol, Any] = {}
        self._requests_routed = 0

    # ── public ──────────────────────────────────────────────────────────

    def route(self, request: ConnectorRequest) -> ConnectorResponse:
        """Select the appropriate client adapter and execute the request."""
        protocol = self._resolve_protocol(request)
        adapter  = self._get_adapter(protocol)
        _log.debug(f"api-gateway routing request {request.request_id!r} via {protocol.value}")

        response = adapter.execute(request)

        with self._lock:
            self._requests_routed += 1

        return response

    @property
    def requests_routed(self) -> int:
        with self._lock:
            return self._requests_routed

    def health_check(self) -> bool:
        """Return True if at least one adapter is operational."""
        return any(
            self._get_adapter(p).health_check()
            for p in list(_ADAPTER_MAP.keys())[:1]
        )

    # ── internals ────────────────────────────────────────────────────────

    def _resolve_protocol(self, request: ConnectorRequest) -> AdapterProtocol:
        """Map the request's service_type to an AdapterProtocol."""
        mapping: Dict[ServiceType, AdapterProtocol] = {
            ServiceType.REST_API:  AdapterProtocol.REST,
            ServiceType.GRAPHQL:   AdapterProtocol.GRAPHQL,
            ServiceType.GRPC:      AdapterProtocol.GRPC,
            ServiceType.WEBSOCKET: AdapterProtocol.WEBSOCKET,
            ServiceType.HTTP:      AdapterProtocol.HTTP,
        }
        return mapping.get(request.service_type, AdapterProtocol.REST)

    def _get_adapter(self, protocol: AdapterProtocol) -> Any:
        with self._lock:
            if protocol not in self._adapters:
                cls = _ADAPTER_MAP.get(protocol, SimulatedRestClient)
                self._adapters[protocol] = cls()
            return self._adapters[protocol]
