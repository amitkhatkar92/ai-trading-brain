"""
kafka_adapter.py — iios.integration.services
----------------------------------------------
Provider-independent Kafka adapter interface.

MUST NOT import: kafka-python, confluent-kafka, or any Kafka library.

C15 Enterprise Integration & Connectivity — Phase 1, Module 4
"""
from __future__ import annotations

import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from .connector_request import ConnectorRequest
from .connector_response import ConnectorResponse
from .constants import MessageDeliveryMode


# ════════════════════════════════════════════════════════════════════════
# Data objects
# ════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class KafkaMessage:
    """A single Kafka message (produce or consume)."""
    topic:     str
    key:       Optional[str]
    value:     Dict[str, Any]
    partition: int
    offset:    int
    timestamp: str  = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ════════════════════════════════════════════════════════════════════════
# Abstract Interface
# ════════════════════════════════════════════════════════════════════════


class BaseKafkaAdapter(ABC):
    """Abstract Kafka adapter — implementors inject the Kafka client library."""

    @abstractmethod
    def produce(
        self,
        topic:         str,
        value:         Dict[str, Any],
        key:           Optional[str]     = None,
        delivery_mode: MessageDeliveryMode = MessageDeliveryMode.AT_LEAST_ONCE,
    ) -> KafkaMessage:
        """Publish a message to a Kafka topic."""

    @abstractmethod
    def consume(
        self,
        topic:         str,
        group_id:      str,
        max_messages:  int = 1,
        timeout_ms:    int = 5_000,
    ) -> List[KafkaMessage]:
        """Poll messages from a Kafka topic."""

    @abstractmethod
    def health_check(self) -> bool:
        """Return True if the Kafka broker is reachable."""

    def execute(self, request: ConnectorRequest) -> ConnectorResponse:
        start = time.perf_counter_ns()
        try:
            cfg       = request.connector_config
            topic     = cfg.get("kafka_topic", "default-topic")
            operation = cfg.get("kafka_operation", "produce").lower()
            if operation == "consume":
                msgs = self.consume(
                    topic=topic,
                    group_id=cfg.get("kafka_group_id", "iios-consumer"),
                    max_messages=cfg.get("kafka_max_messages", 10),
                    timeout_ms=request.timeout_ms,
                )
                data = {"messages": [m.__dict__ for m in msgs], "count": len(msgs)}
            else:
                msg  = self.produce(topic=topic, value=request.payload)
                data = {"topic": msg.topic, "partition": msg.partition, "offset": msg.offset}
            latency_ms = (time.perf_counter_ns() - start) / 1_000_000
            return ConnectorResponse.success(
                request.request_id, data=data, latency_ms=latency_ms,
                adapter_id="kafka-adapter", transport="kafka_protocol",
            )
        except Exception as exc:
            latency_ms = (time.perf_counter_ns() - start) / 1_000_000
            return ConnectorResponse.failure(
                request.request_id, error_message=str(exc), latency_ms=latency_ms,
                adapter_id="kafka-adapter", transport="kafka_protocol",
            )


# ════════════════════════════════════════════════════════════════════════
# Simulated Implementation
# ════════════════════════════════════════════════════════════════════════


class SimulatedKafkaAdapter(BaseKafkaAdapter):
    """In-process Kafka simulation — no broker I/O."""

    def __init__(self) -> None:
        self._offset = 0

    def produce(
        self,
        topic:         str,
        value:         Dict[str, Any],
        key:           Optional[str]     = None,
        delivery_mode: MessageDeliveryMode = MessageDeliveryMode.AT_LEAST_ONCE,
    ) -> KafkaMessage:
        self._offset += 1
        return KafkaMessage(
            topic=topic, key=key, value=value, partition=0, offset=self._offset
        )

    def consume(
        self,
        topic:         str,
        group_id:      str,
        max_messages:  int = 1,
        timeout_ms:    int = 5_000,
    ) -> List[KafkaMessage]:
        return [
            KafkaMessage(
                topic=topic, key=None,
                value={"simulated": True, "index": i},
                partition=0, offset=i,
            )
            for i in range(min(max_messages, 1))
        ]

    def health_check(self) -> bool:
        return True
