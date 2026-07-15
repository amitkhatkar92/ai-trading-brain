"""iios/investment/portfolio/performance/benchmark_statistics.py

Statistics and history for benchmark comparisons.
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List

from iios.investment.portfolio.performance.benchmark_comparison import BenchmarkComparison


@dataclass(frozen=True)
class BenchmarkStatisticsSnapshot:
    """Aggregate statistics over multiple benchmark comparison runs."""

    total_comparisons:    int   = 0
    outperformance_count: int   = 0
    outperformance_rate:  float = 0.0
    avg_alpha:            float = 0.0
    avg_information_ratio:float = 0.0
    avg_tracking_error:   float = 0.0
    avg_beta:             float = 0.0
    best_alpha:           float = 0.0
    worst_alpha:          float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_comparisons":    self.total_comparisons,
            "outperformance_rate":  round(self.outperformance_rate, 4),
            "avg_alpha":            round(self.avg_alpha, 4),
            "avg_information_ratio":round(self.avg_information_ratio, 4),
            "avg_tracking_error":   round(self.avg_tracking_error, 4),
            "avg_beta":             round(self.avg_beta, 4),
        }


class BenchmarkStatistics:
    """Thread-safe accumulator for benchmark comparison statistics."""

    def __init__(self, max_comparisons: int = 500) -> None:
        self._max  = max_comparisons
        self._lock = threading.RLock()
        self._data: List[BenchmarkComparison] = []

    def record(self, comparison: BenchmarkComparison) -> None:
        with self._lock:
            self._data.append(comparison)
            if len(self._data) > self._max:
                self._data = self._data[-self._max:]

    def snapshot(self) -> BenchmarkStatisticsSnapshot:
        with self._lock:
            if not self._data:
                return BenchmarkStatisticsSnapshot()
            n       = len(self._data)
            outperf = sum(1 for c in self._data if c.outperforms)
            alphas  = [c.alpha for c in self._data]
            irs     = [c.information_ratio for c in self._data]
            tes     = [c.tracking_error for c in self._data]
            betas   = [c.beta for c in self._data]
            return BenchmarkStatisticsSnapshot(
                total_comparisons    = n,
                outperformance_count = outperf,
                outperformance_rate  = round(outperf / n, 4),
                avg_alpha            = round(sum(alphas) / n, 4),
                avg_information_ratio= round(sum(irs) / n, 4),
                avg_tracking_error   = round(sum(tes) / n, 4),
                avg_beta             = round(sum(betas) / n, 4),
                best_alpha           = round(max(alphas), 4),
                worst_alpha          = round(min(alphas), 4),
            )
