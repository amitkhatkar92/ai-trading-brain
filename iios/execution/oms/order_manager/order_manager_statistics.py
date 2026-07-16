"""iios/execution/oms/order_manager/order_manager_statistics.py
==================================================
Statistics for the Order Manager.

C6 Execution Intelligence — Phase 2, Module 1
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class OrderManagerStatistics:
    """
    Thread-safe aggregate statistics for the Order Manager.
    """

    created_at: float = field(default_factory=time.time)

    # Order counters
    orders_created:    int = 0
    orders_active:     int = 0
    orders_completed:  int = 0
    orders_cancelled:  int = 0
    orders_rejected:   int = 0
    orders_failed:     int = 0
    orders_archived:   int = 0
    orders_suspended:  int = 0

    # Peak
    peak_active_orders: int = 0

    # Timing totals (ms)
    _total_processing_ms: float = field(default=0.0, repr=False)
    _processed_count:     int   = field(default=0,   repr=False)

    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    # ── Mutation ──────────────────────────────────────────────────────────────

    def record_registered(self) -> None:
        with self._lock:
            self.orders_created += 1
            self.orders_active  += 1
            if self.orders_active > self.peak_active_orders:
                self.peak_active_orders = self.orders_active

    def record_completed(self, processing_ms: float = 0.0) -> None:
        with self._lock:
            self.orders_completed  += 1
            self.orders_active     = max(0, self.orders_active - 1)
            self._total_processing_ms += processing_ms
            self._processed_count  += 1

    def record_cancelled(self) -> None:
        with self._lock:
            self.orders_cancelled += 1
            self.orders_active    = max(0, self.orders_active - 1)

    def record_rejected(self) -> None:
        with self._lock:
            self.orders_rejected += 1
            self.orders_active   = max(0, self.orders_active - 1)

    def record_failed(self) -> None:
        with self._lock:
            self.orders_failed += 1
            self.orders_active  = max(0, self.orders_active - 1)

    def record_archived(self) -> None:
        with self._lock:
            self.orders_archived += 1

    def record_suspended(self) -> None:
        with self._lock:
            self.orders_suspended += 1

    def record_resumed(self) -> None:
        with self._lock:
            self.orders_suspended = max(0, self.orders_suspended - 1)

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def avg_processing_time_ms(self) -> float:
        if self._processed_count == 0:
            return 0.0
        return self._total_processing_ms / self._processed_count

    @property
    def total_terminal(self) -> int:
        return self.orders_completed + self.orders_failed

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "created_at":            self.created_at,
            "orders_created":        self.orders_created,
            "orders_active":         self.orders_active,
            "orders_completed":      self.orders_completed,
            "orders_cancelled":      self.orders_cancelled,
            "orders_rejected":       self.orders_rejected,
            "orders_failed":         self.orders_failed,
            "orders_archived":       self.orders_archived,
            "orders_suspended":      self.orders_suspended,
            "peak_active_orders":    self.peak_active_orders,
            "avg_processing_time_ms": round(self.avg_processing_time_ms, 2),
        }
