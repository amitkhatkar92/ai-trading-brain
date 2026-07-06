"""
iios/events/messaging/message_factory.py
==========================================
Factory for creating typed Message, Command, Query, Response instances.
"""

from __future__ import annotations

import time
from typing import Any, Optional

from .message import Command, Message, MessageEnvelope, MessageType, Query, Response

__all__ = ["MessageFactory"]


class MessageFactory:
    """Creates Message instances with validated envelopes.

    Usage::

        factory = MessageFactory(source="execution_engine")
        msg = factory.message({"order_id": "ORD001", "type": "order.fill"})
        cmd = factory.command("order.cancel", {"order_id": "ORD001"})
        qry = factory.query("portfolio.positions", {"account_id": "ACC001"})
    """

    def __init__(self, source: str = "iios") -> None:
        self._source = source

    def message(
        self,
        payload: Optional[dict[str, Any]] = None,
        *,
        destination: str = "",
        priority: int = 50,
        ttl: Optional[float] = None,
        correlation_id: Optional[str] = None,
        headers: Optional[dict[str, str]] = None,
    ) -> Message:
        env = MessageEnvelope(
            message_type=MessageType.EVENT,
            source=self._source,
            destination=destination,
            priority=priority,
            ttl=ttl,
            headers=headers or {},
        )
        if correlation_id:
            env.correlation_id = correlation_id
        return Message(payload=dict(payload or {}), envelope=env)

    def command(
        self,
        command_type: str,
        payload: Optional[dict[str, Any]] = None,
        *,
        destination: str = "",
        priority: int = 30,
        ttl: Optional[float] = None,
    ) -> Command:
        env = MessageEnvelope(
            message_type=MessageType.COMMAND,
            source=self._source,
            destination=destination,
            priority=priority,
            ttl=ttl,
        )
        return Command(command_type=command_type, payload=dict(payload or {}), source=self._source, envelope=env)

    def query(
        self,
        query_type: str,
        parameters: Optional[dict[str, Any]] = None,
        *,
        reply_to: str = "",
        timeout: float = 30.0,
        priority: int = 40,
    ) -> Query:
        env = MessageEnvelope(
            message_type=MessageType.QUERY,
            source=self._source,
            priority=priority,
        )
        return Query(
            query_type=query_type,
            parameters=dict(parameters or {}),
            source=self._source,
            reply_to=reply_to,
            timeout=timeout,
            envelope=env,
        )

    def response_ok(self, correlation_id: str, payload: Optional[dict[str, Any]] = None) -> Response:
        return Response.ok(correlation_id, payload)

    def response_err(self, correlation_id: str, error: str, code: str = "") -> Response:
        return Response.err(correlation_id, error, code)

    def with_ttl(self, payload: dict[str, Any], ttl: float, **kw: Any) -> Message:
        return self.message(payload, ttl=ttl, **kw)

    @classmethod
    def make(cls, source: str = "iios") -> "MessageFactory":
        return cls(source=source)
