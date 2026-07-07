"""
iios/observation/collectors/collector_metrics.py
================================================
Per-collector run metrics: latency, success rate, throughput.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Optional

__all__ = [
    "RunRecord",
    "MetricsSummary",
    "CollectorMetrics",
    "get_collector_metrics",
    "reset_collector_metrics",
]

_lock    = threading.Lock()
_metrics: Optional["CollectorMetrics"] = None


@dataclass
class RunRecord:
    """Records a single collector execution."""
    run_id:     str
    collector:  str
    started_at: float
    ended_at:   float = 0.0
    items:      int   = 0
    errors:     int   = 0
    retries:    int   = 0
    success:    bool  = False

    @property
    def duration_ms(self) -> float:
        if self.ended_at > 0:
            return (self.ended_at - self.started_at) * 1_000.0
        return 0.0


@dataclass
class MetricsSummary:
    """Aggregated metrics for one collector across all runs."""
    collector:       str
    total_runs:      int   = 0
    successful_runs: int   = 0
    failed_runs:     int   = 0
    total_items:     int   = 0
    total_errors:    int   = 0
    total_retries:   int   = 0
    avg_duration_ms: float = 0.0
    max_duration_ms: float = 0.0
    min_duration_ms: float = float("inf")
    last_run_at:     float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "collector":       self.collector,
            "total_runs":      self.total_runs,
            "successful_runs": self.successful_runs,
            "failed_runs":     self.failed_runs,
            "total_items":     self.total_items,
            "total_errors":    self.total_errors,
            "avg_duration_ms": round(self.avg_duration_ms, 2),
            "max_duration_ms": round(self.max_duration_ms, 2),
            "last_run_at":     self.last_run_at,
        }


class CollectorMetrics:
    """Thread-safe per-collector run metrics store."""

    def __init__(self, max_records_per_collector: int = 200) -> None:
        self._lock        = threading.RLock()
        self._max_records = max_records_per_collector
        self._records:    dict[str, list[RunRecord]] = {}

    def record_run(self, record: RunRecord) -> None:
        with self._lock:
            if record.collector not in self._records:
                self._records[record.collector] = []
            recs = self._records[record.collector]
            recs.append(record)
            if len(recs) > self._max_records:
                self._records[record.collector] = recs[-self._max_records:]

    def summary(self, collector: str) -> MetricsSummary:
        with self._lock:
            records = list(self._records.get(collector, []))
        if not records:
            return MetricsSummary(collector=collector)
        durations = [r.duration_ms for r in records if r.ended_at > 0]
        return MetricsSummary(
            collector       = collector,
            total_runs      = len(records),
            successful_runs = sum(1 for r in records if r.success),
            failed_runs     = sum(1 for r in records if not r.success),
            total_items     = sum(r.items   for r in records),
            total_errors    = sum(r.errors  for r in records),
            total_retries   = sum(r.retries for r in records),
            avg_duration_ms = sum(durations) / len(durations) if durations else 0.0,
            max_duration_ms = max(durations) if durations else 0.0,
            min_duration_ms = min(durations) if durations else 0.0,
            last_run_at     = records[-1].started_at,
        )

    def all_summaries(self) -> dict[str, MetricsSummary]:
        with self._lock:
            names = list(self._records)
        return {n: self.summary(n) for n in names}

    def clear(self, collector: Optional[str] = None) -> None:
        with self._lock:
            if collector:
                self._records.pop(collector, None)
            else:
                self._records.clear()

    def collector_names(self) -> list[str]:
        with self._lock:
            return list(self._records)


def get_collector_metrics() -> CollectorMetrics:
    global _metrics
    if _metrics is None:
        with _lock:
            if _metrics is None:
                _metrics = CollectorMetrics()
    return _metrics


def reset_collector_metrics() -> None:
    global _metrics
    with _lock:
        _metrics = None
