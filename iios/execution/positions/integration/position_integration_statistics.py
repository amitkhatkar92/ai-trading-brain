"""iios/execution/positions/integration/position_integration_statistics.py
==================================================
IntegrationStatistics — mutable operational statistics for the
Position Integration subsystem.

C6 Execution Intelligence — Phase 3, Module 6
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class IntegrationStatistics:
    """
    Mutable operational statistics tracked by the integration layer.

    Thread safety is the caller's responsibility (the manager wraps
    updates in its own lock).
    """

    # ── Counters ──────────────────────────────────────────────────────────────
    positions_managed:     int   = 0
    positions_closed:      int   = 0
    positions_archived:    int   = 0
    snapshots_published:   int   = 0
    validation_successes:  int   = 0
    validation_failures:   int   = 0
    operations_total:      int   = 0
    operations_failed:     int   = 0
    component_failures:    int   = 0

    # ── Timing ────────────────────────────────────────────────────────────────
    total_integration_time_ms: float = 0.0
    _operation_timed_count:    int   = 0

    # ── Health tracking ───────────────────────────────────────────────────────
    last_health_status: str   = "UNKNOWN"
    last_updated_at:    float = field(default_factory=time.time)

    # ── Derived properties ────────────────────────────────────────────────────

    @property
    def average_integration_time_ms(self) -> float:
        if self._operation_timed_count == 0:
            return 0.0
        return self.total_integration_time_ms / self._operation_timed_count

    @property
    def operation_success_rate(self) -> float:
        if self.operations_total == 0:
            return 1.0
        return (self.operations_total - self.operations_failed) / self.operations_total

    @property
    def validation_success_rate(self) -> float:
        total = self.validation_successes + self.validation_failures
        if total == 0:
            return 1.0
        return self.validation_successes / total

    # ── Mutation helpers ──────────────────────────────────────────────────────

    def record_operation(self, elapsed_ms: float = 0.0, *, failed: bool = False) -> None:
        self.operations_total += 1
        if failed:
            self.operations_failed += 1
        if elapsed_ms > 0:
            self.total_integration_time_ms += elapsed_ms
            self._operation_timed_count   += 1
        self.last_updated_at = time.time()

    def record_position_managed(self) -> None:
        self.positions_managed += 1
        self.last_updated_at = time.time()

    def record_position_closed(self) -> None:
        self.positions_closed += 1
        self.last_updated_at = time.time()

    def record_position_archived(self) -> None:
        self.positions_archived += 1
        self.last_updated_at = time.time()

    def record_snapshot_published(self) -> None:
        self.snapshots_published += 1
        self.last_updated_at = time.time()

    def record_validation_success(self) -> None:
        self.validation_successes += 1
        self.last_updated_at = time.time()

    def record_validation_failure(self) -> None:
        self.validation_failures += 1
        self.last_updated_at = time.time()

    def record_component_failure(self) -> None:
        self.component_failures += 1
        self.last_updated_at = time.time()

    def record_health_check(self, status: str) -> None:
        self.last_health_status = status
        self.last_updated_at = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "positions_managed":           self.positions_managed,
            "positions_closed":            self.positions_closed,
            "positions_archived":          self.positions_archived,
            "snapshots_published":         self.snapshots_published,
            "validation_successes":        self.validation_successes,
            "validation_failures":         self.validation_failures,
            "operations_total":            self.operations_total,
            "operations_failed":           self.operations_failed,
            "component_failures":          self.component_failures,
            "total_integration_time_ms":   self.total_integration_time_ms,
            "average_integration_time_ms": self.average_integration_time_ms,
            "operation_success_rate":      self.operation_success_rate,
            "validation_success_rate":     self.validation_success_rate,
            "last_health_status":          self.last_health_status,
            "last_updated_at":             self.last_updated_at,
        }
