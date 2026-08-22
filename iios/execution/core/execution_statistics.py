"""iios/execution/core/execution_statistics.py"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExecutionStatistics:
    """Aggregate operational statistics for the Execution Engine."""

    total_executions:     int   = 0
    successful:           int   = 0
    failed:               int   = 0
    cancelled:            int   = 0
    active_sessions:      int   = 0
    queued:               int   = 0

    avg_execution_ms:     float = 0.0
    min_execution_ms:     float = 0.0
    max_execution_ms:     float = 0.0
    total_execution_ms:   float = 0.0

    avg_fill_ratio:       float = 0.0
    total_volume:         float = 0.0   # sum of quantity_executed across all trades

    uptime_sec:           float = 0.0
    engine_started_at:    float = field(default_factory=time.time)
    last_updated_at:      float = field(default_factory=time.time)

    # ── Derived ────────────────────────────────────────────────────────────────

    @property
    def success_rate(self) -> float:
        if self.total_executions == 0:
            return 0.0
        return self.successful / self.total_executions

    @property
    def failure_rate(self) -> float:
        if self.total_executions == 0:
            return 0.0
        return self.failed / self.total_executions

    def refresh_uptime(self) -> None:
        self.uptime_sec   = time.time() - self.engine_started_at
        self.last_updated_at = time.time()

    def record_completion(
        self,
        *,
        success: bool,
        duration_ms: float,
        fill_ratio: float = 1.0,
        volume: float = 0.0,
    ) -> None:
        self.total_executions += 1
        if success:
            self.successful += 1
        else:
            self.failed += 1

        # Running averages / min / max
        n = self.total_executions
        self.total_execution_ms += duration_ms
        self.avg_execution_ms    = self.total_execution_ms / n
        if n == 1 or duration_ms < self.min_execution_ms:
            self.min_execution_ms = duration_ms
        if duration_ms > self.max_execution_ms:
            self.max_execution_ms = duration_ms

        prev_fill = self.avg_fill_ratio * (n - 1)
        self.avg_fill_ratio = (prev_fill + fill_ratio) / n
        self.total_volume  += volume
        self.last_updated_at = time.time()

    def record_cancellation(self) -> None:
        self.total_executions += 1
        self.cancelled        += 1
        self.last_updated_at  = time.time()

    def to_dict(self) -> dict[str, Any]:
        self.refresh_uptime()
        return {
            "total_executions":   self.total_executions,
            "successful":         self.successful,
            "failed":             self.failed,
            "cancelled":          self.cancelled,
            "active_sessions":    self.active_sessions,
            "queued":             self.queued,
            "success_rate":       round(self.success_rate, 4),
            "failure_rate":       round(self.failure_rate, 4),
            "avg_execution_ms":   round(self.avg_execution_ms, 2),
            "min_execution_ms":   round(self.min_execution_ms, 2),
            "max_execution_ms":   round(self.max_execution_ms, 2),
            "avg_fill_ratio":     round(self.avg_fill_ratio, 4),
            "total_volume":       round(self.total_volume, 4),
            "uptime_sec":         round(self.uptime_sec, 2),
            "engine_started_at":  self.engine_started_at,
            "last_updated_at":    self.last_updated_at,
        }
