"""
portfolio_snapshot_statistics.py — iios.portfolio.snapshot
===========================================================
Thread-safe, lock-protected statistics accumulator for the Portfolio
Snapshot subsystem.

C10 Portfolio Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

import threading
import time
from typing import Any, Dict


class PortfolioSnapshotStatistics:
    """
    Thread-safe statistics accumulator covering the full snapshot
    lifecycle.

    Counters
    --------
    snapshots_created      : Total snapshots built.
    snapshots_published    : Total snapshots published.
    snapshots_archived     : Total snapshots archived.
    validation_successes   : Snapshots that passed all checks.
    validation_failures    : Snapshots that failed at least one check.
    cache_hits             : Cache read hits.
    cache_misses           : Cache read misses.

    Averages
    --------
    avg_build_time_ms      : Rolling average build duration.
    avg_validation_time_ms : Rolling average validation duration.
    avg_snapshot_size_keys : Rolling average number of top-level keys in
                             a snapshot's to_dict() output (proxy for size).
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._reset_counters()

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record_created(self, build_time_ms: float = 0.0) -> None:
        with self._lock:
            self._snapshots_created += 1
            self._total_build_time_ms += build_time_ms
            self._build_samples += 1

    def record_published(self) -> None:
        with self._lock:
            self._snapshots_published += 1

    def record_archived(self) -> None:
        with self._lock:
            self._snapshots_archived += 1

    def record_validation_success(self, duration_ms: float = 0.0) -> None:
        with self._lock:
            self._validation_successes += 1
            self._total_validation_time_ms += duration_ms
            self._validation_samples += 1

    def record_validation_failure(self, duration_ms: float = 0.0) -> None:
        with self._lock:
            self._validation_failures += 1
            self._total_validation_time_ms += duration_ms
            self._validation_samples += 1

    def record_cache_hit(self) -> None:
        with self._lock:
            self._cache_hits += 1

    def record_cache_miss(self) -> None:
        with self._lock:
            self._cache_misses += 1

    def record_snapshot_size(self, key_count: int) -> None:
        with self._lock:
            self._total_size_keys += key_count
            self._size_samples += 1

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def snapshot(self) -> Dict[str, Any]:
        """Return an atomic copy of all statistics."""
        with self._lock:
            avg_build = (
                self._total_build_time_ms / self._build_samples
                if self._build_samples else 0.0
            )
            avg_val = (
                self._total_validation_time_ms / self._validation_samples
                if self._validation_samples else 0.0
            )
            avg_size = (
                self._total_size_keys / self._size_samples
                if self._size_samples else 0.0
            )
            return {
                "snapshots_created":      self._snapshots_created,
                "snapshots_published":    self._snapshots_published,
                "snapshots_archived":     self._snapshots_archived,
                "validation_successes":   self._validation_successes,
                "validation_failures":    self._validation_failures,
                "cache_hits":             self._cache_hits,
                "cache_misses":           self._cache_misses,
                "avg_build_time_ms":      avg_build,
                "avg_validation_time_ms": avg_val,
                "avg_snapshot_size_keys": avg_size,
            }

    def reset(self) -> None:
        with self._lock:
            self._reset_counters()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _reset_counters(self) -> None:
        self._snapshots_created     = 0
        self._snapshots_published   = 0
        self._snapshots_archived    = 0
        self._validation_successes  = 0
        self._validation_failures   = 0
        self._cache_hits            = 0
        self._cache_misses          = 0
        self._total_build_time_ms   = 0.0
        self._build_samples         = 0
        self._total_validation_time_ms = 0.0
        self._validation_samples    = 0
        self._total_size_keys       = 0
        self._size_samples          = 0
