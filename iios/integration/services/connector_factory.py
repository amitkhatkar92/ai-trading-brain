"""
connector_factory.py — iios.integration.services
--------------------------------------------------
ConnectorFactory — creates connector descriptors and contexts.

C15 Enterprise Integration & Connectivity — Phase 1, Module 4
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .connector_context import ConnectorContext
from .connector_registry import ConnectorDescriptor
from .constants import AuthScheme, RetryStrategy, ServiceType, TransportType


class ConnectorFactory:
    """Creates connector descriptors and execution contexts."""

    def create_descriptor(
        self,
        name:         str,
        service_type: ServiceType,
        *,
        version:      str                      = "1.0.0",
        capabilities: Optional[List[str]]      = None,
        enabled:      bool                     = True,
        metadata:     Optional[Dict[str, Any]] = None,
    ) -> ConnectorDescriptor:
        return ConnectorDescriptor.create(
            name, service_type,
            version=version, capabilities=capabilities,
            enabled=enabled, metadata=metadata,
        )

    def create_context(
        self,
        request_id:   str,
        session_id:   str,
        service_type: ServiceType,
        *,
        transport_type:     TransportType      = TransportType.HTTP,
        auth_scheme:        AuthScheme         = AuthScheme.NONE,
        endpoint:           str                = "",
        timeout_ms:         int                = 30_000,
        retry_max_attempts: int                = 3,
        connector_config:   Optional[Dict[str, Any]] = None,
        auth_config:        Optional[Dict[str, Any]] = None,
        transport_config:   Optional[Dict[str, Any]] = None,
        metadata:           Optional[Dict[str, Any]] = None,
    ) -> ConnectorContext:
        return ConnectorContext.create(
            request_id, session_id, service_type,
            transport_type=transport_type, auth_scheme=auth_scheme,
            endpoint=endpoint, timeout_ms=timeout_ms,
            retry_max_attempts=retry_max_attempts,
            connector_config=connector_config, auth_config=auth_config,
            transport_config=transport_config, metadata=metadata,
        )

    # ── convenience factories ─────────────────────────────────────────

    def create_rest_connector(self, name: str = "REST Connector") -> ConnectorDescriptor:
        return self.create_descriptor(
            name, ServiceType.REST_API,
            capabilities=["get", "post", "put", "patch", "delete"],
        )

    def create_kafka_connector(self, name: str = "Kafka Connector") -> ConnectorDescriptor:
        return self.create_descriptor(
            name, ServiceType.KAFKA,
            capabilities=["publish", "subscribe", "consume"],
        )

    def create_websocket_connector(self, name: str = "WebSocket Connector") -> ConnectorDescriptor:
        return self.create_descriptor(
            name, ServiceType.WEBSOCKET,
            capabilities=["connect", "send", "receive"],
        )

    def create_database_connector(self, name: str = "Database Connector") -> ConnectorDescriptor:
        return self.create_descriptor(
            name, ServiceType.DATABASE,
            capabilities=["query", "execute", "transaction"],
        )
