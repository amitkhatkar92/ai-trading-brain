"""
iios/infrastructure/messaging/message_broker.py
===============================================
Simple pub/sub message broker backed by MessageQueue.
"""

from __future__ import annotations

import threading
from typing import Any, Callable, Optional

from .message_queue import Message, MessageQueue

__all__ = ["MessageBroker", "get_message_broker", "reset_message_broker"]

_lock = threading.Lock()
_broker: Optional["MessageBroker"] = None

Handler = Callable[[Message], None]


class MessageBroker:
    """In-process publish/subscribe broker.

    Usage::

        broker = get_message_broker()
        broker.subscribe("orders", handler_fn)
        broker.publish("orders", Message("orders", data))
    """

    def __init__(self) -> None:
        self._queue = MessageQueue()
        self._handlers: dict[str, list[Handler]] = {}
        self._lock = threading.RLock()

    def subscribe(self, topic: str, handler: Handler) -> None:
        with self._lock:
            self._handlers.setdefault(topic, []).append(handler)

    def unsubscribe(self, topic: str, handler: Handler) -> bool:
        with self._lock:
            handlers = self._handlers.get(topic, [])
            try:
                handlers.remove(handler)
                return True
            except ValueError:
                return False

    def publish(self, topic: str, body: Any, headers: Optional[dict] = None) -> Message:
        msg = Message(topic=topic, body=body, headers=headers or {})
        self._queue.publish(topic, msg)
        self._dispatch(msg)
        return msg

    def _dispatch(self, msg: Message) -> None:
        with self._lock:
            handlers = list(self._handlers.get(msg.topic, []))
        for handler in handlers:
            try:
                handler(msg)
            except Exception:
                pass

    def pending(self, topic: str) -> int:
        return self._queue.pending(topic)

    def topics(self) -> list[str]:
        return self._queue.topics()


def get_message_broker() -> MessageBroker:
    global _broker
    with _lock:
        if _broker is None:
            _broker = MessageBroker()
        return _broker


def reset_message_broker() -> None:
    global _broker
    with _lock:
        _broker = None
