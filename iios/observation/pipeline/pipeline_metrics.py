"""
iios/observation/pipeline/pipeline_metrics.py
=============================================
Aggregate counters, gauges, and histograms for the pipeline.

``PipelineMetrics`` is the top-level container.  It is updated by
``PipelineMonitor`` after every pipeline run.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any

__all__ = [
    "MetricsSnapshot",
    "PipelineMetrics",
    "get_pipeline_metrics",
    "reset_pipeline_metrics",
]

_lock    = threading.Lock()
_metrics: "PipelineMetrics | None" = None


@dataclass
class MetricsSnapshot:
    """Point-in-time metrics snapshot."""
    captured_at:       float
    total_processed:   int
    total_success:     int
    total_failed:      int
    total_dead_letter: int
    total_retries:     int
    success_rate:      float
    avg_latency_ms:    float
    p95_latency_ms:    float
    p99_latency_ms:    float
    queue_depth:       int
    active_pipelines:  int
    per_pipeline:      dict[str, dict[str, Any]]
    per_stage:         dict[str, dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "captured_at":       self.captured_at,
            "total_processed":   self.total_processed,
            "total_success":     self.total_success,
            "total_failed":      self.total_failed,
            "total_dead_letter": self.total_dead_letter,
            "total_retries":     self.total_retries,
            "success_rate":      round(self.success_rate, 4),
            "avg_latency_ms":    round(self.avg_latency_ms, 3),
            "p95_latency_ms":    round(self.p95_latency_ms, 3),
            "p99_latency_ms":    round(self.p99_latency_ms, 3),
            "queue_depth":       self.queue_depth,
            "active_pipelines":  self.active_pipelines,
        }


class _LatencyWindow:
    """Rolling window for latency percentile computation."""

    def __init__(self, max_size: int = 1_000) -> None:
        self._samples:  list[float] = []
        self._max_size: int         = max_size
        self._lock      = threading.Lock()

    def record(self, value_ms: float) -> None:
        with self._lock:
            self._samples.append(value_ms)
            if len(self._samples) > self._max_size:
                self._samples = self._samples[-self._max_size:]

    def percentile(self, p: float) -> float:
        with self._lock:
            if not self._samples:
                return 0.0
            sorted_s = sorted(self._samples)
            idx = max(0, int(len(sorted_s) * p / 100.0) - 1)
            return sorted_s[idx]

    def mean(self) -> float:
        with self._lock:
            if not self._samples:
                return 0.0
            return sum(self._samples) / len(self._samples)

    def count(self) -> int:
        with self._lock:
            return len(self._samples)


class _PipelineCounter:
    """Per-pipeline counters and latency window."""

    def __init__(self) -> None:
        self.processed   = 0
        self.success     = 0
        self.failed      = 0
        self.dead_letter = 0
        self.retries     = 0
        self._latency    = _LatencyWindow()

    def record(self, success: bool, dead_letter: bool, retries: int, ms: float) -> None:
        self.processed += 1
        if success:
            self.success += 1
        else:
            self.failed += 1
        if dead_letter:
            self.dead_letter += 1
        self.retries += retries
        self._latency.record(ms)

    def to_dict(self) -> dict[str, Any]:
        return {
            "processed":    self.processed,
            "success":      self.success,
            "failed":       self.failed,
            "dead_letter":  self.dead_letter,
            "retries":      self.retries,
            "avg_ms":       round(self._latency.mean(), 3),
            "p95_ms":       round(self._latency.percentile(95), 3),
            "p99_ms":       round(self._latency.percentile(99), 3),
        }


class _StageCounter:
    """Per-stage latency window and counters."""

    def __init__(self) -> None:
        self.executed = 0
        self.skipped  = 0
        self.failed   = 0
        self._latency = _LatencyWindow(max_size=2_000)

    def record(self, skipped: bool, success: bool, ms: float) -> None:
        if skipped:
            self.skipped += 1
        else:
            self.executed += 1
        if not success and not skipped:
            self.failed += 1
        if not skipped:
            self._latency.record(ms)

    def to_dict(self) -> dict[str, Any]:
        return {
            "executed": self.executed,
            "skipped":  self.skipped,
            "failed":   self.failed,
            "avg_ms":   round(self._latency.mean(), 3),
            "p95_ms":   round(self._latency.percentile(95), 3),
        }


class PipelineMetrics:
    """Aggregates all pipeline and stage metrics."""

    def __init__(self) -> None:
        self._global_latency     = _LatencyWindow(max_size=5_000)
        self._pipeline_counters: dict[str, _PipelineCounter] = {}
        self._stage_counters:    dict[str, _StageCounter]    = {}
        self._queue_depth        = 0
        self._active_pipelines   = 0
        self._lock               = threading.RLock()

    def record_pipeline(
        self,
        pipeline_name: str,
        success:       bool,
        dead_letter:   bool,
        total_ms:      float,
        stage_results: list,
    ) -> None:
        """Update all counters after one pipeline run."""
        total_retries = sum(getattr(r, "retries", 0) for r in stage_results)
        with self._lock:
            self._global_latency.record(total_ms)
            pc = self._pipeline_counters.setdefault(pipeline_name, _PipelineCounter())
            pc.record(success, dead_letter, total_retries, total_ms)
            for sr in stage_results:
                sc = self._stage_counters.setdefault(sr.stage_name, _StageCounter())
                sc.record(sr.skipped, sr.success, sr.duration_ms)

    def inc_queue_depth(self, delta: int = 1) -> None:
        with self._lock:
            self._queue_depth = max(0, self._queue_depth + delta)

    def set_active_pipelines(self, count: int) -> None:
        with self._lock:
            self._active_pipelines = count

    def snapshot(self) -> MetricsSnapshot:
        with self._lock:
            total_p = sum(c.processed for c in self._pipeline_counters.values())
            total_s = sum(c.success   for c in self._pipeline_counters.values())
            total_f = sum(c.failed    for c in self._pipeline_counters.values())
            total_d = sum(c.dead_letter for c in self._pipeline_counters.values())
            total_r = sum(c.retries   for c in self._pipeline_counters.values())
            return MetricsSnapshot(
                captured_at       = time.time(),
                total_processed   = total_p,
                total_success     = total_s,
                total_failed      = total_f,
                total_dead_letter = total_d,
                total_retries     = total_r,
                success_rate      = total_s / total_p if total_p else 0.0,
                avg_latency_ms    = self._global_latency.mean(),
                p95_latency_ms    = self._global_latency.percentile(95),
                p99_latency_ms    = self._global_latency.percentile(99),
                queue_depth       = self._queue_depth,
                active_pipelines  = self._active_pipelines,
                per_pipeline      = {k: v.to_dict() for k, v in self._pipeline_counters.items()},
                per_stage         = {k: v.to_dict() for k, v in self._stage_counters.items()},
            )


def get_pipeline_metrics() -> PipelineMetrics:
    global _metrics
    if _metrics is None:
        with _lock:
            if _metrics is None:
                _metrics = PipelineMetrics()
    return _metrics


def reset_pipeline_metrics() -> None:
    global _metrics
    with _lock:
        _metrics = None
