"""
iios/execution/analytics/snapshot/analytics_snapshot_statistics.py
==================================================================
AnalyticsSnapshotStatistics — thread-safe counters for the snapshot
subsystem.

Tracks: snapshots created/published/archived, validation results,
average build time, average snapshot size.

C8 Execution Analytics & Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

import threading
from typing import Any, Dict


class AnalyticsSnapshotStatistics:
    """
    Thread-safe counters for the snapshot subsystem.

    Metrics:
      - snapshots_created:    total snapshots built
      - snapshots_published:  snapshots promoted to PUBLISHED state
      - snapshots_archived:   snapshots moved to ARCHIVED state
      - validation_success:   snapshots that passed validation
      - validation_failure:   snapshots that failed validation
      - avg_build_time_ms:    rolling average build time in ms
      - avg_snapshot_size:    rolling average serialised size (bytes)
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self.snapshots_created:   int   = 0
        self.snapshots_published: int   = 0
        self.snapshots_archived:  int   = 0
        self.validation_success:  int   = 0
        self.validation_failure:  int   = 0
        self._total_build_ms:     float = 0.0
        self._build_samples:      int   = 0
        self._total_size:         float = 0.0
        self._size_samples:       int   = 0

    # ── Recording ─────────────────────────────────────────────────────────────

    def record_created(self, build_time_ms: float = 0.0) -> None:
        with self._lock:
            self.snapshots_created += 1
            if build_time_ms > 0.0:
                self._total_build_ms += build_time_ms
                self._build_samples  += 1

    def record_published(self) -> None:
        with self._lock:
            self.snapshots_published += 1

    def record_archived(self) -> None:
        with self._lock:
            self.snapshots_archived += 1

    def record_validation_success(self) -> None:
        with self._lock:
            self.validation_success += 1

    def record_validation_failure(self) -> None:
        with self._lock:
            self.validation_failure += 1

    def record_size(self, size_bytes: int) -> None:
        with self._lock:
            self._total_size   += size_bytes
            self._size_samples += 1

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def avg_build_time_ms(self) -> float:
        with self._lock:
            return self._total_build_ms / self._build_samples if self._build_samples else 0.0

    @property
    def avg_snapshot_size(self) -> float:
        with self._lock:
            return self._total_size / self._size_samples if self._size_samples else 0.0

    @property
    def validation_total(self) -> int:
        with self._lock:
            return self.validation_success + self.validation_failure

    @property
    def validation_success_rate(self) -> float:
        with self._lock:
            total = self.validation_success + self.validation_failure
            return self.validation_success / total if total else 1.0

    # ── Snapshot ──────────────────────────────────────────────────────────────

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "snapshots_created":    self.snapshots_created,
                "snapshots_published":  self.snapshots_published,
                "snapshots_archived":   self.snapshots_archived,
                "validation_success":   self.validation_success,
                "validation_failure":   self.validation_failure,
                "avg_build_time_ms":    self.avg_build_time_ms,
                "avg_snapshot_size":    self.avg_snapshot_size,
                "validation_success_rate": self.validation_success_rate,
            }

    def reset(self) -> None:
        with self._lock:
            self.snapshots_created   = 0
            self.snapshots_published = 0
            self.snapshots_archived  = 0
            self.validation_success  = 0
            self.validation_failure  = 0
            self._total_build_ms     = 0.0
            self._build_samples      = 0
            self._total_size         = 0.0
            self._size_samples       = 0
