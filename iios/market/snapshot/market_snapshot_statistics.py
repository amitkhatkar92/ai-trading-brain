"""
market_snapshot_statistics.py — iios.market.snapshot
======================================================
Thread-safe statistics for the Market Snapshot subsystem.

C12 Market Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

import threading
import time
from typing import Any, Dict


class MarketSnapshotStatistics:
    """Thread-safe running statistics for the Market Snapshot subsystem."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._reset()

    def record_snapshot_created(self) -> None:
        with self._lock:
            self._snapshots_created += 1

    def record_snapshot_published(self) -> None:
        with self._lock:
            self._snapshots_published += 1

    def record_snapshot_validated(self) -> None:
        with self._lock:
            self._snapshots_validated += 1

    def record_validation_failed(self) -> None:
        with self._lock:
            self._validation_failures += 1

    def record_snapshot_archived(self) -> None:
        with self._lock:
            self._snapshots_archived += 1

    def record_snapshot_failed(self) -> None:
        with self._lock:
            self._snapshots_failed += 1

    def record_elapsed(self, elapsed_s: float) -> None:
        with self._lock:
            self._total_elapsed_s += elapsed_s
            self._timed_builds    += 1

    def record_cache_hit(self) -> None:
        with self._lock:
            self._cache_hits += 1

    def record_cache_miss(self) -> None:
        with self._lock:
            self._cache_misses += 1

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            avg = (
                self._total_elapsed_s / self._timed_builds
                if self._timed_builds > 0 else 0.0
            )
            elapsed_since_reset = time.time() - self._reset_time
            throughput = (
                self._snapshots_created / elapsed_since_reset
                if elapsed_since_reset > 0 else 0.0
            )
            total_cache = self._cache_hits + self._cache_misses
            return {
                "snapshots_created":    self._snapshots_created,
                "snapshots_published":  self._snapshots_published,
                "snapshots_validated":  self._snapshots_validated,
                "validation_failures":  self._validation_failures,
                "snapshots_archived":   self._snapshots_archived,
                "snapshots_failed":     self._snapshots_failed,
                "average_build_s":      round(avg, 4),
                "snapshot_throughput":  round(throughput, 4),
                "cache_hits":           self._cache_hits,
                "cache_misses":         self._cache_misses,
                "cache_hit_rate":       round(self._cache_hits / total_cache, 4)
                                        if total_cache > 0 else 0.0,
            }

    def reset(self) -> None:
        with self._lock:
            self._reset()

    def _reset(self) -> None:
        self._snapshots_created:    int   = 0
        self._snapshots_published:  int   = 0
        self._snapshots_validated:  int   = 0
        self._validation_failures:  int   = 0
        self._snapshots_archived:   int   = 0
        self._snapshots_failed:     int   = 0
        self._total_elapsed_s:      float = 0.0
        self._timed_builds:         int   = 0
        self._cache_hits:           int   = 0
        self._cache_misses:         int   = 0
        self._reset_time:           float = time.time()
