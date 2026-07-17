"""iios/execution/gateway/engine/gateway_statistics.py
==================================================
GatewayEngineStatistics — aggregated counters and averages for the
Execution Gateway Engine.

C6 Execution Intelligence — Phase 5, Module 2
"""
from __future__ import annotations

import copy
import time
from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class GatewayEngineStatistics:
    """
    Mutable statistics accumulator for the GatewayEngine.

    All numeric fields start at zero and are incremented as requests
    progress through the workflow.  Thread safety is the manager's
    responsibility.
    """

    # ── Request counts ────────────────────────────────────────────────────────
    requests_received:   int = 0
    requests_queued:     int = 0
    requests_dispatched: int = 0
    requests_completed:  int = 0
    requests_failed:     int = 0
    requests_cancelled:  int = 0

    # ── Retry counts ─────────────────────────────────────────────────────────
    retries_attempted:  int = 0
    retries_succeeded:  int = 0
    retries_exhausted:  int = 0

    # ── Timing accumulation ───────────────────────────────────────────────────
    total_queue_time_ms:     float = 0.0
    total_dispatch_time_ms:  float = 0.0
    total_lifecycle_time_ms: float = 0.0

    # ── Timestamp ─────────────────────────────────────────────────────────────
    last_updated_at: float = field(default_factory=time.time)

    # ── Derived ───────────────────────────────────────────────────────────────

    @property
    def requests_ended(self) -> int:
        return self.requests_completed + self.requests_failed + self.requests_cancelled

    @property
    def completion_rate(self) -> float:
        ended = self.requests_ended
        return self.requests_completed / ended if ended else 0.0

    @property
    def failure_rate(self) -> float:
        ended = self.requests_ended
        return self.requests_failed / ended if ended else 0.0

    @property
    def cancellation_rate(self) -> float:
        ended = self.requests_ended
        return self.requests_cancelled / ended if ended else 0.0

    @property
    def average_queue_time_ms(self) -> float:
        n = self.requests_queued
        return self.total_queue_time_ms / n if n else 0.0

    @property
    def average_dispatch_time_ms(self) -> float:
        n = self.requests_dispatched
        return self.total_dispatch_time_ms / n if n else 0.0

    @property
    def average_lifecycle_time_ms(self) -> float:
        ended = self.requests_ended
        return self.total_lifecycle_time_ms / ended if ended else 0.0

    @property
    def gateway_throughput(self) -> float:
        """Requests ended per second (averaged over total lifecycle time)."""
        total_secs = self.total_lifecycle_time_ms / 1_000.0
        if total_secs <= 0.0:
            return 0.0
        return self.requests_ended / total_secs

    # ── Mutators ──────────────────────────────────────────────────────────────

    def record_received(self) -> None:
        self.requests_received += 1
        self.last_updated_at = time.time()

    def record_queued(self, queue_time_ms: float = 0.0) -> None:
        self.requests_queued  += 1
        self.total_queue_time_ms += max(0.0, queue_time_ms)
        self.last_updated_at  = time.time()

    def record_dispatched(self, dispatch_time_ms: float = 0.0) -> None:
        self.requests_dispatched += 1
        self.total_dispatch_time_ms += max(0.0, dispatch_time_ms)
        self.last_updated_at = time.time()

    def record_completed(self, lifecycle_time_ms: float = 0.0) -> None:
        self.requests_completed  += 1
        self.total_lifecycle_time_ms += max(0.0, lifecycle_time_ms)
        self.last_updated_at = time.time()

    def record_failed(self, lifecycle_time_ms: float = 0.0) -> None:
        self.requests_failed     += 1
        self.total_lifecycle_time_ms += max(0.0, lifecycle_time_ms)
        self.last_updated_at = time.time()

    def record_cancelled(self, lifecycle_time_ms: float = 0.0) -> None:
        self.requests_cancelled  += 1
        self.total_lifecycle_time_ms += max(0.0, lifecycle_time_ms)
        self.last_updated_at = time.time()

    def record_retry(self) -> None:
        self.retries_attempted += 1
        self.last_updated_at   = time.time()

    def record_retry_success(self) -> None:
        self.retries_succeeded += 1
        self.last_updated_at   = time.time()

    def record_retry_exhausted(self) -> None:
        self.retries_exhausted += 1
        self.last_updated_at   = time.time()

    def reset(self) -> None:
        self.requests_received   = 0
        self.requests_queued     = 0
        self.requests_dispatched = 0
        self.requests_completed  = 0
        self.requests_failed     = 0
        self.requests_cancelled  = 0
        self.retries_attempted   = 0
        self.retries_succeeded   = 0
        self.retries_exhausted   = 0
        self.total_queue_time_ms     = 0.0
        self.total_dispatch_time_ms  = 0.0
        self.total_lifecycle_time_ms = 0.0
        self.last_updated_at = time.time()

    def copy(self) -> "GatewayEngineStatistics":
        return copy.copy(self)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "requests_received":         self.requests_received,
            "requests_queued":           self.requests_queued,
            "requests_dispatched":       self.requests_dispatched,
            "requests_completed":        self.requests_completed,
            "requests_failed":           self.requests_failed,
            "requests_cancelled":        self.requests_cancelled,
            "requests_ended":            self.requests_ended,
            "retries_attempted":         self.retries_attempted,
            "retries_succeeded":         self.retries_succeeded,
            "retries_exhausted":         self.retries_exhausted,
            "average_queue_time_ms":     self.average_queue_time_ms,
            "average_dispatch_time_ms":  self.average_dispatch_time_ms,
            "average_lifecycle_time_ms": self.average_lifecycle_time_ms,
            "completion_rate":           self.completion_rate,
            "failure_rate":              self.failure_rate,
            "cancellation_rate":         self.cancellation_rate,
            "gateway_throughput":        self.gateway_throughput,
            "last_updated_at":           self.last_updated_at,
        }
