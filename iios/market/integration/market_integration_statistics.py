"""
market_integration_statistics.py — iios.market.integration
============================================================
Thread-safe statistics for the Market Integration subsystem.

C12 Market Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

import threading
import time
from typing import Any, Dict


class MarketIntegrationStatistics:
    """Thread-safe running statistics for the Market Integration engine."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._reset()

    # ------------------------------------------------------------------
    # Record methods
    # ------------------------------------------------------------------

    def record_request_received(self) -> None:
        with self._lock:
            self._requests_processed += 1

    def record_request_succeeded(self) -> None:
        with self._lock:
            self._successful_requests += 1

    def record_request_failed(self) -> None:
        with self._lock:
            self._failed_requests += 1

    def record_request_rejected(self) -> None:
        with self._lock:
            self._rejected_requests += 1

    def record_snapshot_published(self) -> None:
        with self._lock:
            self._snapshot_publications += 1

    def record_elapsed(self, elapsed_s: float) -> None:
        with self._lock:
            self._total_elapsed_s += elapsed_s
            self._timed_requests  += 1

    def record_api_call(self, method: str) -> None:
        with self._lock:
            self._api_calls[method] = self._api_calls.get(method, 0) + 1

    def record_validation_failure(self) -> None:
        with self._lock:
            self._validation_failures += 1

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            avg = (
                self._total_elapsed_s / self._timed_requests
                if self._timed_requests > 0 else 0.0
            )
            elapsed_since_reset = time.time() - self._reset_time
            throughput = (
                self._requests_processed / elapsed_since_reset
                if elapsed_since_reset > 0 else 0.0
            )
            total   = self._requests_processed
            avail   = (
                round(self._successful_requests / total, 4)
                if total > 0 else 1.0
            )
            return {
                "requests_processed":    self._requests_processed,
                "successful_requests":   self._successful_requests,
                "failed_requests":       self._failed_requests,
                "rejected_requests":     self._rejected_requests,
                "validation_failures":   self._validation_failures,
                "snapshot_publications": self._snapshot_publications,
                "average_processing_s":  round(avg, 4),
                "request_throughput":    round(throughput, 4),
                "subsystem_availability": avail,
                "api_utilization":       dict(self._api_calls),
            }

    def reset(self) -> None:
        with self._lock:
            self._reset()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _reset(self) -> None:
        self._requests_processed:  int   = 0
        self._successful_requests: int   = 0
        self._failed_requests:     int   = 0
        self._rejected_requests:   int   = 0
        self._validation_failures: int   = 0
        self._snapshot_publications: int = 0
        self._total_elapsed_s:     float = 0.0
        self._timed_requests:      int   = 0
        self._api_calls:           Dict[str, int] = {}
        self._reset_time:          float = time.time()
