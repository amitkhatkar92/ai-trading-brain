"""
knowledge_snapshot_statistics.py — iios.knowledge.snapshot
------------------------------------------------------------
Thread-safe statistics counters for the snapshot system.

Tracks 10 counters:
  1. snapshots_built
  2. snapshots_validated
  3. snapshots_stored
  4. snapshots_retrieved
  5. snapshots_cached
  6. cache_hits
  7. cache_misses
  8. validation_failures
  9. snapshots_expired
 10. snapshots_bundled

C14 Enterprise Knowledge Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict


@dataclass(frozen=True)
class SnapshotStatisticsReport:
    """Point-in-time snapshot of the statistics counters."""
    snapshots_built:      int
    snapshots_validated:  int
    snapshots_stored:     int
    snapshots_retrieved:  int
    snapshots_cached:     int
    cache_hits:           int
    cache_misses:         int
    validation_failures:  int
    snapshots_expired:    int
    snapshots_bundled:    int
    captured_at:          str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshots_built":     self.snapshots_built,
            "snapshots_validated": self.snapshots_validated,
            "snapshots_stored":    self.snapshots_stored,
            "snapshots_retrieved": self.snapshots_retrieved,
            "snapshots_cached":    self.snapshots_cached,
            "cache_hits":          self.cache_hits,
            "cache_misses":        self.cache_misses,
            "validation_failures": self.validation_failures,
            "snapshots_expired":   self.snapshots_expired,
            "snapshots_bundled":   self.snapshots_bundled,
            "captured_at":         self.captured_at,
        }


class KnowledgeSnapshotStatistics:
    """Thread-safe rolling statistics for the snapshot system."""

    def __init__(self) -> None:
        self._lock                = threading.Lock()
        self._snapshots_built     = 0
        self._snapshots_validated = 0
        self._snapshots_stored    = 0
        self._snapshots_retrieved = 0
        self._snapshots_cached    = 0
        self._cache_hits          = 0
        self._cache_misses        = 0
        self._validation_failures = 0
        self._snapshots_expired   = 0
        self._snapshots_bundled   = 0

    # ------------------------------------------------------------------
    # Increment methods
    # ------------------------------------------------------------------

    def record_built(self, n: int = 1) -> None:
        with self._lock:
            self._snapshots_built += n

    def record_validated(self, n: int = 1) -> None:
        with self._lock:
            self._snapshots_validated += n

    def record_stored(self, n: int = 1) -> None:
        with self._lock:
            self._snapshots_stored += n

    def record_retrieved(self, n: int = 1) -> None:
        with self._lock:
            self._snapshots_retrieved += n

    def record_cached(self, n: int = 1) -> None:
        with self._lock:
            self._snapshots_cached += n

    def record_cache_hit(self) -> None:
        with self._lock:
            self._cache_hits += 1

    def record_cache_miss(self) -> None:
        with self._lock:
            self._cache_misses += 1

    def record_validation_failure(self, n: int = 1) -> None:
        with self._lock:
            self._validation_failures += n

    def record_expired(self, n: int = 1) -> None:
        with self._lock:
            self._snapshots_expired += n

    def record_bundled(self, n: int = 1) -> None:
        with self._lock:
            self._snapshots_bundled += n

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------

    def report(self) -> SnapshotStatisticsReport:
        with self._lock:
            return SnapshotStatisticsReport(
                snapshots_built     = self._snapshots_built,
                snapshots_validated = self._snapshots_validated,
                snapshots_stored    = self._snapshots_stored,
                snapshots_retrieved = self._snapshots_retrieved,
                snapshots_cached    = self._snapshots_cached,
                cache_hits          = self._cache_hits,
                cache_misses        = self._cache_misses,
                validation_failures = self._validation_failures,
                snapshots_expired   = self._snapshots_expired,
                snapshots_bundled   = self._snapshots_bundled,
                captured_at         = datetime.now(tz=timezone.utc).isoformat(),
            )

    def reset(self) -> None:
        with self._lock:
            self._snapshots_built     = 0
            self._snapshots_validated = 0
            self._snapshots_stored    = 0
            self._snapshots_retrieved = 0
            self._snapshots_cached    = 0
            self._cache_hits          = 0
            self._cache_misses        = 0
            self._validation_failures = 0
            self._snapshots_expired   = 0
            self._snapshots_bundled   = 0
