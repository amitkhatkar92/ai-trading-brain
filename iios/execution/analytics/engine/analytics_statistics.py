"""
iios/execution/analytics/engine/analytics_statistics.py
=======================================================
EngineAnalyticsStatistics — thread-safe runtime statistics for the
Execution Analytics Engine.

C8 Execution Analytics & Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import threading
from typing import Any, Dict


class EngineAnalyticsStatistics:
    """
    Thread-safe, in-memory statistics for the Execution Analytics Engine.

    Tracks request counts, pipeline counts, and timing averages.
    """

    def __init__(self) -> None:
        self._lock                        = threading.RLock()
        self._requests_received:    int   = 0
        self._requests_completed:   int   = 0
        self._requests_failed:      int   = 0
        self._requests_rejected:    int   = 0
        self._pipelines_dispatched: int   = 0
        self._pipelines_completed:  int   = 0
        self._pipelines_failed:     int   = 0
        # Timing accumulators
        self._processing_count:     int   = 0
        self._total_processing_ms:  float = 0.0
        self._collection_count:     int   = 0
        self._total_collection_ms:  float = 0.0
        self._dispatch_count:       int   = 0
        self._total_dispatch_ms:    float = 0.0

    # ── Mutating ──────────────────────────────────────────────────────────────

    def record_received(self) -> None:
        with self._lock:
            self._requests_received += 1

    def record_completed(
        self,
        processing_ms: float = 0.0,
        collection_ms: float = 0.0,
        dispatch_ms:   float = 0.0,
    ) -> None:
        with self._lock:
            self._requests_completed += 1
            if processing_ms > 0.0:
                self._processing_count    += 1
                self._total_processing_ms += processing_ms
            if collection_ms > 0.0:
                self._collection_count    += 1
                self._total_collection_ms += collection_ms
            if dispatch_ms > 0.0:
                self._dispatch_count    += 1
                self._total_dispatch_ms += dispatch_ms

    def record_failed(self) -> None:
        with self._lock:
            self._requests_failed += 1

    def record_rejected(self) -> None:
        with self._lock:
            self._requests_rejected += 1

    def record_pipeline_dispatched(self) -> None:
        with self._lock:
            self._pipelines_dispatched += 1

    def record_pipeline_completed(self) -> None:
        with self._lock:
            self._pipelines_completed += 1

    def record_pipeline_failed(self) -> None:
        with self._lock:
            self._pipelines_failed += 1

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def requests_received(self) -> int:
        with self._lock:
            return self._requests_received

    @property
    def requests_completed(self) -> int:
        with self._lock:
            return self._requests_completed

    @property
    def requests_failed(self) -> int:
        with self._lock:
            return self._requests_failed

    @property
    def requests_rejected(self) -> int:
        with self._lock:
            return self._requests_rejected

    @property
    def pipelines_dispatched(self) -> int:
        with self._lock:
            return self._pipelines_dispatched

    @property
    def pipelines_completed(self) -> int:
        with self._lock:
            return self._pipelines_completed

    @property
    def pipelines_failed(self) -> int:
        with self._lock:
            return self._pipelines_failed

    @property
    def average_processing_ms(self) -> float:
        with self._lock:
            if self._processing_count == 0:
                return 0.0
            return self._total_processing_ms / self._processing_count

    @property
    def average_collection_ms(self) -> float:
        with self._lock:
            if self._collection_count == 0:
                return 0.0
            return self._total_collection_ms / self._collection_count

    @property
    def average_dispatch_ms(self) -> float:
        with self._lock:
            if self._dispatch_count == 0:
                return 0.0
            return self._total_dispatch_ms / self._dispatch_count

    @property
    def success_rate(self) -> float:
        """Fraction of completed / (completed + failed).  0.0 if no terminal requests."""
        with self._lock:
            total = self._requests_completed + self._requests_failed
            if total == 0:
                return 0.0
            return self._requests_completed / total

    @property
    def subsystem_availability(self) -> float:
        """Fraction of requests that were NOT rejected.  1.0 if no requests."""
        with self._lock:
            total = self._requests_received
            if total == 0:
                return 1.0
            return max(0.0, (total - self._requests_rejected) / total)

    # ── Utility ───────────────────────────────────────────────────────────────

    def copy(self) -> "EngineAnalyticsStatistics":
        """Return an independent snapshot copy."""
        c = EngineAnalyticsStatistics()
        with self._lock:
            c._requests_received    = self._requests_received
            c._requests_completed   = self._requests_completed
            c._requests_failed      = self._requests_failed
            c._requests_rejected    = self._requests_rejected
            c._pipelines_dispatched = self._pipelines_dispatched
            c._pipelines_completed  = self._pipelines_completed
            c._pipelines_failed     = self._pipelines_failed
            c._processing_count     = self._processing_count
            c._total_processing_ms  = self._total_processing_ms
            c._collection_count     = self._collection_count
            c._total_collection_ms  = self._total_collection_ms
            c._dispatch_count       = self._dispatch_count
            c._total_dispatch_ms    = self._total_dispatch_ms
        return c

    def reset(self) -> None:
        with self._lock:
            self._requests_received    = 0
            self._requests_completed   = 0
            self._requests_failed      = 0
            self._requests_rejected    = 0
            self._pipelines_dispatched = 0
            self._pipelines_completed  = 0
            self._pipelines_failed     = 0
            self._processing_count     = 0
            self._total_processing_ms  = 0.0
            self._collection_count     = 0
            self._total_collection_ms  = 0.0
            self._dispatch_count       = 0
            self._total_dispatch_ms    = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "requests_received":     self.requests_received,
            "requests_completed":    self.requests_completed,
            "requests_failed":       self.requests_failed,
            "requests_rejected":     self.requests_rejected,
            "pipelines_dispatched":  self.pipelines_dispatched,
            "pipelines_completed":   self.pipelines_completed,
            "pipelines_failed":      self.pipelines_failed,
            "average_processing_ms": round(self.average_processing_ms, 3),
            "average_collection_ms": round(self.average_collection_ms, 3),
            "average_dispatch_ms":   round(self.average_dispatch_ms, 3),
            "success_rate":          round(self.success_rate, 4),
            "subsystem_availability":round(self.subsystem_availability, 4),
        }
