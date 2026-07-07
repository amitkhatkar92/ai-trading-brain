"""
iios/observation/pipeline/pipeline_monitor.py
=============================================
Real-time pipeline health monitor.

Tracks per-stage and per-pipeline latency, throughput, failure rates,
and detects bottleneck stages based on p95 latency.
"""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from .pipeline_executor  import PipelineExecutionResult
from .pipeline_metrics   import PipelineMetrics, get_pipeline_metrics

__all__ = [
    "StageHealthReport",
    "PipelineHealthReport",
    "PipelineMonitor",
    "get_pipeline_monitor",
    "reset_pipeline_monitor",
]

_LOG     = logging.getLogger("iios.observation.pipeline.monitor")
_lock    = threading.Lock()
_monitor: Optional["PipelineMonitor"] = None

# Stage latency threshold for "bottleneck" classification (ms)
_BOTTLENECK_THRESHOLD_MS: float = 500.0


@dataclass
class StageHealthReport:
    """Health summary for a single stage."""
    stage_name:   str
    executed:     int
    skipped:      int
    failed:       int
    failure_rate: float
    avg_ms:       float
    p95_ms:       float
    is_bottleneck: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage_name":    self.stage_name,
            "executed":      self.executed,
            "skipped":       self.skipped,
            "failed":        self.failed,
            "failure_rate":  round(self.failure_rate, 4),
            "avg_ms":        round(self.avg_ms, 3),
            "p95_ms":        round(self.p95_ms, 3),
            "is_bottleneck": self.is_bottleneck,
        }


@dataclass
class PipelineHealthReport:
    """Full health report for the pipeline engine."""
    report_at:       float
    total_processed: int
    success_rate:    float
    avg_latency_ms:  float
    p95_latency_ms:  float
    p99_latency_ms:  float
    queue_depth:     int
    active_pipelines: int
    bottleneck_stages: list[str]
    stage_reports:   list[StageHealthReport]
    per_pipeline:    dict[str, dict[str, Any]]
    healthy:         bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_at":        self.report_at,
            "total_processed":  self.total_processed,
            "success_rate":     round(self.success_rate, 4),
            "avg_latency_ms":   round(self.avg_latency_ms, 3),
            "p95_latency_ms":   round(self.p95_latency_ms, 3),
            "p99_latency_ms":   round(self.p99_latency_ms, 3),
            "queue_depth":      self.queue_depth,
            "active_pipelines": self.active_pipelines,
            "bottleneck_stages": self.bottleneck_stages,
            "healthy":          self.healthy,
            "stages":           [s.to_dict() for s in self.stage_reports],
            "per_pipeline":     self.per_pipeline,
        }


class PipelineMonitor:
    """
    Observes pipeline execution results and builds health reports.

    Typical usage::

        monitor = get_pipeline_monitor()
        result  = executor.execute(obs, pipeline)
        monitor.record(result)
        report  = monitor.health_report()
    """

    def __init__(self, metrics: Optional[PipelineMetrics] = None) -> None:
        self._metrics  = metrics or get_pipeline_metrics()
        self._recent:  list[PipelineExecutionResult] = []
        self._max_recent = 200
        self._lock     = threading.RLock()

    def record(self, result: PipelineExecutionResult) -> None:
        """Record a completed pipeline execution result."""
        self._metrics.record_pipeline(
            pipeline_name = result.pipeline_name,
            success       = result.success,
            dead_letter   = result.dead_lettered,
            total_ms      = result.total_ms,
            stage_results = result.stage_results,
        )
        with self._lock:
            self._recent.append(result)
            if len(self._recent) > self._max_recent:
                self._recent = self._recent[-self._max_recent:]

        if not result.success:
            _LOG.warning(
                "Pipeline %r FAILED for obs %s in %.1fms: %s",
                result.pipeline_name, result.obs_id[:8],
                result.total_ms, result.rejection_reason,
            )

    def health_report(self) -> PipelineHealthReport:
        """Build and return a current health report."""
        snap = self._metrics.snapshot()

        # Build per-stage reports
        stage_reports: list[StageHealthReport] = []
        bottleneck_stages: list[str]           = []

        for name, data in snap.per_stage.items():
            executed = data.get("executed", 0)
            failed   = data.get("failed", 0)
            p95      = data.get("p95_ms", 0.0)
            is_bn    = p95 > _BOTTLENECK_THRESHOLD_MS
            if is_bn:
                bottleneck_stages.append(name)
            stage_reports.append(StageHealthReport(
                stage_name    = name,
                executed      = executed,
                skipped       = data.get("skipped", 0),
                failed        = failed,
                failure_rate  = failed / executed if executed else 0.0,
                avg_ms        = data.get("avg_ms", 0.0),
                p95_ms        = p95,
                is_bottleneck = is_bn,
            ))

        # Consider healthy if:
        # - success_rate >= 0.90
        # - p99 latency < 10,000 ms
        # - no catastrophic failures
        healthy = (
            snap.success_rate >= 0.90
            and snap.p99_latency_ms < 10_000.0
        )

        return PipelineHealthReport(
            report_at        = snap.captured_at,
            total_processed  = snap.total_processed,
            success_rate     = snap.success_rate,
            avg_latency_ms   = snap.avg_latency_ms,
            p95_latency_ms   = snap.p95_latency_ms,
            p99_latency_ms   = snap.p99_latency_ms,
            queue_depth      = snap.queue_depth,
            active_pipelines = snap.active_pipelines,
            bottleneck_stages = bottleneck_stages,
            stage_reports    = sorted(stage_reports, key=lambda r: r.stage_name),
            per_pipeline     = snap.per_pipeline,
            healthy          = healthy,
        )

    def recent(self, limit: int = 50) -> list[PipelineExecutionResult]:
        with self._lock:
            return list(self._recent[-limit:])

    def stats(self) -> dict[str, Any]:
        snap = self._metrics.snapshot()
        return snap.to_dict()


def get_pipeline_monitor() -> PipelineMonitor:
    global _monitor
    if _monitor is None:
        with _lock:
            if _monitor is None:
                _monitor = PipelineMonitor()
    return _monitor


def reset_pipeline_monitor() -> None:
    global _monitor
    with _lock:
        _monitor = None
