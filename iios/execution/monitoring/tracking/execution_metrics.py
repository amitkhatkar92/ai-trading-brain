"""iios/execution/monitoring/tracking/execution_metrics.py"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExecutionMetrics:
    """Aggregated metrics computed over a set of execution records."""

    # Counts
    total_executions:   int   = 0
    active:             int   = 0
    completed:          int   = 0
    partially_filled:   int   = 0
    fully_filled:       int   = 0
    cancelled:          int   = 0
    rejected:           int   = 0
    failed:             int   = 0

    # Volume
    total_orders:       int   = 0
    total_fills:        int   = 0
    total_volume:       float = 0.0
    total_notional:     float = 0.0

    # Quality
    avg_fill_ratio:     float = 0.0
    success_rate:       float = 0.0
    rejection_rate:     float = 0.0
    cancellation_rate:  float = 0.0

    # Latency
    avg_latency_ms:     float = 0.0
    p50_latency_ms:     float = 0.0
    p75_latency_ms:     float = 0.0
    p95_latency_ms:     float = 0.0
    p99_latency_ms:     float = 0.0
    max_latency_ms:     float = 0.0

    # Composite
    execution_quality_index: float = 0.0   # 0.0 – 1.0

    # Period
    period_start:       float | None = None
    period_end:         float | None = None
    computed_at:        float        = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_executions":        self.total_executions,
            "active":                  self.active,
            "completed":               self.completed,
            "partially_filled":        self.partially_filled,
            "fully_filled":            self.fully_filled,
            "cancelled":               self.cancelled,
            "rejected":                self.rejected,
            "failed":                  self.failed,
            "total_orders":            self.total_orders,
            "total_fills":             self.total_fills,
            "total_volume":            round(self.total_volume, 4),
            "total_notional":          round(self.total_notional, 2),
            "avg_fill_ratio":          round(self.avg_fill_ratio, 4),
            "success_rate":            round(self.success_rate, 4),
            "rejection_rate":          round(self.rejection_rate, 4),
            "cancellation_rate":       round(self.cancellation_rate, 4),
            "avg_latency_ms":          round(self.avg_latency_ms, 2),
            "p50_latency_ms":          round(self.p50_latency_ms, 2),
            "p95_latency_ms":          round(self.p95_latency_ms, 2),
            "p99_latency_ms":          round(self.p99_latency_ms, 2),
            "max_latency_ms":          round(self.max_latency_ms, 2),
            "execution_quality_index": round(self.execution_quality_index, 4),
            "period_start":            self.period_start,
            "period_end":              self.period_end,
            "computed_at":             self.computed_at,
        }
