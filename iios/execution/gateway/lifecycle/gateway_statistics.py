"""iios/execution/gateway/lifecycle/gateway_statistics.py
==================================================
GatewayStatistics — aggregated counters and averages for the
Execution Gateway Lifecycle.

C6 Execution Intelligence — Phase 5, Module 1
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class GatewayStatistics:
    """
    Mutable statistics accumulator for the GatewayLifecycle.

    All numeric fields start at zero and are incremented as requests
    change state.  Thread safety is the lifecycle's responsibility.
    """

    # ── Request counts ────────────────────────────────────────────────────────
    requests_received:  int = 0
    requests_completed: int = 0
    requests_failed:    int = 0
    requests_cancelled: int = 0
    requests_archived:  int = 0

    # ── Transition counters ───────────────────────────────────────────────────
    total_transitions: int = 0

    # ── Lifecycle time accumulation ───────────────────────────────────────────
    total_lifecycle_time_ms: float = 0.0

    # ── Timestamp ─────────────────────────────────────────────────────────────
    last_updated_at: float = field(default_factory=time.time)

    # ── Derived ───────────────────────────────────────────────────────────────

    @property
    def requests_ended(self) -> int:
        """Requests that reached an outcome (completed + failed + cancelled)."""
        return self.requests_completed + self.requests_failed + self.requests_cancelled

    @property
    def average_lifecycle_time_ms(self) -> float:
        """Mean lifecycle time in ms for all ended requests."""
        ended = self.requests_ended
        if ended == 0:
            return 0.0
        return self.total_lifecycle_time_ms / ended

    @property
    def completion_rate(self) -> float:
        """Fraction of ended requests that completed successfully."""
        ended = self.requests_ended
        if ended == 0:
            return 0.0
        return self.requests_completed / ended

    @property
    def failure_rate(self) -> float:
        """Fraction of ended requests that failed."""
        ended = self.requests_ended
        if ended == 0:
            return 0.0
        return self.requests_failed / ended

    @property
    def cancellation_rate(self) -> float:
        """Fraction of ended requests that were cancelled."""
        ended = self.requests_ended
        if ended == 0:
            return 0.0
        return self.requests_cancelled / ended

    # ── Mutators ──────────────────────────────────────────────────────────────

    def record_received(self) -> None:
        self.requests_received += 1
        self.last_updated_at    = time.time()

    def record_completed(self, lifecycle_time_ms: float = 0.0) -> None:
        self.requests_completed      += 1
        self.total_lifecycle_time_ms += lifecycle_time_ms
        self.last_updated_at          = time.time()

    def record_failed(self, lifecycle_time_ms: float = 0.0) -> None:
        self.requests_failed         += 1
        self.total_lifecycle_time_ms += lifecycle_time_ms
        self.last_updated_at          = time.time()

    def record_cancelled(self, lifecycle_time_ms: float = 0.0) -> None:
        self.requests_cancelled      += 1
        self.total_lifecycle_time_ms += lifecycle_time_ms
        self.last_updated_at          = time.time()

    def record_archived(self) -> None:
        self.requests_archived += 1
        self.last_updated_at    = time.time()

    def record_transition(self) -> None:
        self.total_transitions += 1
        self.last_updated_at    = time.time()

    def reset(self) -> None:
        """Reset all counters to zero."""
        self.requests_received   = 0
        self.requests_completed  = 0
        self.requests_failed     = 0
        self.requests_cancelled  = 0
        self.requests_archived   = 0
        self.total_transitions   = 0
        self.total_lifecycle_time_ms = 0.0
        self.last_updated_at     = time.time()

    def copy(self) -> "GatewayStatistics":
        """Return an independent copy of these statistics."""
        s = GatewayStatistics(
            requests_received=self.requests_received,
            requests_completed=self.requests_completed,
            requests_failed=self.requests_failed,
            requests_cancelled=self.requests_cancelled,
            requests_archived=self.requests_archived,
            total_transitions=self.total_transitions,
            total_lifecycle_time_ms=self.total_lifecycle_time_ms,
        )
        s.last_updated_at = self.last_updated_at
        return s

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "requests_received":        self.requests_received,
            "requests_completed":       self.requests_completed,
            "requests_failed":          self.requests_failed,
            "requests_cancelled":       self.requests_cancelled,
            "requests_archived":        self.requests_archived,
            "requests_ended":           self.requests_ended,
            "total_transitions":        self.total_transitions,
            "total_lifecycle_time_ms":  self.total_lifecycle_time_ms,
            "average_lifecycle_time_ms": self.average_lifecycle_time_ms,
            "completion_rate":          self.completion_rate,
            "failure_rate":             self.failure_rate,
            "cancellation_rate":        self.cancellation_rate,
            "last_updated_at":          self.last_updated_at,
        }
