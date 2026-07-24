"""
adapter_factory.py — iios.integration.services
------------------------------------------------
AdapterFactory — creates adapter descriptors.

C15 Enterprise Integration & Connectivity — Phase 1, Module 4
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .adapter_registry import AdapterDescriptor
from .constants import AdapterProtocol, ServiceType


class AdapterFactory:
    """Creates adapter descriptors for all supported protocols."""

    def create_descriptor(
        self,
        name:         str,
        protocol:     AdapterProtocol,
        service_type: ServiceType,
        *,
        version:      str                      = "1.0.0",
        capabilities: Optional[List[str]]      = None,
        enabled:      bool                     = True,
        metadata:     Optional[Dict[str, Any]] = None,
    ) -> AdapterDescriptor:
        return AdapterDescriptor.create(
            name, protocol, service_type,
            version=version, capabilities=capabilities,
            enabled=enabled, metadata=metadata,
        )

    def create_rest_adapter(self) -> AdapterDescriptor:
        return self.create_descriptor(
            "REST Adapter", AdapterProtocol.REST, ServiceType.REST_API,
            capabilities=["get", "post", "put", "patch", "delete", "head", "options"],
        )

    def create_graphql_adapter(self) -> AdapterDescriptor:
        return self.create_descriptor(
            "GraphQL Adapter", AdapterProtocol.GRAPHQL, ServiceType.GRAPHQL,
            capabilities=["query", "mutation", "subscription"],
        )

    def create_grpc_adapter(self) -> AdapterDescriptor:
        return self.create_descriptor(
            "gRPC Adapter", AdapterProtocol.GRPC, ServiceType.GRPC,
            capabilities=["unary", "server_stream", "client_stream", "bidi_stream"],
        )

    def create_websocket_adapter(self) -> AdapterDescriptor:
        return self.create_descriptor(
            "WebSocket Adapter", AdapterProtocol.WEBSOCKET, ServiceType.WEBSOCKET,
            capabilities=["connect", "send", "receive", "close"],
        )

    def create_kafka_adapter(self) -> AdapterDescriptor:
        return self.create_descriptor(
            "Kafka Adapter", AdapterProtocol.KAFKA, ServiceType.KAFKA,
            capabilities=["publish", "subscribe", "consume", "commit"],
        )

    def create_rabbitmq_adapter(self) -> AdapterDescriptor:
        return self.create_descriptor(
            "RabbitMQ Adapter", AdapterProtocol.RABBITMQ, ServiceType.RABBITMQ,
            capabilities=["publish", "consume", "ack", "nack"],
        )

    def create_redis_adapter(self) -> AdapterDescriptor:
        return self.create_descriptor(
            "Redis Stream Adapter", AdapterProtocol.REDIS, ServiceType.REDIS_STREAM,
            capabilities=["xadd", "xread", "xack", "xgroup"],
        )

    def create_database_adapter(self) -> AdapterDescriptor:
        return self.create_descriptor(
            "Database Adapter", AdapterProtocol.DATABASE, ServiceType.DATABASE,
            capabilities=["query", "execute", "transaction", "batch"],
        )

    def create_notification_adapter(self) -> AdapterDescriptor:
        return self.create_descriptor(
            "Notification Adapter", AdapterProtocol.PUSH, ServiceType.PUSH_NOTIFICATION,
            capabilities=["send", "broadcast", "schedule"],
        )
