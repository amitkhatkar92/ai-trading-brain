"""iios/execution/positions/snapshot/position_snapshot_statistics.py
==================================================
SnapshotStatistics — mutable counters and derived metrics for the
Position Snapshot subsystem.

C6 Execution Intelligence — Phase 3, Module 5
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class SnapshotStatistics:
    """
    Mutable statistics accumulator for the PositionSnapshotStore.

    Thread safety is the caller's responsibility.
    """

    # ── Operation counters ────────────────────────────────────────────────────
    snapshots_created:   int = 0
    snapshots_published: int = 0
    snapshots_archived:  int = 0
    snapshots_retrieved: int = 0
    snapshots_cached:    int = 0

    # ── Validation counters ───────────────────────────────────────────────────
    validation_successes: int = 0
    validation_failures:  int = 0

    # ── Build timing (for averages) ───────────────────────────────────────────
    total_build_time_ms:  float = 0.0
    _build_count:         int   = field(default=0, repr=False)

    # ── Approximate size tracking ─────────────────────────────────────────────
    total_snapshot_fields: int = 0   # proxy for size (each snapshot has ~35 fields)

    # ── Timestamp ─────────────────────────────────────────────────────────────
    last_updated_at: float = field(default_factory=time.time)

    # ── Derived properties ────────────────────────────────────────────────────

    @property
    def average_build_time_ms(self) -> float:
        if self._build_count == 0:
            return 0.0
        return self.total_build_time_ms / self._build_count

    @property
    def validation_success_rate(self) -> float:
        total = self.validation_successes + self.validation_failures
        if total == 0:
            return 1.0
        return self.validation_successes / total

    @property
    def average_snapshot_fields(self) -> float:
        if self.snapshots_created == 0:
            return 0.0
        return self.total_snapshot_fields / self.snapshots_created

    # ── Mutation helpers ──────────────────────────────────────────────────────

    def record_created(self, build_time_ms: float = 0.0) -> None:
        self.snapshots_created  += 1
        self.total_build_time_ms += build_time_ms
        self._build_count        += 1
        self.total_snapshot_fields += 35   # approximate per-snapshot field count
        self.last_updated_at     = time.time()

    def record_published(self) -> None:
        self.snapshots_published += 1
        self.last_updated_at      = time.time()

    def record_archived(self) -> None:
        self.snapshots_archived += 1
        self.last_updated_at     = time.time()

    def record_retrieved(self) -> None:
        self.snapshots_retrieved += 1
        self.last_updated_at      = time.time()

    def record_cached(self) -> None:
        self.snapshots_cached += 1
        self.last_updated_at   = time.time()

    def record_validation_success(self) -> None:
        self.validation_successes += 1
        self.last_updated_at       = time.time()

    def record_validation_failure(self) -> None:
        self.validation_failures += 1
        self.last_updated_at      = time.time()

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshots_created":       self.snapshots_created,
            "snapshots_published":     self.snapshots_published,
            "snapshots_archived":      self.snapshots_archived,
            "snapshots_retrieved":     self.snapshots_retrieved,
            "snapshots_cached":        self.snapshots_cached,
            "validation_successes":    self.validation_successes,
            "validation_failures":     self.validation_failures,
            "average_build_time_ms":   self.average_build_time_ms,
            "validation_success_rate": self.validation_success_rate,
            "last_updated_at":         self.last_updated_at,
        }
