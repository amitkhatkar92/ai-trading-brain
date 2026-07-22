"""
portfolio_optimization_statistics.py — iios.portfolio.optimization
===================================================================
Thread-safe counters for the optimization engine.

C10 Portfolio Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any, Dict

from .constants import VERSION


@dataclass(frozen=True)
class OptimizationStatisticsSnapshot:
    """Immutable point-in-time snapshot of optimization engine statistics."""
    total_requests:         int
    total_optimizations:    int
    successful:             int
    failed:                 int
    total_candidates:       int
    total_solutions:        int
    total_selected:         int
    uptime_s:               float
    captured_at:            float
    framework_version:      str = VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_requests":       self.total_requests,
            "total_optimizations":  self.total_optimizations,
            "successful":           self.successful,
            "failed":               self.failed,
            "total_candidates":     self.total_candidates,
            "total_solutions":      self.total_solutions,
            "total_selected":       self.total_selected,
            "success_rate":         (
                round(self.successful / self.total_optimizations, 4)
                if self.total_optimizations > 0
                else 0.0
            ),
            "uptime_s":             self.uptime_s,
            "captured_at":          self.captured_at,
            "framework_version":    self.framework_version,
        }


class PortfolioOptimizationStatistics:
    """
    Thread-safe atomic counters for optimization engine metrics.
    """

    def __init__(self) -> None:
        self._lock                  = threading.Lock()
        self._total_requests:       int = 0
        self._total_optimizations:  int = 0
        self._successful:           int = 0
        self._failed:               int = 0
        self._total_candidates:     int = 0
        self._total_solutions:      int = 0
        self._total_selected:       int = 0
        self._started_at:           float = time.monotonic()

    # ------------------------------------------------------------------
    # Incrementers
    # ------------------------------------------------------------------

    def record_request(self) -> None:
        with self._lock:
            self._total_requests += 1

    def record_optimization_started(self, candidate_count: int = 0) -> None:
        with self._lock:
            self._total_optimizations += 1
            self._total_candidates    += candidate_count

    def record_success(self, solution_count: int = 0, selected: bool = False) -> None:
        with self._lock:
            self._successful       += 1
            self._total_solutions  += solution_count
            if selected:
                self._total_selected += 1

    def record_failure(self) -> None:
        with self._lock:
            self._failed += 1

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------

    def snapshot(self) -> OptimizationStatisticsSnapshot:
        with self._lock:
            return OptimizationStatisticsSnapshot(
                total_requests       = self._total_requests,
                total_optimizations  = self._total_optimizations,
                successful           = self._successful,
                failed               = self._failed,
                total_candidates     = self._total_candidates,
                total_solutions      = self._total_solutions,
                total_selected       = self._total_selected,
                uptime_s             = time.monotonic() - self._started_at,
                captured_at          = time.time(),
            )

    def reset(self) -> None:
        with self._lock:
            self._total_requests       = 0
            self._total_optimizations  = 0
            self._successful           = 0
            self._failed               = 0
            self._total_candidates     = 0
            self._total_solutions      = 0
            self._total_selected       = 0
            self._started_at           = time.monotonic()
