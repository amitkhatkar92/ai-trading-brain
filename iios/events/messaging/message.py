"""
iios/events/messaging/message.py
================================
Base Message, Command, Query, and Response dataclasses.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Generic, Optional, TypeVar

__all__ = [
    "MessageStatus", "MessageType",
    "MessageEnvelope", "Message", "Command", "Query", "Response",
    "make_message_id",
]

T = TypeVar("T")


class MessageStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    DELIVERED = "delivered"
    ACKNOWLEDGED = "acknowledged"
    FAILED = "failed"
    DEAD_LETTERED = "dead_lettered"
    EXPIRED = "expired"


class MessageType(str, Enum):
    EVENT = "event"
    COMMAND = "command"
    QUERY = "query"
    RESPONSE = "response"


def make_message_id() -> str:
    return str(uuid.uuid4())


@dataclass
class MessageEnvelope:
    """Routing and delivery envelope wrapping any message."""
    message_id: str = field(default_factory=make_message_id)
    message_type: MessageType = MessageType.EVENT
    source: str = ""
    destination: str = ""
    correlation_id: str = field(default_factory=make_message_id)
    reply_to: str = ""
    timestamp: float = field(default_factory=time.time)
    ttl: Optional[float] = None
    retry_count: int = 0
    max_retries: int = 3
    headers: dict[str, str] = field(default_factory=dict)
    priority: int = 50
    status: MessageStatus = MessageStatus.PENDING
    idempotency_key: str = ""

    @property
    def is_expired(self) -> bool:
        if self.ttl is None:
            return False
        return time.time() - self.timestamp >= self.ttl

    def ack(self) -> None:
        self.status = MessageStatus.ACKNOWLEDGED

    def fail(self) -> None:
        self.status = MessageStatus.FAILED
        self.retry_count += 1

    def deliver(self) -> None:
        self.status = MessageStatus.DELIVERED


@dataclass
class Message:
    """Generic message containing a payload and an envelope."""
    payload: dict[str, Any] = field(default_factory=dict)
    envelope: MessageEnvelope = field(default_factory=MessageEnvelope)

    @property
    def message_id(self) -> str:
        return self.envelope.message_id

    @property
    def is_expired(self) -> bool:
        return self.envelope.is_expired

    @property
    def can_retry(self) -> bool:
        return self.envelope.retry_count < self.envelope.max_retries


@dataclass
class Command:
    """A command message — instructs the system to perform an action.

    Usage::

        cmd = Command(
            command_type="trade.place_order",
            payload={"symbol": "RELIANCE", "qty": 10, "side": "BUY"},
            source="execution_engine",
        )
    """
    command_type: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    source: str = ""
    envelope: MessageEnvelope = field(default_factory=lambda: MessageEnvelope(message_type=MessageType.COMMAND))

    @property
    def command_id(self) -> str:
        return self.envelope.message_id

    @property
    def correlation_id(self) -> str:
        return self.envelope.correlation_id


@dataclass
class Query:
    """A query message — requests data from the system.

    Usage::

        q = Query(
            query_type="portfolio.get_positions",
            parameters={"account_id": "ACC001"},
        )
    """
    query_type: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)
    source: str = ""
    reply_to: str = ""
    timeout: float = 30.0
    envelope: MessageEnvelope = field(default_factory=lambda: MessageEnvelope(message_type=MessageType.QUERY))

    @property
    def query_id(self) -> str:
        return self.envelope.message_id

    @property
    def correlation_id(self) -> str:
        return self.envelope.correlation_id


@dataclass
class Response:
    """Response to a Command or Query."""
    correlation_id: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    success: bool = True
    error: Optional[str] = None
    error_code: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    envelope: MessageEnvelope = field(default_factory=lambda: MessageEnvelope(message_type=MessageType.RESPONSE))

    @classmethod
    def ok(cls, correlation_id: str, payload: Optional[dict[str, Any]] = None) -> "Response":
        return cls(correlation_id=correlation_id, payload=payload or {}, success=True)

    @classmethod
    def err(cls, correlation_id: str, error: str, code: str = "") -> "Response":
        return cls(correlation_id=correlation_id, error=error, error_code=code, success=False)
