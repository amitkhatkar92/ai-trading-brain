"""iios/execution/monitoring/metrics/metrics_statistics.py
==================================================
MetricsStatistics — mutable accumulator for metrics framework statistics.

C6 Execution Intelligence — Phase 6, Module 3
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class MetricsStatistics:
    """Mutable accumulator for framework-wide operational metrics."""

    metrics_calculated:        int   = 0
    calculation_failures:      int   = 0
    aggregation_count:         int   = 0
    aggregation_failures:      int   = 0
    metrics_published:         int   = 0   # snapshots published
    data_points_recorded:      int   = 0
    requests_processed:        int   = 0
    # Running sum for average calculation
    _total_calculation_ms:     float = 0.0
    _total_aggregation_ms:     float = 0.0
    last_updated_at:           float = 0.0

    def __post_init__(self) -> None:
        self._lock = threading.RLock()

    # ── Record helpers ────────────────────────────────────────────────────────

    def record_calculation(self, duration_ms: float = 0.0) -> None:
        with self._lock:
            self.metrics_calculated  += 1
            self._total_calculation_ms += duration_ms
            self.last_updated_at      = time.time()

    def record_calculation_failure(self) -> None:
        with self._lock:
            self.calculation_failures += 1
            self.last_updated_at       = time.time()

    def record_aggregation(self, duration_ms: float = 0.0) -> None:
        with self._lock:
            self.aggregation_count     += 1
            self._total_aggregation_ms += duration_ms
            self.last_updated_at        = time.time()

    def record_aggregation_failure(self) -> None:
        with self._lock:
            self.aggregation_failures += 1
            self.last_updated_at       = time.time()

    def record_published(self) -> None:
        with self._lock:
            self.metrics_published += 1
            self.last_updated_at    = time.time()

    def record_data_point(self) -> None:
        with self._lock:
            self.data_points_recorded += 1
            self.last_updated_at       = time.time()

    def record_request(self) -> None:
        with self._lock:
            self.requests_processed += 1
            self.last_updated_at     = time.time()

    # ── Derived properties ────────────────────────────────────────────────────

    @property
    def average_calculation_time_ms(self) -> float:
        with self._lock:
            if self.metrics_calculated == 0:
                return 0.0
            return self._total_calculation_ms / self.metrics_calculated

    @property
    def average_aggregation_time_ms(self) -> float:
        with self._lock:
            if self.aggregation_count == 0:
                return 0.0
            return self._total_aggregation_ms / self.aggregation_count

    @property
    def calculation_success_rate(self) -> float:
        with self._lock:
            total = self.metrics_calculated + self.calculation_failures
            if total == 0:
                return 0.0
            return self.metrics_calculated / total

    @property
    def aggregation_success_rate(self) -> float:
        with self._lock:
            total = self.aggregation_count + self.aggregation_failures
            if total == 0:
                return 0.0
            return self.aggregation_count / total

    # ── Utilities ─────────────────────────────────────────────────────────────

    def reset(self) -> None:
        with self._lock:
            self.metrics_calculated    = 0
            self.calculation_failures  = 0
            self.aggregation_count     = 0
            self.aggregation_failures  = 0
            self.metrics_published     = 0
            self.data_points_recorded  = 0
            self.requests_processed    = 0
            self._total_calculation_ms = 0.0
            self._total_aggregation_ms = 0.0
            self.last_updated_at       = 0.0

    def copy(self) -> "MetricsStatistics":
        with self._lock:
            s = MetricsStatistics(
                metrics_calculated       = self.metrics_calculated,
                calculation_failures     = self.calculation_failures,
                aggregation_count        = self.aggregation_count,
                aggregation_failures     = self.aggregation_failures,
                metrics_published        = self.metrics_published,
                data_points_recorded     = self.data_points_recorded,
                requests_processed       = self.requests_processed,
                _total_calculation_ms    = self._total_calculation_ms,
                _total_aggregation_ms    = self._total_aggregation_ms,
                last_updated_at          = self.last_updated_at,
            )
        return s

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "metrics_calculated":         self.metrics_calculated,
                "calculation_failures":        self.calculation_failures,
                "aggregation_count":           self.aggregation_count,
                "aggregation_failures":        self.aggregation_failures,
                "metrics_published":           self.metrics_published,
                "data_points_recorded":        self.data_points_recorded,
                "requests_processed":          self.requests_processed,
                "average_calculation_time_ms": self.average_calculation_time_ms,
                "average_aggregation_time_ms": self.average_aggregation_time_ms,
                "calculation_success_rate":    self.calculation_success_rate,
                "aggregation_success_rate":    self.aggregation_success_rate,
                "last_updated_at":             self.last_updated_at,
            }
