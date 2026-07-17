"""iios/execution/gateway/integration/gateway_integration_statistics.py
==================================================
GatewayIntegrationStatistics — mutable accumulator for
integration-layer metrics.

C6 Execution Intelligence — Phase 5, Module 6
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class GatewayIntegrationStatistics:
    """
    Mutable accumulator for integration-layer counters and timings.

    All mutator calls must be made under the manager's internal lock.
    """

    # ── Request counters ──────────────────────────────────────────────────────
    requests_received:   int   = 0
    requests_validated:  int   = 0
    requests_routed:     int   = 0
    requests_dispatched: int   = 0
    requests_completed:  int   = 0
    requests_failed:     int   = 0
    requests_cancelled:  int   = 0

    # ── Timing totals ─────────────────────────────────────────────────────────
    total_processing_ms: float = 0.0
    total_routing_ms:    float = 0.0
    total_dispatch_ms:   float = 0.0

    # ── Component-level metrics ───────────────────────────────────────────────
    snapshots_published:      int = 0
    health_checks_performed:  int = 0
    validation_failures:      int = 0

    # ── Timestamps ────────────────────────────────────────────────────────────
    last_updated_at: float = field(default_factory=time.time)

    # ── Mutators ──────────────────────────────────────────────────────────────

    def record_received(self) -> None:
        self.requests_received += 1
        self.last_updated_at    = time.time()

    def record_validated(self) -> None:
        self.requests_validated += 1
        self.last_updated_at     = time.time()

    def record_validation_failure(self) -> None:
        self.validation_failures += 1
        self.last_updated_at      = time.time()

    def record_routed(self, routing_ms: float = 0.0) -> None:
        self.requests_routed  += 1
        self.total_routing_ms += max(0.0, routing_ms)
        self.last_updated_at   = time.time()

    def record_dispatched(self, dispatch_ms: float = 0.0) -> None:
        self.requests_dispatched += 1
        self.total_dispatch_ms   += max(0.0, dispatch_ms)
        self.last_updated_at      = time.time()

    def record_completed(self, processing_ms: float = 0.0) -> None:
        self.requests_completed  += 1
        self.total_processing_ms += max(0.0, processing_ms)
        self.last_updated_at      = time.time()

    def record_failed(self) -> None:
        self.requests_failed += 1
        self.last_updated_at  = time.time()

    def record_cancelled(self) -> None:
        self.requests_cancelled += 1
        self.last_updated_at     = time.time()

    def record_snapshot_published(self) -> None:
        self.snapshots_published += 1
        self.last_updated_at      = time.time()

    def record_health_check(self) -> None:
        self.health_checks_performed += 1
        self.last_updated_at          = time.time()

    # ── Derived properties ────────────────────────────────────────────────────

    @property
    def success_rate(self) -> float:
        total = self.requests_completed + self.requests_failed
        if total == 0:
            return 0.0
        return self.requests_completed / total

    @property
    def failure_rate(self) -> float:
        total = self.requests_completed + self.requests_failed
        if total == 0:
            return 0.0
        return self.requests_failed / total

    @property
    def average_processing_ms(self) -> float:
        if self.requests_completed == 0:
            return 0.0
        return self.total_processing_ms / self.requests_completed

    @property
    def average_routing_ms(self) -> float:
        if self.requests_routed == 0:
            return 0.0
        return self.total_routing_ms / self.requests_routed

    @property
    def average_dispatch_ms(self) -> float:
        if self.requests_dispatched == 0:
            return 0.0
        return self.total_dispatch_ms / self.requests_dispatched

    # ── Utilities ─────────────────────────────────────────────────────────────

    def reset(self) -> None:
        self.requests_received    = 0
        self.requests_validated   = 0
        self.requests_routed      = 0
        self.requests_dispatched  = 0
        self.requests_completed   = 0
        self.requests_failed      = 0
        self.requests_cancelled   = 0
        self.total_processing_ms  = 0.0
        self.total_routing_ms     = 0.0
        self.total_dispatch_ms    = 0.0
        self.snapshots_published  = 0
        self.health_checks_performed = 0
        self.validation_failures  = 0
        self.last_updated_at      = time.time()

    def copy(self) -> "GatewayIntegrationStatistics":
        s = GatewayIntegrationStatistics(
            requests_received=self.requests_received,
            requests_validated=self.requests_validated,
            requests_routed=self.requests_routed,
            requests_dispatched=self.requests_dispatched,
            requests_completed=self.requests_completed,
            requests_failed=self.requests_failed,
            requests_cancelled=self.requests_cancelled,
            total_processing_ms=self.total_processing_ms,
            total_routing_ms=self.total_routing_ms,
            total_dispatch_ms=self.total_dispatch_ms,
            snapshots_published=self.snapshots_published,
            health_checks_performed=self.health_checks_performed,
            validation_failures=self.validation_failures,
            last_updated_at=self.last_updated_at,
        )
        return s

    def to_dict(self) -> Dict[str, Any]:
        return {
            "requests_received":       self.requests_received,
            "requests_validated":      self.requests_validated,
            "requests_routed":         self.requests_routed,
            "requests_dispatched":     self.requests_dispatched,
            "requests_completed":      self.requests_completed,
            "requests_failed":         self.requests_failed,
            "requests_cancelled":      self.requests_cancelled,
            "total_processing_ms":     self.total_processing_ms,
            "total_routing_ms":        self.total_routing_ms,
            "total_dispatch_ms":       self.total_dispatch_ms,
            "snapshots_published":     self.snapshots_published,
            "health_checks_performed": self.health_checks_performed,
            "validation_failures":     self.validation_failures,
            "success_rate":            self.success_rate,
            "failure_rate":            self.failure_rate,
            "average_processing_ms":   self.average_processing_ms,
            "average_routing_ms":      self.average_routing_ms,
            "average_dispatch_ms":     self.average_dispatch_ms,
            "last_updated_at":         self.last_updated_at,
        }
