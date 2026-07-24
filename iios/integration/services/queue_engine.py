"""
queue_engine.py — iios.integration.services
---------------------------------------------
QueueEngine — bounded in-memory FIFO queue for integration messages,
supporting multiple named queues with publisher/consumer isolation.

C15 Enterprise Integration & Connectivity — Phase 1, Module 4
"""
from __future__ import annotations

import threading
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Deque, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import DEFAULT_MAX_QUEUE_SIZE, MessageDeliveryMode

_log = get_logger(__name__)


@dataclass(frozen=True)
class QueueMessage:
    """An enqueued message."""
    message_id:    str
    queue_name:    str
    payload:       Dict[str, Any]
    delivery_mode: MessageDeliveryMode
    enqueued_at:   str

    @classmethod
    def create(
        cls,
        queue_name:    str,
        payload:       Dict[str, Any],
        delivery_mode: MessageDeliveryMode = MessageDeliveryMode.AT_LEAST_ONCE,
    ) -> "QueueMessage":
        return cls(
            message_id    = f"qmsg-{uuid.uuid4().hex[:12]}",
            queue_name    = queue_name,
            payload       = payload,
            delivery_mode = delivery_mode,
            enqueued_at   = datetime.now(timezone.utc).isoformat(),
        )


@dataclass
class QueueStats:
    """Per-queue statistics."""
    queue_name:  str
    enqueued:    int = 0
    dequeued:    int = 0
    dropped:     int = 0
    depth:       int = 0


class QueueEngine:
    """
    Thread-safe bounded in-memory message queue engine.

    Supports multiple named queues, each bounded at ``max_size``.
    Messages beyond capacity are dropped and tracked.
    """

    def __init__(self, max_size: int = DEFAULT_MAX_QUEUE_SIZE) -> None:
        self._lock    = threading.Lock()
        self._queues: Dict[str, Deque[QueueMessage]] = {}
        self._stats:  Dict[str, QueueStats]           = {}
        self._max     = max_size

    # ── Queue management ─────────────────────────────────────────────────

    def create_queue(self, name: str) -> None:
        with self._lock:
            if name not in self._queues:
                self._queues[name] = deque()
                self._stats[name]  = QueueStats(queue_name=name)

    def delete_queue(self, name: str) -> bool:
        with self._lock:
            if name in self._queues:
                del self._queues[name]
                del self._stats[name]
                return True
        return False

    def queue_names(self) -> List[str]:
        with self._lock:
            return list(self._queues.keys())

    # ── Publish / consume ─────────────────────────────────────────────────

    def enqueue(
        self,
        queue_name:    str,
        payload:       Dict[str, Any],
        delivery_mode: MessageDeliveryMode = MessageDeliveryMode.AT_LEAST_ONCE,
    ) -> Optional[QueueMessage]:
        """Enqueue a message. Returns the message or None if dropped."""
        with self._lock:
            if queue_name not in self._queues:
                self._queues[queue_name] = deque()
                self._stats[queue_name]  = QueueStats(queue_name=queue_name)
            q   = self._queues[queue_name]
            st  = self._stats[queue_name]
            if len(q) >= self._max:
                st.dropped += 1
                _log.debug(f"queue-engine: queue {queue_name!r} full — message dropped")
                return None
            msg = QueueMessage.create(queue_name, payload, delivery_mode)
            q.append(msg)
            st.enqueued += 1
            st.depth     = len(q)
        return msg

    def dequeue(
        self,
        queue_name: str,
        max_count:  int = 1,
    ) -> List[QueueMessage]:
        """Dequeue up to ``max_count`` messages. Returns empty list if none."""
        with self._lock:
            if queue_name not in self._queues:
                return []
            q   = self._queues[queue_name]
            st  = self._stats[queue_name]
            out = []
            for _ in range(min(max_count, len(q))):
                out.append(q.popleft())
            st.dequeued += len(out)
            st.depth     = len(q)
        return out

    def peek(self, queue_name: str) -> Optional[QueueMessage]:
        """Return the front message without removing it."""
        with self._lock:
            q = self._queues.get(queue_name)
            return q[0] if q else None

    def depth(self, queue_name: str) -> int:
        with self._lock:
            q = self._queues.get(queue_name)
            return len(q) if q else 0

    def stats(self, queue_name: str) -> Optional[QueueStats]:
        with self._lock:
            st = self._stats.get(queue_name)
            if st is None:
                return None
            return QueueStats(
                queue_name = st.queue_name,
                enqueued   = st.enqueued,
                dequeued   = st.dequeued,
                dropped    = st.dropped,
                depth      = st.depth,
            )

    @property
    def total_queues(self) -> int:
        with self._lock:
            return len(self._queues)
