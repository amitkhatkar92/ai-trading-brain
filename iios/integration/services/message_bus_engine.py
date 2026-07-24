"""
message_bus_engine.py — iios.integration.services
---------------------------------------------------
MessageBusEngine — routes messages to the appropriate messaging adapter
(Kafka, RabbitMQ, Redis Streams, or generic queue).

C15 Enterprise Integration & Connectivity — Phase 1, Module 4
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .connector_request import ConnectorRequest
from .connector_response import ConnectorResponse
from .constants import ServiceType
from .kafka_adapter import SimulatedKafkaAdapter
from .rabbitmq_adapter import SimulatedRabbitMQAdapter
from .redis_stream_adapter import SimulatedRedisStreamAdapter

_log = get_logger(__name__)


@dataclass
class MessageBusStats:
    """Counters for message bus activity."""
    published:    int = 0
    consumed:     int = 0
    failed:       int = 0
    total_latency_ms: float = 0.0

    @property
    def avg_latency_ms(self) -> float:
        total = self.published + self.consumed
        return self.total_latency_ms / total if total else 0.0


class MessageBusEngine:
    """
    Routes integration requests to Kafka, RabbitMQ, or Redis Streams.

    Adapters are lazily initialised and cached; no vendor SDKs are imported
    by the engine itself — only provider-independent interfaces.
    """

    def __init__(self) -> None:
        self._lock       = threading.Lock()
        self._stats      = MessageBusStats()
        self._kafka      = SimulatedKafkaAdapter()
        self._rabbitmq   = SimulatedRabbitMQAdapter()
        self._redis      = SimulatedRedisStreamAdapter()

    # ── public ──────────────────────────────────────────────────────────

    def route(self, request: ConnectorRequest) -> ConnectorResponse:
        """Dispatch a messaging request to the correct adapter."""
        adapter_map = {
            ServiceType.KAFKA:        self._kafka.execute,
            ServiceType.RABBITMQ:     self._rabbitmq.execute,
            ServiceType.REDIS_STREAM: self._redis.execute,
        }
        execute_fn = adapter_map.get(request.service_type)
        if execute_fn is None:
            return ConnectorResponse.failure(
                request.request_id,
                error_message=f"Unsupported messaging service_type: {request.service_type.value}",
                adapter_id="message-bus-engine",
            )
        response = execute_fn(request)
        with self._lock:
            if response.status.value == "success":
                self._stats.published += 1
            else:
                self._stats.failed += 1
            self._stats.total_latency_ms += response.latency_ms
        return response

    @property
    def stats(self) -> MessageBusStats:
        with self._lock:
            return MessageBusStats(
                published        = self._stats.published,
                consumed         = self._stats.consumed,
                failed           = self._stats.failed,
                total_latency_ms = self._stats.total_latency_ms,
            )

    def health_check(self) -> bool:
        return (
            self._kafka.health_check()
            and self._rabbitmq.health_check()
            and self._redis.health_check()
        )
