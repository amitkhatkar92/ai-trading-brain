"""
rabbitmq_adapter.py — iios.integration.services
-------------------------------------------------
Provider-independent RabbitMQ (AMQP) adapter interface.

MUST NOT import: pika, aio-pika, or any AMQP library.

C15 Enterprise Integration & Connectivity — Phase 1, Module 4
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .connector_request import ConnectorRequest
from .connector_response import ConnectorResponse
from .constants import MessageDeliveryMode


# ════════════════════════════════════════════════════════════════════════
# Data objects
# ════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class AmqpMessage:
    """A single AMQP message."""
    exchange:    str
    routing_key: str
    body:        Dict[str, Any]
    delivery_tag: int
    timestamp:   str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ════════════════════════════════════════════════════════════════════════
# Abstract Interface
# ════════════════════════════════════════════════════════════════════════


class BaseRabbitMQAdapter(ABC):
    """Abstract RabbitMQ adapter — implementors inject pika/aio-pika."""

    @abstractmethod
    def publish(
        self,
        exchange:    str,
        routing_key: str,
        body:        Dict[str, Any],
        delivery_mode: MessageDeliveryMode = MessageDeliveryMode.AT_LEAST_ONCE,
    ) -> AmqpMessage:
        """Publish a message to an exchange."""

    @abstractmethod
    def consume(
        self,
        queue:        str,
        max_messages: int = 1,
        timeout_ms:   int = 5_000,
    ) -> List[AmqpMessage]:
        """Fetch messages from a queue."""

    @abstractmethod
    def health_check(self) -> bool:
        """Return True if the broker connection is alive."""

    def execute(self, request: ConnectorRequest) -> ConnectorResponse:
        start = time.perf_counter_ns()
        try:
            cfg       = request.connector_config
            operation = cfg.get("rmq_operation", "publish").lower()
            if operation == "consume":
                msgs = self.consume(
                    queue=cfg.get("rmq_queue", "iios"),
                    max_messages=cfg.get("rmq_max_messages", 10),
                    timeout_ms=request.timeout_ms,
                )
                data = {"messages": [m.__dict__ for m in msgs], "count": len(msgs)}
            else:
                msg  = self.publish(
                    exchange=cfg.get("rmq_exchange", ""),
                    routing_key=cfg.get("rmq_routing_key", "iios"),
                    body=request.payload,
                )
                data = {"exchange": msg.exchange, "routing_key": msg.routing_key,
                        "delivery_tag": msg.delivery_tag}
            latency_ms = (time.perf_counter_ns() - start) / 1_000_000
            return ConnectorResponse.success(
                request.request_id, data=data, latency_ms=latency_ms,
                adapter_id="rabbitmq-adapter", transport="amqp",
            )
        except Exception as exc:
            latency_ms = (time.perf_counter_ns() - start) / 1_000_000
            return ConnectorResponse.failure(
                request.request_id, error_message=str(exc), latency_ms=latency_ms,
                adapter_id="rabbitmq-adapter", transport="amqp",
            )


# ════════════════════════════════════════════════════════════════════════
# Simulated Implementation
# ════════════════════════════════════════════════════════════════════════


class SimulatedRabbitMQAdapter(BaseRabbitMQAdapter):
    """In-process AMQP simulation — no broker I/O."""

    def __init__(self) -> None:
        self._delivery_tag = 0

    def publish(
        self,
        exchange:    str,
        routing_key: str,
        body:        Dict[str, Any],
        delivery_mode: MessageDeliveryMode = MessageDeliveryMode.AT_LEAST_ONCE,
    ) -> AmqpMessage:
        self._delivery_tag += 1
        return AmqpMessage(
            exchange=exchange, routing_key=routing_key,
            body=body, delivery_tag=self._delivery_tag,
        )

    def consume(
        self,
        queue:        str,
        max_messages: int = 1,
        timeout_ms:   int = 5_000,
    ) -> List[AmqpMessage]:
        return [
            AmqpMessage(
                exchange="", routing_key=queue,
                body={"simulated": True, "index": i},
                delivery_tag=i + 1,
            )
            for i in range(min(max_messages, 1))
        ]

    def health_check(self) -> bool:
        return True
