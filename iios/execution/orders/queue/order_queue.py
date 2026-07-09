"""iios/execution/orders/queue/order_queue.py

Thread-safe FIFO order queue backed by collections.deque.
"""
from __future__ import annotations

import threading
import time
from collections import deque
from typing import Any

from ..order_constants import DEFAULT_MAX_QUEUE_SIZE
from ..core.order import Order
from ..order_exceptions import QueueFullError


class OrderQueue:
    """Thread-safe FIFO queue of Order objects."""

    def __init__(
        self,
        name:      str = "default",
        max_size:  int = DEFAULT_MAX_QUEUE_SIZE,
    ) -> None:
        self._name      = name
        self._max_size  = max_size
        self._queue:    deque[Order]    = deque()
        self._lock:     threading.RLock = threading.RLock()
        self._enqueued: int  = 0
        self._dequeued: int  = 0
        self._created_at: float = time.time()

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def name(self) -> str:
        return self._name

    @property
    def max_size(self) -> int:
        return self._max_size

    # ── Core operations ───────────────────────────────────────────────────────

    def enqueue(self, order: Order) -> None:
        with self._lock:
            if len(self._queue) >= self._max_size:
                raise QueueFullError(queue_name=self._name, capacity=self._max_size)
            self._queue.append(order)
            self._enqueued += 1

    def dequeue(self) -> Order | None:
        with self._lock:
            if not self._queue:
                return None
            order = self._queue.popleft()
            self._dequeued += 1
            return order

    def peek(self) -> Order | None:
        with self._lock:
            return self._queue[0] if self._queue else None

    def remove(self, order_id: str) -> bool:
        """Remove a specific order by ID. Returns True if found and removed."""
        with self._lock:
            for i, o in enumerate(self._queue):
                if o.order_id == order_id:
                    del self._queue[i]
                    return True
            return False

    # ── Inspection ────────────────────────────────────────────────────────────

    def __len__(self) -> int:
        with self._lock:
            return len(self._queue)

    def is_empty(self) -> bool:
        with self._lock:
            return len(self._queue) == 0

    def is_full(self) -> bool:
        with self._lock:
            return len(self._queue) >= self._max_size

    def contains(self, order_id: str) -> bool:
        with self._lock:
            return any(o.order_id == order_id for o in self._queue)

    def list_orders(self) -> list[Order]:
        with self._lock:
            return list(self._queue)

    def clear(self) -> int:
        with self._lock:
            count = len(self._queue)
            self._queue.clear()
            return count

    # ── Stats ─────────────────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "name":       self._name,
                "size":       len(self._queue),
                "max_size":   self._max_size,
                "enqueued":   self._enqueued,
                "dequeued":   self._dequeued,
                "created_at": self._created_at,
            }
