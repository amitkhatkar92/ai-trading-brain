"""iios/execution/oms/order_queue/queue_statistics.py
==================================================
QueueStatistics — thread-safe counters for the Order Queue.

C6 Execution Intelligence — Phase 2, Module 4
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class QueueStatistics:
    """Thread-safe statistics for the Order Queue."""
    _lock: threading.Lock = field(
        default_factory=threading.Lock, repr=False, compare=False
    )

    _queue_size:         int   = 0
    _peak_queue_size:    int   = 0
    _total_enqueued:     int   = 0
    _total_dispatched:   int   = 0
    _total_failed:       int   = 0
    _total_expired:      int   = 0
    _total_retried:      int   = 0
    _total_suspended:    int   = 0
    _total_removed:      int   = 0
    _total_wait_ms:      float = 0.0
    _dispatch_count:     int   = 0   # for avg wait time denominator
    _created_at:         float = field(default_factory=time.time)
    _last_updated_at:    float = field(default_factory=time.time)

    # ── Mutators ──────────────────────────────────────────────────────────────

    def record_enqueue(self) -> None:
        with self._lock:
            self._total_enqueued += 1
            self._queue_size += 1
            if self._queue_size > self._peak_queue_size:
                self._peak_queue_size = self._queue_size
            self._last_updated_at = time.time()

    def record_dispatch(self, wait_ms: float = 0.0) -> None:
        with self._lock:
            self._total_dispatched += 1
            self._queue_size = max(0, self._queue_size - 1)
            self._total_wait_ms += wait_ms
            self._dispatch_count += 1
            self._last_updated_at = time.time()

    def record_failure(self) -> None:
        with self._lock:
            self._total_failed += 1
            self._queue_size = max(0, self._queue_size - 1)
            self._last_updated_at = time.time()

    def record_expiry(self) -> None:
        with self._lock:
            self._total_expired += 1
            self._queue_size = max(0, self._queue_size - 1)
            self._last_updated_at = time.time()

    def record_retry(self) -> None:
        with self._lock:
            self._total_retried += 1
            self._last_updated_at = time.time()

    def record_suspend(self) -> None:
        with self._lock:
            self._total_suspended += 1
            self._last_updated_at = time.time()

    def record_remove(self) -> None:
        with self._lock:
            self._total_removed += 1
            self._queue_size = max(0, self._queue_size - 1)
            self._last_updated_at = time.time()

    def set_queue_size(self, size: int) -> None:
        with self._lock:
            self._queue_size = max(0, size)
            if self._queue_size > self._peak_queue_size:
                self._peak_queue_size = self._queue_size

    # ── Accessors ─────────────────────────────────────────────────────────────

    @property
    def queue_size(self) -> int:
        with self._lock:
            return self._queue_size

    @property
    def peak_queue_size(self) -> int:
        with self._lock:
            return self._peak_queue_size

    @property
    def total_enqueued(self) -> int:
        with self._lock:
            return self._total_enqueued

    @property
    def total_dispatched(self) -> int:
        with self._lock:
            return self._total_dispatched

    @property
    def total_failed(self) -> int:
        with self._lock:
            return self._total_failed

    @property
    def total_expired(self) -> int:
        with self._lock:
            return self._total_expired

    @property
    def total_retried(self) -> int:
        with self._lock:
            return self._total_retried

    @property
    def total_suspended(self) -> int:
        with self._lock:
            return self._total_suspended

    @property
    def total_removed(self) -> int:
        with self._lock:
            return self._total_removed

    @property
    def avg_wait_time_ms(self) -> float:
        with self._lock:
            if self._dispatch_count == 0:
                return 0.0
            return self._total_wait_ms / self._dispatch_count

    def reset(self) -> None:
        with self._lock:
            self._queue_size      = 0
            self._peak_queue_size = 0
            self._total_enqueued  = 0
            self._total_dispatched = 0
            self._total_failed    = 0
            self._total_expired   = 0
            self._total_retried   = 0
            self._total_suspended = 0
            self._total_removed   = 0
            self._total_wait_ms   = 0.0
            self._dispatch_count  = 0
            self._last_updated_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        with self._lock:
            return {
                "queue_size":       self._queue_size,
                "peak_queue_size":  self._peak_queue_size,
                "total_enqueued":   self._total_enqueued,
                "total_dispatched": self._total_dispatched,
                "total_failed":     self._total_failed,
                "total_expired":    self._total_expired,
                "total_retried":    self._total_retried,
                "total_suspended":  self._total_suspended,
                "total_removed":    self._total_removed,
                "avg_wait_time_ms": (
                    self._total_wait_ms / self._dispatch_count
                    if self._dispatch_count > 0 else 0.0
                ),
                "created_at":       self._created_at,
                "last_updated_at":  self._last_updated_at,
            }
