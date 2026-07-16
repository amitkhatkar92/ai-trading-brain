"""iios/execution/snapshot/execution_snapshot_statistics.py
==================================================
Statistics for the Execution Snapshot package.

SnapshotBuildStats     — per-build timing and outcome.
ExecutionSnapshotStats — aggregate across all snapshots.

C6 Execution Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SnapshotBuildStats:
    """Per-build timing and outcome for a single snapshot."""

    snapshot_id:        str
    execution_id:       str
    built_at:           float = field(default_factory=time.time)
    build_time_ms:      float = 0.0
    validation_passed:  bool  = False
    validation_time_ms: float = 0.0
    snapshot_size_bytes: int  = 0
    sequence_number:    int   = 0
    errors:             tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id":         self.snapshot_id,
            "execution_id":        self.execution_id,
            "built_at":            self.built_at,
            "build_time_ms":       round(self.build_time_ms, 2),
            "validation_passed":   self.validation_passed,
            "validation_time_ms":  round(self.validation_time_ms, 2),
            "snapshot_size_bytes": self.snapshot_size_bytes,
            "sequence_number":     self.sequence_number,
        }


@dataclass
class ExecutionSnapshotStats:
    """Thread-safe aggregate statistics for the snapshot package."""

    created_at: float = field(default_factory=time.time)

    # Counters
    snapshot_count:      int = 0
    publication_count:   int = 0
    validation_success:  int = 0
    validation_failure:  int = 0
    stored_count:        int = 0
    archived_count:      int = 0

    # Timing totals (ms)
    _total_build_ms:      float = field(default=0.0, repr=False)
    _total_validation_ms: float = field(default=0.0, repr=False)

    # Size totals (bytes)
    _total_size_bytes: int = field(default=0, repr=False)

    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    # ── Mutation ──────────────────────────────────────────────────────────────

    def record_build(self, stats: SnapshotBuildStats) -> None:
        with self._lock:
            self.snapshot_count       += 1
            self._total_build_ms      += stats.build_time_ms
            self._total_validation_ms += stats.validation_time_ms
            self._total_size_bytes    += stats.snapshot_size_bytes
            if stats.validation_passed:
                self.validation_success += 1
            else:
                self.validation_failure += 1

    def record_published(self) -> None:
        with self._lock:
            self.publication_count += 1

    def record_stored(self) -> None:
        with self._lock:
            self.stored_count += 1

    def record_archived(self) -> None:
        with self._lock:
            self.archived_count += 1

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def validation_success_rate(self) -> float:
        total = self.validation_success + self.validation_failure
        if total == 0:
            return 0.0
        return self.validation_success / total

    @property
    def avg_build_time_ms(self) -> float:
        if self.snapshot_count == 0:
            return 0.0
        return self._total_build_ms / self.snapshot_count

    @property
    def avg_snapshot_size_bytes(self) -> float:
        if self.snapshot_count == 0:
            return 0.0
        return self._total_size_bytes / self.snapshot_count

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "created_at":              self.created_at,
            "snapshot_count":          self.snapshot_count,
            "publication_count":       self.publication_count,
            "validation_success":      self.validation_success,
            "validation_failure":      self.validation_failure,
            "validation_success_rate": round(self.validation_success_rate, 4),
            "stored_count":            self.stored_count,
            "archived_count":          self.archived_count,
            "avg_build_time_ms":       round(self.avg_build_time_ms, 2),
            "avg_snapshot_size_bytes": round(self.avg_snapshot_size_bytes, 0),
        }
