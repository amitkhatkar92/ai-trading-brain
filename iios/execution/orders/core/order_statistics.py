"""iios/execution/orders/core/order_statistics.py

Aggregate OMS operational statistics — thread-safe counters.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class OrderStatistics:
    """Snapshot of OMS operational metrics."""

    orders_total:      int   = 0
    orders_draft:      int   = 0
    orders_created:    int   = 0
    orders_validated:  int   = 0
    orders_approved:   int   = 0
    orders_queued:     int   = 0
    orders_submitted:  int   = 0
    orders_acked:      int   = 0
    orders_partial:    int   = 0
    orders_filled:     int   = 0
    orders_cancelled:  int   = 0
    orders_expired:    int   = 0
    orders_rejected:   int   = 0
    orders_failed:     int   = 0
    orders_archived:   int   = 0

    total_fill_value:  float = 0.0
    total_commission:  float = 0.0

    fill_rate:         float = 0.0    # orders_filled / orders_submitted
    cancel_rate:       float = 0.0    # orders_cancelled / orders_submitted
    reject_rate:       float = 0.0

    avg_fill_latency_ms:   float = 0.0
    p99_fill_latency_ms:   float = 0.0
    total_fill_latency_ms: float = 0.0
    fill_latency_samples:  int   = 0

    uptime_sec:        float = 0.0
    started_at:        float = field(default_factory=time.time)

    def record_fill_latency(self, latency_ms: float) -> None:
        n = self.fill_latency_samples
        self.total_fill_latency_ms += latency_ms
        self.fill_latency_samples   = n + 1
        self.avg_fill_latency_ms    = self.total_fill_latency_ms / self.fill_latency_samples
        # Simple p99 approximation (update high-water mark if in top 1%)
        if latency_ms > self.p99_fill_latency_ms:
            self.p99_fill_latency_ms = latency_ms

    def recompute_rates(self) -> None:
        sub = self.orders_submitted
        if sub > 0:
            self.fill_rate   = self.orders_filled    / sub
            self.cancel_rate = self.orders_cancelled / sub
            self.reject_rate = self.orders_rejected  / sub

    def to_dict(self) -> dict[str, Any]:
        self.uptime_sec = time.time() - self.started_at
        self.recompute_rates()
        return {
            "orders_total":           self.orders_total,
            "orders_filled":          self.orders_filled,
            "orders_cancelled":       self.orders_cancelled,
            "orders_rejected":        self.orders_rejected,
            "orders_failed":          self.orders_failed,
            "orders_archived":        self.orders_archived,
            "total_fill_value":       self.total_fill_value,
            "total_commission":       self.total_commission,
            "fill_rate":              round(self.fill_rate, 4),
            "cancel_rate":            round(self.cancel_rate, 4),
            "reject_rate":            round(self.reject_rate, 4),
            "avg_fill_latency_ms":    round(self.avg_fill_latency_ms, 2),
            "p99_fill_latency_ms":    round(self.p99_fill_latency_ms, 2),
            "uptime_sec":             round(self.uptime_sec, 2),
        }


class LiveOrderStatistics:
    """Thread-safe wrapper around OrderStatistics for live updates."""

    def __init__(self) -> None:
        self._stats = OrderStatistics()
        self._lock  = threading.Lock()

    def increment(self, field_name: str, by: float = 1) -> None:
        with self._lock:
            old = getattr(self._stats, field_name, 0)
            setattr(self._stats, field_name, old + by)

    def record_fill_latency(self, latency_ms: float) -> None:
        with self._lock:
            self._stats.record_fill_latency(latency_ms)

    def snapshot(self) -> OrderStatistics:
        with self._lock:
            # Return a shallow copy so the caller doesn't hold the lock
            import copy
            return copy.copy(self._stats)

    def to_dict(self) -> dict[str, Any]:
        with self._lock:
            return self._stats.to_dict()

    def reset(self) -> None:
        with self._lock:
            self._stats = OrderStatistics()
