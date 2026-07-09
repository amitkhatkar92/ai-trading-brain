"""iios/execution/orders/tracking/status_tracker.py

Aggregate status counters — how many orders are in each status right now.
"""
from __future__ import annotations

import threading
from collections import defaultdict
from typing import Any

from ..order_constants import OrderStatus


class StatusTracker:
    """Thread-safe counter by OrderStatus."""

    def __init__(self) -> None:
        self._counts: dict[OrderStatus, int] = defaultdict(int)
        self._lock   = threading.Lock()

    def increment(self, status: OrderStatus) -> None:
        with self._lock:
            self._counts[status] += 1

    def decrement(self, status: OrderStatus) -> None:
        with self._lock:
            if self._counts[status] > 0:
                self._counts[status] -= 1

    def move(self, from_status: OrderStatus, to_status: OrderStatus) -> None:
        with self._lock:
            if self._counts[from_status] > 0:
                self._counts[from_status] -= 1
            self._counts[to_status] += 1

    def count(self, status: OrderStatus) -> int:
        with self._lock:
            return self._counts[status]

    def total(self) -> int:
        with self._lock:
            return sum(self._counts.values())

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return {s.value: c for s, c in self._counts.items() if c > 0}

    def reset(self) -> None:
        with self._lock:
            self._counts.clear()

    def to_dict(self) -> dict[str, Any]:
        return self.snapshot()
