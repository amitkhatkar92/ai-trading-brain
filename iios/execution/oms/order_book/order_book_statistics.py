"""iios/execution/oms/order_book/order_book_statistics.py
==================================================
OrderBookStatistics — thread-safe aggregate statistics for
the Order Book.

C6 Execution Intelligence — Phase 2, Module 2
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class OrderBookStatistics:
    """Thread-safe aggregate statistics for the Order Book."""

    created_at: float = field(default_factory=time.time)

    # Order counters (by book status)
    orders_added:     int = 0
    orders_active:    int = 0
    orders_completed: int = 0
    orders_cancelled: int = 0
    orders_rejected:  int = 0
    orders_expired:   int = 0
    orders_failed:    int = 0
    orders_removed:   int = 0

    # Lookup performance
    _total_lookup_ms: float = field(default=0.0, repr=False)
    _lookup_count:    int   = field(default=0,   repr=False)

    # Snapshot counters
    snapshots_created: int = 0

    # Peak
    peak_active:      int = 0

    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    # ── Mutation ──────────────────────────────────────────────────────────────

    def record_added(self) -> None:
        with self._lock:
            self.orders_added  += 1
            self.orders_active += 1
            if self.orders_active > self.peak_active:
                self.peak_active = self.orders_active

    def record_status_change(self, old_status: str, new_status: str) -> None:
        with self._lock:
            if old_status == "ACTIVE" and new_status != "ACTIVE":
                self.orders_active = max(0, self.orders_active - 1)
            counter_map = {
                "COMPLETED": "orders_completed",
                "CANCELLED": "orders_cancelled",
                "REJECTED":  "orders_rejected",
                "EXPIRED":   "orders_expired",
                "FAILED":    "orders_failed",
            }
            attr = counter_map.get(new_status)
            if attr:
                setattr(self, attr, getattr(self, attr) + 1)

    def record_removed(self) -> None:
        with self._lock:
            self.orders_removed += 1

    def record_lookup(self, lookup_ms: float) -> None:
        with self._lock:
            self._total_lookup_ms += lookup_ms
            self._lookup_count    += 1

    def record_snapshot(self) -> None:
        with self._lock:
            self.snapshots_created += 1

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def avg_lookup_time_ms(self) -> float:
        if self._lookup_count == 0:
            return 0.0
        return self._total_lookup_ms / self._lookup_count

    @property
    def total_terminal(self) -> int:
        return (
            self.orders_completed
            + self.orders_cancelled
            + self.orders_rejected
            + self.orders_expired
            + self.orders_failed
        )

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "created_at":        self.created_at,
            "orders_added":      self.orders_added,
            "orders_active":     self.orders_active,
            "orders_completed":  self.orders_completed,
            "orders_cancelled":  self.orders_cancelled,
            "orders_rejected":   self.orders_rejected,
            "orders_expired":    self.orders_expired,
            "orders_failed":     self.orders_failed,
            "orders_removed":    self.orders_removed,
            "total_terminal":    self.total_terminal,
            "peak_active":       self.peak_active,
            "avg_lookup_time_ms": round(self.avg_lookup_time_ms, 3),
            "snapshots_created": self.snapshots_created,
        }
