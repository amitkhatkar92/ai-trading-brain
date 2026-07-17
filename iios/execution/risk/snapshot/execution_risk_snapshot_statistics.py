"""iios/execution/risk/snapshot/execution_risk_snapshot_statistics.py
==================================================
SnapshotStatistics — runtime metrics for the snapshot subsystem.

C6 Execution Intelligence — Phase 4, Module 5
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class SnapshotStatistics:
    """
    Mutable statistics collected by the SnapshotRegistry.

    Not thread-safe on its own — the registry acquires a lock before
    calling any record_* method.
    """

    snapshots_created:   int   = 0
    snapshots_published: int   = 0
    snapshots_archived:  int   = 0
    snapshots_cached:    int   = 0
    cache_hits:          int   = 0
    cache_misses:        int   = 0
    validation_success:  int   = 0
    validation_failure:  int   = 0
    total_build_time_ms: float = 0.0
    total_size_bytes:    int   = 0

    # ── Computed properties ───────────────────────────────────────────────────

    @property
    def average_build_time_ms(self) -> float:
        if self.snapshots_created == 0:
            return 0.0
        return self.total_build_time_ms / self.snapshots_created

    @property
    def average_snapshot_size_bytes(self) -> float:
        if self.snapshots_created == 0:
            return 0.0
        return self.total_size_bytes / self.snapshots_created

    @property
    def cache_hit_rate(self) -> float:
        total = self.cache_hits + self.cache_misses
        if total == 0:
            return 0.0
        return self.cache_hits / total

    @property
    def validation_pass_rate(self) -> float:
        total = self.validation_success + self.validation_failure
        if total == 0:
            return 0.0
        return self.validation_success / total

    # ── Mutation helpers ──────────────────────────────────────────────────────

    def record_created(self, elapsed_ms: float = 0.0, size_bytes: int = 0) -> None:
        self.snapshots_created   += 1
        self.total_build_time_ms += elapsed_ms
        self.total_size_bytes    += size_bytes

    def record_published(self) -> None:
        self.snapshots_published += 1

    def record_archived(self) -> None:
        self.snapshots_archived += 1

    def record_cached(self) -> None:
        self.snapshots_cached += 1

    def record_cache_hit(self) -> None:
        self.cache_hits += 1

    def record_cache_miss(self) -> None:
        self.cache_misses += 1

    def record_validation_success(self) -> None:
        self.validation_success += 1

    def record_validation_failure(self) -> None:
        self.validation_failure += 1

    def reset(self) -> None:
        self.snapshots_created   = 0
        self.snapshots_published = 0
        self.snapshots_archived  = 0
        self.snapshots_cached    = 0
        self.cache_hits          = 0
        self.cache_misses        = 0
        self.validation_success  = 0
        self.validation_failure  = 0
        self.total_build_time_ms = 0.0
        self.total_size_bytes    = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshots_created":           self.snapshots_created,
            "snapshots_published":         self.snapshots_published,
            "snapshots_archived":          self.snapshots_archived,
            "snapshots_cached":            self.snapshots_cached,
            "cache_hits":                  self.cache_hits,
            "cache_misses":                self.cache_misses,
            "cache_hit_rate":              self.cache_hit_rate,
            "validation_success":          self.validation_success,
            "validation_failure":          self.validation_failure,
            "validation_pass_rate":        self.validation_pass_rate,
            "total_build_time_ms":         self.total_build_time_ms,
            "average_build_time_ms":       self.average_build_time_ms,
            "total_size_bytes":            self.total_size_bytes,
            "average_snapshot_size_bytes": self.average_snapshot_size_bytes,
        }

    def copy(self) -> "SnapshotStatistics":
        s = SnapshotStatistics()
        s.snapshots_created   = self.snapshots_created
        s.snapshots_published = self.snapshots_published
        s.snapshots_archived  = self.snapshots_archived
        s.snapshots_cached    = self.snapshots_cached
        s.cache_hits          = self.cache_hits
        s.cache_misses        = self.cache_misses
        s.validation_success  = self.validation_success
        s.validation_failure  = self.validation_failure
        s.total_build_time_ms = self.total_build_time_ms
        s.total_size_bytes    = self.total_size_bytes
        return s
