"""
market_analytics_statistics.py — iios.market.analytics
========================================================
Thread-safe statistics for the Market Analytics Framework.

C12 Market Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import threading
import time
from typing import Any, Dict


class MarketAnalyticsStatistics:
    """Thread-safe running statistics for the Market Analytics Framework."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._reset()

    def record_analytics_started(self) -> None:
        with self._lock:
            self._analytics_total += 1

    def record_analytics_completed(self) -> None:
        with self._lock:
            self._analytics_completed += 1

    def record_analytics_failed(self) -> None:
        with self._lock:
            self._analytics_failed += 1

    def record_regime_classified(self) -> None:
        with self._lock:
            self._regimes_classified += 1

    def record_sector_analysis(self) -> None:
        with self._lock:
            self._sector_analyses += 1

    def record_breadth_analysis(self) -> None:
        with self._lock:
            self._breadth_analyses += 1

    def record_forecast_generated(self) -> None:
        with self._lock:
            self._forecasts_generated += 1

    def record_elapsed(self, elapsed_s: float) -> None:
        with self._lock:
            self._total_elapsed_s += elapsed_s
            self._timed_runs += 1

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            avg = (
                self._total_elapsed_s / self._timed_runs
                if self._timed_runs > 0 else 0.0
            )
            elapsed_since_reset = time.time() - self._reset_time
            throughput = (
                self._analytics_total / elapsed_since_reset
                if elapsed_since_reset > 0 else 0.0
            )
            return {
                "analytics_total":       self._analytics_total,
                "analytics_completed":   self._analytics_completed,
                "analytics_failed":      self._analytics_failed,
                "regimes_classified":    self._regimes_classified,
                "sector_analyses":       self._sector_analyses,
                "breadth_analyses":      self._breadth_analyses,
                "forecasts_generated":   self._forecasts_generated,
                "average_runtime_s":     round(avg, 4),
                "analytics_throughput":  round(throughput, 4),
            }

    def reset(self) -> None:
        with self._lock:
            self._reset()

    def _reset(self) -> None:
        self._analytics_total:     int   = 0
        self._analytics_completed: int   = 0
        self._analytics_failed:    int   = 0
        self._regimes_classified:  int   = 0
        self._sector_analyses:     int   = 0
        self._breadth_analyses:    int   = 0
        self._forecasts_generated: int   = 0
        self._total_elapsed_s:     float = 0.0
        self._timed_runs:          int   = 0
        self._reset_time:          float = time.time()
