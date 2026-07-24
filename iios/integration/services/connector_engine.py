"""
connector_engine.py — iios.integration.services
-------------------------------------------------
ConnectorEngine — ties together connector and adapter layers to execute
integration requests.

C15 Enterprise Integration & Connectivity — Phase 1, Module 4
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .adapter_engine import AdapterEngine
from .connector_context import ConnectorContext
from .connector_manager import ConnectorManager
from .connector_request import ConnectorRequest
from .connector_response import ConnectorResponse
from .constants import ServiceType
from .exceptions import ConnectorNotFoundError


class ConnectorEngine:
    """
    Loads connectors and executes requests through the adapter layer.

    Orchestrates the connector-adapter interaction; does not implement
    any vendor-specific protocol.
    """

    def __init__(
        self,
        connector_manager: Optional[ConnectorManager] = None,
        adapter_engine:    Optional[AdapterEngine]    = None,
    ) -> None:
        self._connector_manager = connector_manager or ConnectorManager()
        self._adapter_engine    = adapter_engine    or AdapterEngine()

    @property
    def connector_manager(self) -> ConnectorManager:
        return self._connector_manager

    @property
    def adapter_engine(self) -> AdapterEngine:
        return self._adapter_engine

    def load_connector(self, service_type: ServiceType) -> Dict[str, Any]:
        """Load connector descriptor for the given service type."""
        desc = self._connector_manager.load(service_type)
        return desc.to_dict()

    def execute(
        self,
        request: ConnectorRequest,
        context: ConnectorContext,
    ) -> ConnectorResponse:
        """Execute a single connector request through the adapter layer."""
        import time
        t0 = time.monotonic()

        # Try to load connector
        try:
            desc = self._connector_manager.load(request.service_type)
        except ConnectorNotFoundError:
            return ConnectorResponse.failure(
                request.request_id,
                error_message=f"No connector available for {request.service_type.value}",
            )

        # Attempt to load and execute adapter
        try:
            adapter = self._adapter_engine.load_for_service(request.service_type)
            result  = self._adapter_engine.execute(adapter, context, request.payload)
        except Exception as exc:
            latency = (time.monotonic() - t0) * 1_000
            return ConnectorResponse.failure(
                request.request_id,
                error_message=str(exc),
                latency_ms=latency,
                connector_id=desc.connector_id,
            )

        latency = (time.monotonic() - t0) * 1_000
        return ConnectorResponse.success(
            request.request_id,
            data=result,
            latency_ms=latency,
            connector_id=desc.connector_id,
            adapter_id=result.get("adapter_id", ""),
            transport=context.transport_type.value,
        )

    def execute_batch(
        self,
        requests: List[ConnectorRequest],
        contexts: List[ConnectorContext],
    ) -> List[ConnectorResponse]:
        return [self.execute(req, ctx) for req, ctx in zip(requests, contexts)]
