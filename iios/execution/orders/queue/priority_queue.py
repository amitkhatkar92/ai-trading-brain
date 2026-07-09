"""iios/execution/orders/queue/priority_queue.py

Thread-safe priority queue backed by Python's heapq.
Orders with lower numeric priority weight are dequeued first.
"""
from __future__ import annotations

import heapq
import itertools
import threading
import time
from typing import Any

from ..order_constants import DEFAULT_MAX_QUEUE_SIZE, PRIORITY_WEIGHT, OrderPriority
from ..core.order import Order
from ..order_exceptions import QueueFullError

# Tie-breaker counter to keep FIFO ordering within same priority
_counter = itertools.count()


class PriorityQueue:
    """Min-heap priority queue where lower weight = higher priority."""

    def __init__(
        self,
        name:     str = "priority",
        max_size: int = DEFAULT_MAX_QUEUE_SIZE,
    ) -> None:
        self._name      = name
        self._max_size  = max_size
        self._heap:     list[tuple[int, int, Order]] = []   # (weight, seq, order)
        self._lock:     threading.RLock = threading.RLock()
        self._seq                       = itertools.count()
        self._enqueued: int = 0
        self._dequeued: int = 0
        self._created_at: float = time.time()

    @property
    def name(self) -> str:
        return self._name

    def _weight(self, priority: OrderPriority) -> int:
        return PRIORITY_WEIGHT.get(priority.value, 2)

    def enqueue(self, order: Order) -> None:
        with self._lock:
            if len(self._heap) >= self._max_size:
                raise QueueFullError(queue_name=self._name, capacity=self._max_size)
            w   = self._weight(order.priority)
            seq = next(self._seq)
            heapq.heappush(self._heap, (w, seq, order))
            self._enqueued += 1

    def dequeue(self) -> Order | None:
        with self._lock:
            if not self._heap:
                return None
            _, _, order = heapq.heappop(self._heap)
            self._dequeued += 1
            return order

    def peek(self) -> Order | None:
        with self._lock:
            if not self._heap:
                return None
            return self._heap[0][2]

    def remove(self, order_id: str) -> bool:
        with self._lock:
            for i, (_, _, o) in enumerate(self._heap):
                if o.order_id == order_id:
                    self._heap.pop(i)
                    heapq.heapify(self._heap)
                    return True
            return False

    def __len__(self) -> int:
        with self._lock:
            return len(self._heap)

    def is_empty(self) -> bool:
        with self._lock:
            return len(self._heap) == 0

    def list_orders(self) -> list[Order]:
        with self._lock:
            return [o for _, _, o in self._heap]

    def clear(self) -> int:
        with self._lock:
            count = len(self._heap)
            self._heap.clear()
            return count

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "name":      self._name,
                "size":      len(self._heap),
                "max_size":  self._max_size,
                "enqueued":  self._enqueued,
                "dequeued":  self._dequeued,
            }
