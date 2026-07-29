"""
latency_metrics.py -- iios.ai.learning_evaluation.metrics
===========================================================
:class:`LatencyMetrics` — p50, p95, p99, mean, max latency.

A7 Learning & Evaluation Platform — Phase 3, Module 7
"""
from __future__ import annotations

import statistics
import time
import uuid
from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class LatencyMetrics:
    """Immutable latency distribution metrics (all values in milliseconds)."""

    metrics_id:  str
    p50_ms:      float
    p95_ms:      float
    p99_ms:      float
    mean_ms:     float
    max_ms:      float
    min_ms:      float
    sample_size: int
    computed_at: float

    @classmethod
    def compute(cls, latencies_ms: List[float]) -> "LatencyMetrics":
        """Compute latency distribution from a list of millisecond measurements."""
        if not latencies_ms:
            return cls(
                metrics_id  = str(uuid.uuid4()),
                p50_ms      = 0.0,
                p95_ms      = 0.0,
                p99_ms      = 0.0,
                mean_ms     = 0.0,
                max_ms      = 0.0,
                min_ms      = 0.0,
                sample_size = 0,
                computed_at = time.time(),
            )
        sorted_l = sorted(latencies_ms)
        n        = len(sorted_l)

        def _percentile(p: float) -> float:
            idx = int(p / 100.0 * n)
            return sorted_l[min(idx, n - 1)]

        return cls(
            metrics_id  = str(uuid.uuid4()),
            p50_ms      = round(_percentile(50), 3),
            p95_ms      = round(_percentile(95), 3),
            p99_ms      = round(_percentile(99), 3),
            mean_ms     = round(statistics.mean(latencies_ms), 3),
            max_ms      = round(max(latencies_ms), 3),
            min_ms      = round(min(latencies_ms), 3),
            sample_size = n,
            computed_at = time.time(),
        )

    def meets_slo(self, p95_limit_ms: float) -> bool:
        """Return True if p95 latency is within the SLO limit."""
        return self.p95_ms <= p95_limit_ms
