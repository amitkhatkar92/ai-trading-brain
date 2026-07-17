"""iios/execution/gateway/snapshot/gateway_snapshot_statistics.py
==================================================
GatewaySnapshotStatistics — lightweight accumulator for snapshot
module performance and usage metrics.

Thread safety is NOT embedded — the caller (GatewaySnapshotStore)
serialises writes behind its own lock.

C6 Execution Intelligence — Phase 5, Module 5
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class GatewaySnapshotStatistics:
    """
    Mutable accumulator of snapshot module metrics.

    Intended to be owned by GatewaySnapshotStore.  All mutators
    must be called under the store's internal lock.
    """

    snapshots_created:         int   = 0
    snapshots_published:       int   = 0
    snapshots_archived:        int   = 0
    snapshots_retrieved:       int   = 0
    snapshots_cached:          int   = 0
    validation_successes:      int   = 0
    validation_failures:       int   = 0
    total_build_time_ms:       float = 0.0
    total_snapshot_size_bytes: int   = 0
    last_updated_at:           float = field(default_factory=time.time)

    # ── Mutators ──────────────────────────────────────────────────────────────

    def record_created(self, build_time_ms: float = 0.0) -> None:
        self.snapshots_created   += 1
        self.total_build_time_ms += max(0.0, build_time_ms)
        self.last_updated_at      = time.time()

    def record_published(self) -> None:
        self.snapshots_published += 1
        self.last_updated_at      = time.time()

    def record_archived(self) -> None:
        self.snapshots_archived  += 1
        self.last_updated_at      = time.time()

    def record_retrieved(self) -> None:
        self.snapshots_retrieved += 1
        self.last_updated_at      = time.time()

    def record_cached(self) -> None:
        self.snapshots_cached    += 1
        self.last_updated_at      = time.time()

    def record_validation_success(self) -> None:
        self.validation_successes += 1
        self.last_updated_at       = time.time()

    def record_validation_failure(self) -> None:
        self.validation_failures += 1
        self.last_updated_at      = time.time()

    def record_size(self, size_bytes: int) -> None:
        self.total_snapshot_size_bytes += max(0, size_bytes)
        self.last_updated_at            = time.time()

    # ── Derived properties ────────────────────────────────────────────────────

    @property
    def validation_success_rate(self) -> float:
        total = self.validation_successes + self.validation_failures
        if total == 0:
            return 0.0
        return self.validation_successes / total

    @property
    def validation_failure_rate(self) -> float:
        total = self.validation_successes + self.validation_failures
        if total == 0:
            return 0.0
        return self.validation_failures / total

    @property
    def average_build_time_ms(self) -> float:
        if self.snapshots_created == 0:
            return 0.0
        return self.total_build_time_ms / self.snapshots_created

    @property
    def average_snapshot_size_bytes(self) -> float:
        if self.snapshots_published == 0:
            return 0.0
        return self.total_snapshot_size_bytes / self.snapshots_published

    # ── Utilities ─────────────────────────────────────────────────────────────

    def reset(self) -> None:
        self.snapshots_created         = 0
        self.snapshots_published       = 0
        self.snapshots_archived        = 0
        self.snapshots_retrieved       = 0
        self.snapshots_cached          = 0
        self.validation_successes      = 0
        self.validation_failures       = 0
        self.total_build_time_ms       = 0.0
        self.total_snapshot_size_bytes = 0
        self.last_updated_at           = time.time()

    def copy(self) -> "GatewaySnapshotStatistics":
        return GatewaySnapshotStatistics(
            snapshots_created=self.snapshots_created,
            snapshots_published=self.snapshots_published,
            snapshots_archived=self.snapshots_archived,
            snapshots_retrieved=self.snapshots_retrieved,
            snapshots_cached=self.snapshots_cached,
            validation_successes=self.validation_successes,
            validation_failures=self.validation_failures,
            total_build_time_ms=self.total_build_time_ms,
            total_snapshot_size_bytes=self.total_snapshot_size_bytes,
            last_updated_at=self.last_updated_at,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshots_created":         self.snapshots_created,
            "snapshots_published":       self.snapshots_published,
            "snapshots_archived":        self.snapshots_archived,
            "snapshots_retrieved":       self.snapshots_retrieved,
            "snapshots_cached":          self.snapshots_cached,
            "validation_successes":      self.validation_successes,
            "validation_failures":       self.validation_failures,
            "total_build_time_ms":       self.total_build_time_ms,
            "total_snapshot_size_bytes": self.total_snapshot_size_bytes,
            "average_build_time_ms":     self.average_build_time_ms,
            "average_snapshot_size_bytes": self.average_snapshot_size_bytes,
            "validation_success_rate":   self.validation_success_rate,
            "last_updated_at":           self.last_updated_at,
        }
