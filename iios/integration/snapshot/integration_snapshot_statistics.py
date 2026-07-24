"""
integration_snapshot_statistics.py — iios.integration.snapshot
---------------------------------------------------------------
IntegrationSnapshotStatistics — thread-safe counter set that tracks
snapshot lifecycle metrics.

C15 Enterprise Integration & Connectivity — Phase 1, Module 5
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict

from iios.common.logging.logging_manager import get_logger

_log = get_logger(__name__)


@dataclass(frozen=True)
class SnapshotStatisticsReport:
    """Immutable snapshot of all statistics counters."""
    snapshots_created:    int
    snapshots_published:  int
    snapshots_retrieved:  int
    snapshots_archived:   int
    snapshots_expired:    int
    validation_passed:    int
    validation_failed:    int
    cache_hits:           int
    cache_misses:         int
    average_build_time_ms: float
    generated_at:         str

    def as_dict(self) -> Dict[str, Any]:
        return {
            "snapshots_created":    self.snapshots_created,
            "snapshots_published":  self.snapshots_published,
            "snapshots_retrieved":  self.snapshots_retrieved,
            "snapshots_archived":   self.snapshots_archived,
            "snapshots_expired":    self.snapshots_expired,
            "validation_passed":    self.validation_passed,
            "validation_failed":    self.validation_failed,
            "cache_hits":           self.cache_hits,
            "cache_misses":         self.cache_misses,
            "average_build_time_ms": round(self.average_build_time_ms, 3),
            "generated_at":         self.generated_at,
        }


class IntegrationSnapshotStatistics:
    """
    Thread-safe statistics counters for the snapshot module.

    All increment methods are atomic under a single lock.
    """

    def __init__(self) -> None:
        self._created:       int   = 0
        self._published:     int   = 0
        self._retrieved:     int   = 0
        self._archived:      int   = 0
        self._expired:       int   = 0
        self._val_passed:    int   = 0
        self._val_failed:    int   = 0
        self._cache_hits:    int   = 0
        self._cache_misses:  int   = 0
        self._build_total_ms: float = 0.0
        self._build_count:   int   = 0
        self._lock: threading.Lock = threading.Lock()

    def increment_created(self, n: int = 1) -> None:
        with self._lock:
            self._created += n

    def increment_published(self, n: int = 1) -> None:
        with self._lock:
            self._published += n

    def increment_retrieved(self, n: int = 1) -> None:
        with self._lock:
            self._retrieved += n

    def increment_archived(self, n: int = 1) -> None:
        with self._lock:
            self._archived += n

    def increment_expired(self, n: int = 1) -> None:
        with self._lock:
            self._expired += n

    def record_validation(self, passed: bool) -> None:
        with self._lock:
            if passed:
                self._val_passed += 1
            else:
                self._val_failed += 1

    def record_cache_hit(self) -> None:
        with self._lock:
            self._cache_hits += 1

    def record_cache_miss(self) -> None:
        with self._lock:
            self._cache_misses += 1

    def record_build(self, duration_ms: float) -> None:
        with self._lock:
            self._build_total_ms += duration_ms
            self._build_count    += 1

    def snapshot(self) -> SnapshotStatisticsReport:
        """Return an immutable copy of current counters."""
        with self._lock:
            avg = (
                self._build_total_ms / self._build_count
                if self._build_count > 0 else 0.0
            )
            return SnapshotStatisticsReport(
                snapshots_created    = self._created,
                snapshots_published  = self._published,
                snapshots_retrieved  = self._retrieved,
                snapshots_archived   = self._archived,
                snapshots_expired    = self._expired,
                validation_passed    = self._val_passed,
                validation_failed    = self._val_failed,
                cache_hits           = self._cache_hits,
                cache_misses         = self._cache_misses,
                average_build_time_ms = avg,
                generated_at         = datetime.now(tz=timezone.utc).isoformat(),
            )

    def reset(self) -> None:
        """Reset all counters to zero."""
        with self._lock:
            self._created        = 0
            self._published      = 0
            self._retrieved      = 0
            self._archived       = 0
            self._expired        = 0
            self._val_passed     = 0
            self._val_failed     = 0
            self._cache_hits     = 0
            self._cache_misses   = 0
            self._build_total_ms = 0.0
            self._build_count    = 0
