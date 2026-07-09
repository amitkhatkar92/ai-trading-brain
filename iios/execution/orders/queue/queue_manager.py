"""iios/execution/orders/queue/queue_manager.py

Manages multiple named queues: FIFO, priority, retry, delayed, dead-letter.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any

from ..order_constants import DEFAULT_MAX_QUEUE_SIZE, DEFAULT_RETRY_LIMIT, QueueType
from ..core.order import Order
from ..order_exceptions import QueueFullError, QueueNotFoundError
from .order_queue import OrderQueue
from .priority_queue import PriorityQueue

_log = logging.getLogger(__name__)

_FIFO_NAME       = "fifo"
_PRIORITY_NAME   = "priority"
_RETRY_NAME      = "retry"
_DEAD_LETTER_NAME = "dead_letter"
_DELAYED_NAME    = "delayed"


class QueueManager:
    """Central registry and router for all OMS queues."""

    def __init__(self, max_size: int = DEFAULT_MAX_QUEUE_SIZE) -> None:
        self._max_size    = max_size
        self._lock        = threading.RLock()

        # Named FIFO queues
        self._queues:  dict[str, OrderQueue]  = {
            _FIFO_NAME:        OrderQueue(_FIFO_NAME,        max_size),
            _RETRY_NAME:       OrderQueue(_RETRY_NAME,       max_size),
            _DEAD_LETTER_NAME: OrderQueue(_DEAD_LETTER_NAME, max_size),
            _DELAYED_NAME:     OrderQueue(_DELAYED_NAME,     max_size),
        }

        # Priority queue (singleton)
        self._priority_queue = PriorityQueue(_PRIORITY_NAME, max_size)

        # Delayed queue: (release_at, order)
        self._delayed_items: list[tuple[float, Order]] = []

    # ── Enqueue ───────────────────────────────────────────────────────────────

    def enqueue(self, order: Order, queue_type: QueueType = QueueType.PRIORITY) -> None:
        """Route order to the appropriate queue."""
        if queue_type == QueueType.PRIORITY:
            self._priority_queue.enqueue(order)
        elif queue_type == QueueType.FIFO:
            self._queues[_FIFO_NAME].enqueue(order)
        elif queue_type == QueueType.RETRY:
            if order.retry_count < DEFAULT_RETRY_LIMIT:
                order.retry_count += 1
                self._queues[_RETRY_NAME].enqueue(order)
            else:
                _log.warning("Order %s exhausted retries — moving to dead-letter", order.order_id)
                self._queues[_DEAD_LETTER_NAME].enqueue(order)
        elif queue_type == QueueType.DEAD_LETTER:
            self._queues[_DEAD_LETTER_NAME].enqueue(order)
        elif queue_type == QueueType.DELAYED:
            # Requires metadata["release_after_sec"]
            delay = order.metadata.get("release_after_sec", 0)
            release_at = time.time() + float(delay)
            with self._lock:
                self._delayed_items.append((release_at, order))
        else:
            # Default fallback: priority
            self._priority_queue.enqueue(order)

    # ── Dequeue ───────────────────────────────────────────────────────────────

    def dequeue(self, queue_type: QueueType = QueueType.PRIORITY) -> Order | None:
        if queue_type == QueueType.PRIORITY:
            return self._priority_queue.dequeue()
        elif queue_type == QueueType.FIFO:
            return self._queues[_FIFO_NAME].dequeue()
        elif queue_type == QueueType.RETRY:
            return self._queues[_RETRY_NAME].dequeue()
        elif queue_type == QueueType.DEAD_LETTER:
            return self._queues[_DEAD_LETTER_NAME].dequeue()
        return None

    def dequeue_ready_delayed(self) -> list[Order]:
        """Return all delayed orders whose release_at has passed."""
        now = time.time()
        ready: list[Order] = []
        with self._lock:
            remaining = []
            for release_at, order in self._delayed_items:
                if now >= release_at:
                    ready.append(order)
                else:
                    remaining.append((release_at, order))
            self._delayed_items = remaining
        return ready

    # ── Removal ───────────────────────────────────────────────────────────────

    def remove(self, order_id: str) -> bool:
        """Remove an order from any queue. Returns True if found."""
        if self._priority_queue.remove(order_id):
            return True
        for q in self._queues.values():
            if q.remove(order_id):
                return True
        return False

    # ── Custom queues ─────────────────────────────────────────────────────────

    def create_queue(self, name: str, max_size: int | None = None) -> OrderQueue:
        with self._lock:
            q = OrderQueue(name, max_size or self._max_size)
            self._queues[name] = q
            return q

    def get_queue(self, name: str) -> OrderQueue:
        with self._lock:
            q = self._queues.get(name)
            if q is None:
                raise QueueNotFoundError(queue_name=name)
            return q

    # ── Stats ─────────────────────────────────────────────────────────────────

    def total_pending(self) -> int:
        total = len(self._priority_queue)
        for q in self._queues.values():
            total += len(q)
        with self._lock:
            total += len(self._delayed_items)
        return total

    def stats(self) -> dict[str, Any]:
        s = {
            "priority":    self._priority_queue.stats(),
            "delayed_count": len(self._delayed_items),
        }
        for name, q in self._queues.items():
            s[name] = q.stats()
        return s
