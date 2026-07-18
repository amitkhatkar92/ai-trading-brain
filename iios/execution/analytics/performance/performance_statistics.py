"""
iios/execution/analytics/performance/performance_statistics.py
==============================================================
PerformanceAnalyticsStatistics — thread-safe counters and timing
statistics for the Performance Analytics Framework.

C8 Execution Analytics & Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class PerformanceAnalyticsStatistics:
    """
    Thread-safe operational statistics for PerformanceAnalyticsEngine.

    Counters are updated atomically under a single RLock.
    """

    # Counters
    analytics_cycles:        int   = 0
    kpis_generated:          int   = 0
    reports_generated:       int   = 0
    trend_analyses:          int   = 0
    benchmark_comparisons:   int   = 0
    scorecard_generations:   int   = 0
    failed_cycles:           int   = 0
    total_kpi_reports:       int   = 0

    # Timing
    total_calculation_ms:    float = 0.0
    total_processing_ms:     float = 0.0

    # Derived (read-only; computed on access)
    _lock:                   threading.RLock = field(
        default_factory=threading.RLock, repr=False, compare=False
    )

    # ── Thread-safe update methods ────────────────────────────────────────────

    def record_cycle(
        self,
        kpi_count:       int,
        processing_ms:   float,
        calculation_ms:  float = 0.0,
        had_trends:      bool  = False,
        had_benchmarks:  bool  = False,
        had_scorecard:   bool  = False,
    ) -> None:
        with self._lock:
            self.analytics_cycles      += 1
            self.kpis_generated        += kpi_count
            self.reports_generated     += 1
            self.total_kpi_reports     += 1
            self.total_processing_ms   += processing_ms
            self.total_calculation_ms  += calculation_ms
            if had_trends:
                self.trend_analyses    += 1
            if had_benchmarks:
                self.benchmark_comparisons += 1
            if had_scorecard:
                self.scorecard_generations += 1

    def record_failure(self) -> None:
        with self._lock:
            self.failed_cycles += 1

    # ── Derived properties ────────────────────────────────────────────────────

    @property
    def avg_processing_time_ms(self) -> float:
        with self._lock:
            n = self.analytics_cycles
            return self.total_processing_ms / n if n > 0 else 0.0

    @property
    def avg_calculation_time_ms(self) -> float:
        with self._lock:
            n = self.analytics_cycles
            return self.total_calculation_ms / n if n > 0 else 0.0

    @property
    def avg_kpis_per_cycle(self) -> float:
        with self._lock:
            n = self.analytics_cycles
            return self.kpis_generated / n if n > 0 else 0.0

    @property
    def success_rate(self) -> float:
        with self._lock:
            total = self.analytics_cycles + self.failed_cycles
            return self.analytics_cycles / total if total > 0 else 1.0

    def snapshot(self) -> Dict[str, float]:
        """Return a point-in-time snapshot as a plain dict."""
        with self._lock:
            return {
                "analytics_cycles":       float(self.analytics_cycles),
                "kpis_generated":         float(self.kpis_generated),
                "reports_generated":      float(self.reports_generated),
                "trend_analyses":         float(self.trend_analyses),
                "benchmark_comparisons":  float(self.benchmark_comparisons),
                "scorecard_generations":  float(self.scorecard_generations),
                "failed_cycles":          float(self.failed_cycles),
                "avg_processing_time_ms": self.avg_processing_time_ms,
                "avg_calculation_time_ms":self.avg_calculation_time_ms,
                "success_rate":           self.success_rate,
            }
