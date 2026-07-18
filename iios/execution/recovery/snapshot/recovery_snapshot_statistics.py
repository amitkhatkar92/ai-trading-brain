"""
iios/execution/recovery/snapshot/recovery_snapshot_statistics.py
================================================================
RecoverySnapshotStatistics — thread-safe statistics for the Snapshot
subsystem.

C7 Execution Recovery & Resilience — Phase 1, Module 5
"""
from __future__ import annotations

import threading
from typing import Any, Dict


class RecoverySnapshotStatistics:
    """
    Thread-safe statistics tracker for the Snapshot subsystem.

    Tracks:
      • snapshots_created / published / archived
      • validation success and failure counts
      • average build time
      • average snapshot size
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._created:          int   = 0
        self._published:        int   = 0
        self._archived:         int   = 0
        self._validation_passed: int  = 0
        self._validation_failed: int  = 0
        self._build_count:      int   = 0
        self._total_build_ms:   float = 0.0
        self._size_count:       int   = 0
        self._total_size_bytes: int   = 0

    # ── Mutating ──────────────────────────────────────────────────────────────

    def record_created(self) -> None:
        with self._lock:
            self._created += 1

    def record_published(self) -> None:
        with self._lock:
            self._published += 1

    def record_archived(self) -> None:
        with self._lock:
            self._archived += 1

    def record_validation_run(self, *, passed: bool) -> None:
        with self._lock:
            if passed:
                self._validation_passed += 1
            else:
                self._validation_failed += 1

    def record_build_time(self, ms: float) -> None:
        with self._lock:
            self._build_count += 1
            self._total_build_ms += ms

    def record_snapshot_size(self, size_bytes: int) -> None:
        with self._lock:
            self._size_count += 1
            self._total_size_bytes += size_bytes

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def snapshots_created(self) -> int:
        with self._lock:
            return self._created

    @property
    def snapshots_published(self) -> int:
        with self._lock:
            return self._published

    @property
    def snapshots_archived(self) -> int:
        with self._lock:
            return self._archived

    @property
    def validation_success_rate(self) -> float:
        with self._lock:
            total = self._validation_passed + self._validation_failed
            if total == 0:
                return 0.0
            return self._validation_passed / total

    @property
    def average_build_time_ms(self) -> float:
        with self._lock:
            if self._build_count == 0:
                return 0.0
            return self._total_build_ms / self._build_count

    @property
    def average_snapshot_size_bytes(self) -> float:
        with self._lock:
            if self._size_count == 0:
                return 0.0
            return self._total_size_bytes / self._size_count

    # ── Copy / reset ──────────────────────────────────────────────────────────

    def copy(self) -> "RecoverySnapshotStatistics":
        """Return a detached copy of the current statistics."""
        with self._lock:
            other = RecoverySnapshotStatistics()
            other._created           = self._created
            other._published         = self._published
            other._archived          = self._archived
            other._validation_passed = self._validation_passed
            other._validation_failed = self._validation_failed
            other._build_count       = self._build_count
            other._total_build_ms    = self._total_build_ms
            other._size_count        = self._size_count
            other._total_size_bytes  = self._total_size_bytes
        return other

    def reset(self) -> None:
        """Reset all counters to zero."""
        with self._lock:
            self._created           = 0
            self._published         = 0
            self._archived          = 0
            self._validation_passed = 0
            self._validation_failed = 0
            self._build_count       = 0
            self._total_build_ms    = 0.0
            self._size_count        = 0
            self._total_size_bytes  = 0

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "snapshots_created":           self._created,
                "snapshots_published":         self._published,
                "snapshots_archived":          self._archived,
                "validation_success_rate":     self.validation_success_rate,
                "average_build_time_ms":       self.average_build_time_ms,
                "average_snapshot_size_bytes": self.average_snapshot_size_bytes,
            }
