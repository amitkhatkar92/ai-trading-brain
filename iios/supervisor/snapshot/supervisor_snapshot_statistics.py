"""
supervisor_snapshot_statistics.py — iios.supervisor.snapshot
--------------------------------------------------------------
Thread-safe statistics accumulator for the Supervisor Snapshot subsystem.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 5
"""
from __future__ import annotations

import threading
import time
from typing import Any, Dict

_EMA_ALPHA = 0.1


class SupervisorSnapshotStatistics:
    """Thread-safe statistics for the Supervisor Snapshot subsystem."""

    def __init__(self) -> None:
        self._lock                   = threading.Lock()
        self._builds:          int   = 0
        self._validations:     int   = 0
        self._validation_passes: int = 0
        self._validation_failures: int = 0
        self._publishes:       int   = 0
        self._cache_hits:      int   = 0
        self._cache_misses:    int   = 0
        self._total_build_s:   float = 0.0
        self._ema_build_s:     float = 0.0
        self._total_size_bytes: int  = 0
        self._started_at:      float = time.time()

    # ------------------------------------------------------------------
    # Recorders
    # ------------------------------------------------------------------

    def record_build(self, elapsed_s: float = 0.0, size_bytes: int = 0) -> None:
        with self._lock:
            self._builds += 1
            self._total_build_s  += elapsed_s
            self._total_size_bytes += size_bytes
            if self._ema_build_s == 0.0:
                self._ema_build_s = elapsed_s
            else:
                self._ema_build_s = (
                    _EMA_ALPHA * elapsed_s
                    + (1 - _EMA_ALPHA) * self._ema_build_s
                )

    def record_validation(self, passed: bool = True) -> None:
        with self._lock:
            self._validations += 1
            if passed:
                self._validation_passes += 1
            else:
                self._validation_failures += 1

    def record_publish(self) -> None:
        with self._lock:
            self._publishes += 1

    def record_cache_hit(self) -> None:
        with self._lock:
            self._cache_hits += 1

    def record_cache_miss(self) -> None:
        with self._lock:
            self._cache_misses += 1

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            total_cache = self._cache_hits + self._cache_misses
            return {
                "builds":              self._builds,
                "validations":         self._validations,
                "validation_passes":   self._validation_passes,
                "validation_failures": self._validation_failures,
                "publishes":           self._publishes,
                "cache_hits":          self._cache_hits,
                "cache_misses":        self._cache_misses,
                "cache_hit_rate":      (
                    self._cache_hits / total_cache if total_cache > 0 else 0.0
                ),
                "avg_build_s":         (
                    self._total_build_s / self._builds
                    if self._builds > 0 else 0.0
                ),
                "ema_build_s":         self._ema_build_s,
                "total_size_bytes":    self._total_size_bytes,
                "uptime_s":            time.time() - self._started_at,
            }

    def reset(self) -> None:
        with self._lock:
            self._builds              = 0
            self._validations         = 0
            self._validation_passes   = 0
            self._validation_failures = 0
            self._publishes           = 0
            self._cache_hits          = 0
            self._cache_misses        = 0
            self._total_build_s       = 0.0
            self._ema_build_s         = 0.0
            self._total_size_bytes    = 0
            self._started_at          = time.time()
