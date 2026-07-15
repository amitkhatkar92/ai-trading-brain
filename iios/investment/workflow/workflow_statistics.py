"""iios/investment/workflow/workflow_statistics.py
WorkflowRunMetric — per-run metric data.
WorkflowStatistics — aggregate statistics accumulator.
"""
from __future__ import annotations

import statistics
import threading
from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict, List, Optional

from iios.investment.workflow.workflow_types import PIPELINE_STAGES, WorkflowStage


@dataclass(frozen=True)
class WorkflowRunMetric:
    """Lightweight per-run metric record for statistical aggregation."""

    workflow_id:       str
    portfolio_id:      str
    succeeded:         bool
    total_duration_ms: float
    n_stages_done:     int
    n_retries:         int
    n_errors:          int
    n_warnings:        int
    market_quality:    Optional[float]
    company_quality:   Optional[float]
    strategy_quality:  Optional[float]
    decision_quality:  Optional[float]
    portfolio_quality: Optional[float]
    snapshot_id:       Optional[str]

    def to_dict(self) -> dict:
        return {
            "workflow_id":       self.workflow_id,
            "portfolio_id":      self.portfolio_id,
            "succeeded":         self.succeeded,
            "total_duration_ms": round(self.total_duration_ms, 2),
            "n_stages_done":     self.n_stages_done,
            "n_retries":         self.n_retries,
            "n_errors":          self.n_errors,
            "n_warnings":        self.n_warnings,
        }


@dataclass(frozen=True)
class WorkflowStatisticsSnapshot:
    """Immutable summary of accumulated workflow statistics."""

    total_runs:         int
    total_succeeded:    int
    total_failed:       int
    success_rate:       float   # 0.0-1.0
    avg_duration_ms:    float
    p95_duration_ms:    float
    total_retries:      int
    avg_retries_per_run: float
    avg_market_quality:   Optional[float]
    avg_company_quality:  Optional[float]
    avg_strategy_quality: Optional[float]
    avg_decision_quality: Optional[float]
    avg_portfolio_quality: Optional[float]

    def to_dict(self) -> dict:
        return {
            "total_runs":           self.total_runs,
            "total_succeeded":      self.total_succeeded,
            "total_failed":         self.total_failed,
            "success_rate":         round(self.success_rate, 4),
            "avg_duration_ms":      round(self.avg_duration_ms, 2),
            "p95_duration_ms":      round(self.p95_duration_ms, 2),
            "total_retries":        self.total_retries,
            "avg_retries_per_run":  round(self.avg_retries_per_run, 3),
            "avg_market_quality":   self.avg_market_quality,
            "avg_company_quality":  self.avg_company_quality,
            "avg_strategy_quality": self.avg_strategy_quality,
            "avg_decision_quality": self.avg_decision_quality,
            "avg_portfolio_quality": self.avg_portfolio_quality,
        }


def _safe_mean(values: List[float]) -> Optional[float]:
    clean = [v for v in values if v is not None]
    if not clean:
        return None
    return statistics.mean(clean)


def _p95(values: List[float]) -> float:
    if not values:
        return 0.0
    sorted_v = sorted(values)
    idx = max(0, int(len(sorted_v) * 0.95) - 1)
    return sorted_v[idx]


class WorkflowStatistics:
    """
    Thread-safe rolling statistics accumulator for workflow runs.
    Keeps the last *max_runs* metrics.
    """

    def __init__(self, max_runs: int = 500) -> None:
        if max_runs < 1:
            raise ValueError("max_runs must be >= 1")
        self._max   = max_runs
        self._lock  = threading.RLock()
        self._metrics: Deque[WorkflowRunMetric] = deque(maxlen=max_runs)

    def record(self, metric: WorkflowRunMetric) -> None:
        with self._lock:
            self._metrics.append(metric)

    @property
    def total_runs(self) -> int:
        with self._lock:
            return len(self._metrics)

    def success_rate(self) -> float:
        with self._lock:
            if not self._metrics:
                return 0.0
            return sum(1 for m in self._metrics if m.succeeded) / len(self._metrics)

    def average_duration_ms(self) -> float:
        with self._lock:
            if not self._metrics:
                return 0.0
            return statistics.mean(m.total_duration_ms for m in self._metrics)

    def summary(self) -> WorkflowStatisticsSnapshot:
        with self._lock:
            metrics = list(self._metrics)

        if not metrics:
            return WorkflowStatisticsSnapshot(
                total_runs=0, total_succeeded=0, total_failed=0,
                success_rate=0.0, avg_duration_ms=0.0, p95_duration_ms=0.0,
                total_retries=0, avg_retries_per_run=0.0,
                avg_market_quality=None, avg_company_quality=None,
                avg_strategy_quality=None, avg_decision_quality=None,
                avg_portfolio_quality=None,
            )

        n          = len(metrics)
        succeeded  = sum(1 for m in metrics if m.succeeded)
        durations  = [m.total_duration_ms for m in metrics]
        retries    = sum(m.n_retries for m in metrics)

        return WorkflowStatisticsSnapshot(
            total_runs            = n,
            total_succeeded       = succeeded,
            total_failed          = n - succeeded,
            success_rate          = succeeded / n,
            avg_duration_ms       = statistics.mean(durations),
            p95_duration_ms       = _p95(durations),
            total_retries         = retries,
            avg_retries_per_run   = retries / n,
            avg_market_quality    = _safe_mean([m.market_quality for m in metrics
                                                if m.market_quality is not None]),
            avg_company_quality   = _safe_mean([m.company_quality for m in metrics
                                                if m.company_quality is not None]),
            avg_strategy_quality  = _safe_mean([m.strategy_quality for m in metrics
                                                if m.strategy_quality is not None]),
            avg_decision_quality  = _safe_mean([m.decision_quality for m in metrics
                                                if m.decision_quality is not None]),
            avg_portfolio_quality = _safe_mean([m.portfolio_quality for m in metrics
                                                if m.portfolio_quality is not None]),
        )
