"""
integration_services_factory.py — iios.integration.services
-------------------------------------------------------------
IntegrationServicesFactory — creates pre-configured ConnectorRequest
objects, adapters, engines, and pools for common integration patterns.

C15 Enterprise Integration & Connectivity — Phase 1, Module 4
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .connection_pool import ConnectionPool
from .connector_request import ConnectorRequest
from .constants import (
    AuthScheme,
    ConnectorOperation,
    DEFAULT_POOL_MAX,
    DEFAULT_POOL_SIZE,
    DEFAULT_RETRY_COUNT,
    DEFAULT_TIMEOUT_MS,
    MessageDeliveryMode,
    RetryStrategy,
    ServiceType,
    TransportType,
)
from .event_bus_engine import EventBusEngine
from .message_bus_engine import MessageBusEngine
from .notification_engine import NotificationEngine
from .queue_engine import QueueEngine
from .retry_engine import RetryConfig, RetryEngine
from .stream_engine import StreamEngine
from .webhook_engine import WebhookEngine


class IntegrationServicesFactory:
    """
    Factory for building pre-configured integration service objects.

    All create_* methods are stateless and return new instances.
    """

    # ── ConnectorRequest factories ────────────────────────────────────────

    @staticmethod
    def create_rest_request(
        endpoint:     str,
        payload:      Optional[Dict[str, Any]] = None,
        headers:      Optional[Dict[str, str]] = None,
        http_method:  str                       = "POST",
        auth_scheme:  AuthScheme                = AuthScheme.NONE,
        auth_config:  Optional[Dict[str, Any]] = None,
        timeout_ms:   int                       = DEFAULT_TIMEOUT_MS,
    ) -> ConnectorRequest:
        return ConnectorRequest.create(
            approved_request_id = f"factory-{uuid.uuid4().hex[:8]}",
            service_type        = ServiceType.REST_API,
            transport_type      = TransportType.HTTP,
            auth_scheme         = auth_scheme,
            endpoint            = endpoint,
            payload             = payload or {},
            headers             = headers or {},
            auth_config         = auth_config or {},
            connector_config    = {"http_method": http_method},
            timeout_ms          = timeout_ms,
        )

    @staticmethod
    def create_kafka_request(
        topic:        str,
        payload:      Optional[Dict[str, Any]] = None,
        operation:    str                       = "produce",
        delivery_mode: MessageDeliveryMode      = MessageDeliveryMode.AT_LEAST_ONCE,
        timeout_ms:   int                       = DEFAULT_TIMEOUT_MS,
    ) -> ConnectorRequest:
        return ConnectorRequest.create(
            approved_request_id = f"factory-{uuid.uuid4().hex[:8]}",
            service_type        = ServiceType.KAFKA,
            transport_type      = TransportType.KAFKA_PROTOCOL,
            endpoint            = f"kafka://{topic}",
            payload             = payload or {},
            connector_config    = {
                "kafka_topic":     topic,
                "kafka_operation": operation,
                "delivery_mode":   delivery_mode.value,
            },
            timeout_ms = timeout_ms,
        )

    @staticmethod
    def create_rabbitmq_request(
        exchange:    str,
        routing_key: str,
        payload:     Optional[Dict[str, Any]] = None,
        operation:   str                      = "publish",
        timeout_ms:  int                      = DEFAULT_TIMEOUT_MS,
    ) -> ConnectorRequest:
        return ConnectorRequest.create(
            approved_request_id = f"factory-{uuid.uuid4().hex[:8]}",
            service_type        = ServiceType.RABBITMQ,
            transport_type      = TransportType.AMQP,
            endpoint            = f"amqp://{exchange}/{routing_key}",
            payload             = payload or {},
            connector_config    = {
                "rmq_operation":   operation,
                "rmq_exchange":    exchange,
                "rmq_routing_key": routing_key,
            },
            timeout_ms = timeout_ms,
        )

    @staticmethod
    def create_webhook_request(
        topic:     str,
        payload:   Optional[Dict[str, Any]] = None,
        timeout_ms: int = DEFAULT_TIMEOUT_MS,
    ) -> ConnectorRequest:
        return ConnectorRequest.create(
            approved_request_id = f"factory-{uuid.uuid4().hex[:8]}",
            service_type        = ServiceType.WEBHOOK,
            transport_type      = TransportType.HTTP,
            endpoint            = f"webhook://{topic}",
            payload             = payload or {},
            connector_config    = {"webhook_topic": topic},
            timeout_ms          = timeout_ms,
        )

    @staticmethod
    def create_notification_request(
        channel:    str,
        recipient:  str,
        subject:    str,
        body:       str,
        timeout_ms: int = DEFAULT_TIMEOUT_MS,
    ) -> ConnectorRequest:
        _channel_type_map = {
            "email": ServiceType.EMAIL,
            "sms":   ServiceType.SMS,
            "push":  ServiceType.PUSH_NOTIFICATION,
        }
        svc = _channel_type_map.get(channel, ServiceType.EMAIL)
        return ConnectorRequest.create(
            approved_request_id = f"factory-{uuid.uuid4().hex[:8]}",
            service_type        = svc,
            transport_type      = TransportType.INTERNAL,
            endpoint            = f"notification://{channel}/{recipient}",
            payload             = {"body": body},
            connector_config    = {
                "notification_channel":   channel,
                "notification_recipient": recipient,
                "notification_subject":   subject,
            },
            timeout_ms = timeout_ms,
        )

    # ── Engine factories ──────────────────────────────────────────────────

    @staticmethod
    def create_retry_engine(
        max_attempts: int          = DEFAULT_RETRY_COUNT,
        strategy:     RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF,
        delay_ms:     int          = 100,
    ) -> RetryEngine:
        return RetryEngine(RetryConfig(
            max_attempts = max_attempts,
            strategy     = strategy,
            delay_ms     = delay_ms,
        ))

    @staticmethod
    def create_connection_pool(
        name:     str,
        min_size: int = DEFAULT_POOL_SIZE,
        max_size: int = DEFAULT_POOL_MAX,
    ) -> ConnectionPool:
        return ConnectionPool(pool_name=name, min_size=min_size, max_size=max_size)

    @staticmethod
    def create_message_bus() -> MessageBusEngine:
        return MessageBusEngine()

    @staticmethod
    def create_event_bus() -> EventBusEngine:
        return EventBusEngine()

    @staticmethod
    def create_stream_engine(max_sessions: int = 256) -> StreamEngine:
        return StreamEngine(max_sessions=max_sessions)

    @staticmethod
    def create_queue_engine(max_size: int = 10_000) -> QueueEngine:
        return QueueEngine(max_size=max_size)

    @staticmethod
    def create_webhook_engine() -> WebhookEngine:
        return WebhookEngine()

    @staticmethod
    def create_notification_engine() -> NotificationEngine:
        return NotificationEngine()
