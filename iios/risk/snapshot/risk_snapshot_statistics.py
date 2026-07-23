"""
risk_snapshot_statistics.py — iios.risk.snapshot
==================================================
Thread-safe running statistics for the Risk Snapshot Framework.

C11 Risk Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

import threading
import time
from typing import Any, Dict


class RiskSnapshotStatistics:
    """
    Thread-safe running statistics for the snapshot framework.

    Tracks:
      Snapshots Built, Snapshots Published, Snapshots Superseded,
      Snapshots Archived, Snapshots Failed, Snapshots Retrieved,
      Average Build Time, Cache Hit Rate.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._reset()

    # ------------------------------------------------------------------
    # Internal reset
    # ------------------------------------------------------------------

    def _reset(self) -> None:
        self._built:      int   = 0
        self._published:  int   = 0
        self._superseded: int   = 0
        self._archived:   int   = 0
        self._failed:     int   = 0
        self._retrieved:  int   = 0
        self._validated:  int   = 0
        self._bundled:    int   = 0
        self._total_build_s: float = 0.0
        self._timed_builds:  int   = 0
        self._reset_at: float = time.time()

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record_built(self) -> None:
        with self._lock:
            self._built += 1

    def record_published(self) -> None:
        with self._lock:
            self._published += 1

    def record_superseded(self) -> None:
        with self._lock:
            self._superseded += 1

    def record_archived(self) -> None:
        with self._lock:
            self._archived += 1

    def record_failed(self) -> None:
        with self._lock:
            self._failed += 1

    def record_retrieved(self) -> None:
        with self._lock:
            self._retrieved += 1

    def record_validated(self) -> None:
        with self._lock:
            self._validated += 1

    def record_bundled(self) -> None:
        with self._lock:
            self._bundled += 1

    def record_build_time(self, elapsed_s: float) -> None:
        with self._lock:
            self._total_build_s += elapsed_s
            self._timed_builds  += 1

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            avg = (
                self._total_build_s / self._timed_builds
                if self._timed_builds > 0 else 0.0
            )
            return {
                "built":          self._built,
                "published":      self._published,
                "superseded":     self._superseded,
                "archived":       self._archived,
                "failed":         self._failed,
                "retrieved":      self._retrieved,
                "validated":      self._validated,
                "bundled":        self._bundled,
                "avg_build_s":    round(avg, 6),
                "reset_at":       self._reset_at,
            }

    def total_built(self) -> int:
        with self._lock:
            return self._built

    def total_published(self) -> int:
        with self._lock:
            return self._published

    def total_failed(self) -> int:
        with self._lock:
            return self._failed

    def reset(self) -> None:
        with self._lock:
            self._reset()
