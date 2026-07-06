"""
iios/events/messaging/message_dispatcher.py
============================================
Dispatches messages to registered handler functions.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from .message import Message, Response
from .message_queue import RetryQueue, DeadLetterQueue
from ..event_exceptions import MessageDeliveryError

__all__ = ["MessageHandler", "DispatchStats", "MessageDispatcher"]

_LOG = logging.getLogger("iios.events.messaging.dispatcher")

MessageHandler = Callable[[Message], Optional[Response]]


@dataclass
class DispatchStats:
    delivered: int = 0
    failed: int = 0
    retried: int = 0
    dead_lettered: int = 0
    avg_duration_ms: float = 0.0
    _total_ms: float = field(default=0.0, repr=False)

    def record(self, ms: float, success: bool) -> None:
        if success:
            self.delivered += 1
        else:
            self.failed += 1
        self._total_ms += ms
        total = self.delivered + self.failed
        self.avg_duration_ms = self._total_ms / total if total else 0.0


class MessageDispatcher:
    """Routes incoming messages to registered handler functions.

    Usage::

        dispatcher = MessageDispatcher()
        dispatcher.register("order.create", handle_create_order)
        result = dispatcher.dispatch(message)
    """

    def __init__(self) -> None:
        self._handlers: dict[str, MessageHandler] = {}
        self._retry_queue = RetryQueue()
        self._dlq = DeadLetterQueue()
        self._stats = DispatchStats()
        self._lock = threading.RLock()

    def register(self, message_type: str, handler: MessageHandler) -> None:
        with self._lock:
            self._handlers[message_type] = handler

    def unregister(self, message_type: str) -> bool:
        with self._lock:
            return self._handlers.pop(message_type, None) is not None

    def dispatch(self, message: Message) -> Optional[Response]:
        if message.is_expired:
            _LOG.debug("Dropping expired message %s", message.message_id)
            return None

        msg_type = message.payload.get("type", "") or message.envelope.headers.get("type", "")
        with self._lock:
            handler = self._handlers.get(msg_type)

        t0 = time.monotonic()
        try:
            result = handler(message) if handler else None
            ms = (time.monotonic() - t0) * 1000
            message.envelope.deliver()
            self._stats.record(ms, success=True)
            return result
        except Exception as exc:
            ms = (time.monotonic() - t0) * 1000
            self._stats.record(ms, success=False)
            message.envelope.fail()
            _LOG.warning("Message dispatch failed: %s", exc)
            if message.can_retry:
                self._retry_queue.schedule_retry(message)
                self._stats.retried += 1
            else:
                self._dlq.put(message, reason=str(exc))
                self._stats.dead_lettered += 1
            return None

    def process_retries(self) -> int:
        """Process all currently-due retry messages. Returns count processed."""
        due = self._retry_queue.drain_due()
        for msg in due:
            self.dispatch(msg)
        return len(due)

    def stats(self) -> DispatchStats:
        return self._stats

    def dlq(self) -> DeadLetterQueue:
        return self._dlq
