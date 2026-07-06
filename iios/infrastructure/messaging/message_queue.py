"""
iios/infrastructure/messaging/message_queue.py
===============================================
Simple thread-safe FIFO message queue.
"""

from __future__ import annotations

import queue
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

__all__ = ["Message", "MessageQueue"]


@dataclass
class Message:
    """A message in the queue."""
    topic: str
    body: Any
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    headers: dict[str, str] = field(default_factory=dict)

    def __repr__(self) -> str:
        return f"Message(topic={self.topic!r}, id={self.message_id[:8]})"


class MessageQueue:
    """Thread-safe FIFO queue for Message objects.

    Usage::

        mq = MessageQueue(maxsize=1000)
        mq.publish("orders", Message("orders", {"symbol": "RELIANCE"}))
        msg = mq.consume("orders")
    """

    def __init__(self, maxsize: int = 10000) -> None:
        self._queues: dict[str, queue.Queue[Message]] = {}
        self._lock = threading.RLock()
        self._maxsize = maxsize
        self._total_published = 0
        self._total_consumed = 0

    def _get_queue(self, topic: str) -> "queue.Queue[Message]":
        with self._lock:
            if topic not in self._queues:
                self._queues[topic] = queue.Queue(maxsize=self._maxsize)
            return self._queues[topic]

    def publish(self, topic: str, message: Message, *, block: bool = True, timeout: Optional[float] = None) -> None:
        q = self._get_queue(topic)
        q.put(message, block=block, timeout=timeout)
        with self._lock:
            self._total_published += 1

    def consume(self, topic: str, *, block: bool = True, timeout: Optional[float] = 1.0) -> Optional[Message]:
        q = self._get_queue(topic)
        try:
            msg = q.get(block=block, timeout=timeout)
            with self._lock:
                self._total_consumed += 1
            return msg
        except queue.Empty:
            return None

    def pending(self, topic: str) -> int:
        with self._lock:
            q = self._queues.get(topic)
        return q.qsize() if q else 0

    def topics(self) -> list[str]:
        with self._lock:
            return list(self._queues.keys())

    @property
    def total_published(self) -> int:
        return self._total_published

    @property
    def total_consumed(self) -> int:
        return self._total_consumed
