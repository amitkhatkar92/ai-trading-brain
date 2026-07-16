"""iios/execution/oms/order_router/routing_history.py
==================================================
RoutingHistory — append-only, bounded history of RoutingResult objects.

C6 Execution Intelligence — Phase 2, Module 3
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Any, Iterator, Optional

from iios.execution.oms.order_router.constants import DEFAULT_MAX_HISTORY
from iios.execution.oms.order_router.routing_result import RoutingResult


class RoutingHistory:
    """
    Thread-safe, bounded append-only store of RoutingResult objects.

    When the deque is full, the oldest entry is evicted (deque behaviour).
    """

    __slots__ = ("_max_size", "_entries", "_total", "_evicted", "_lock")

    def __init__(self, max_size: int = DEFAULT_MAX_HISTORY) -> None:
        if max_size < 1:
            raise ValueError(f"max_size must be ≥ 1, got {max_size!r}")
        self._max_size = max_size
        self._entries: deque[RoutingResult] = deque(maxlen=max_size)
        self._total   = 0
        self._evicted = 0
        self._lock    = threading.RLock()

    # ── Mutators ──────────────────────────────────────────────────────────────

    def append(self, result: RoutingResult) -> None:
        with self._lock:
            if len(self._entries) == self._max_size:
                self._evicted += 1
            self._entries.append(result)
            self._total += 1

    # ── Accessors ─────────────────────────────────────────────────────────────

    @property
    def total(self) -> int:
        with self._lock:
            return self._total

    @property
    def evicted(self) -> int:
        with self._lock:
            return self._evicted

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._entries)

    def latest(self, n: int = 10) -> list[RoutingResult]:
        with self._lock:
            entries = list(self._entries)
        return entries[-n:]

    def for_order(self, order_id: str) -> list[RoutingResult]:
        with self._lock:
            entries = list(self._entries)
        return [r for r in entries if r.order_id == order_id]

    def for_broker(self, broker_id: str) -> list[RoutingResult]:
        with self._lock:
            entries = list(self._entries)
        return [r for r in entries if r.decision.selected_broker_id == broker_id]

    def successful(self) -> list[RoutingResult]:
        with self._lock:
            entries = list(self._entries)
        return [r for r in entries if r.succeeded]

    def rejected(self) -> list[RoutingResult]:
        with self._lock:
            entries = list(self._entries)
        return [r for r in entries if not r.succeeded]

    def __iter__(self) -> Iterator[RoutingResult]:
        with self._lock:
            snapshot = list(self._entries)
        return iter(snapshot)

    def __len__(self) -> int:
        return self.size

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_size": self._max_size,
            "size":     self.size,
            "total":    self.total,
            "evicted":  self.evicted,
        }
