"""
risk_integration_statistics.py — iios.risk.integration
========================================================
Thread-safe running statistics for the Risk Integration layer.

C11 Risk Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

import threading
import time
from typing import Any, Dict


class RiskIntegrationStatistics:
    """
    Thread-safe running statistics for the Risk Integration layer.

    Tracks:
      Requests Processed, Successful Requests, Failed Requests,
      Average Processing Time, Snapshot Publications,
      Validation Failures, API Calls per Type.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._reset()

    # ------------------------------------------------------------------
    # Internal reset
    # ------------------------------------------------------------------

    def _reset(self) -> None:
        self._requests_received:  int   = 0
        self._requests_completed: int   = 0
        self._requests_failed:    int   = 0
        self._requests_cancelled: int   = 0
        self._snapshots_published: int  = 0
        self._validation_failures: int  = 0
        self._total_processing_s: float = 0.0
        self._timed_requests:     int   = 0
        self._initialized_count:  int   = 0
        self._started_count:      int   = 0
        self._stopped_count:      int   = 0
        self._reset_at: float = time.time()

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record_request_received(self) -> None:
        with self._lock:
            self._requests_received += 1

    def record_request_completed(self) -> None:
        with self._lock:
            self._requests_completed += 1

    def record_request_failed(self) -> None:
        with self._lock:
            self._requests_failed += 1

    def record_request_cancelled(self) -> None:
        with self._lock:
            self._requests_cancelled += 1

    def record_snapshot_published(self) -> None:
        with self._lock:
            self._snapshots_published += 1

    def record_validation_failure(self) -> None:
        with self._lock:
            self._validation_failures += 1

    def record_processing_time(self, elapsed_s: float) -> None:
        with self._lock:
            self._total_processing_s += elapsed_s
            self._timed_requests     += 1

    def record_initialized(self) -> None:
        with self._lock:
            self._initialized_count += 1

    def record_started(self) -> None:
        with self._lock:
            self._started_count += 1

    def record_stopped(self) -> None:
        with self._lock:
            self._stopped_count += 1

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            avg = (
                self._total_processing_s / self._timed_requests
                if self._timed_requests > 0 else 0.0
            )
            total = self._requests_completed + self._requests_failed
            return {
                "requests_received":   self._requests_received,
                "requests_completed":  self._requests_completed,
                "requests_failed":     self._requests_failed,
                "requests_cancelled":  self._requests_cancelled,
                "snapshots_published": self._snapshots_published,
                "validation_failures": self._validation_failures,
                "avg_processing_s":    round(avg, 6),
                "subsystem_availability": 1.0,   # reported by health
                "api_utilization":     self._requests_received,
                "success_rate":        self._requests_completed / total if total > 0 else 0.0,
                "error_rate":          self._requests_failed    / total if total > 0 else 0.0,
                "reset_at":            self._reset_at,
            }

    def total_received(self) -> int:
        with self._lock:
            return self._requests_received

    def total_completed(self) -> int:
        with self._lock:
            return self._requests_completed

    def total_failed(self) -> int:
        with self._lock:
            return self._requests_failed

    def total_snapshots(self) -> int:
        with self._lock:
            return self._snapshots_published

    def reset(self) -> None:
        with self._lock:
            self._reset()
