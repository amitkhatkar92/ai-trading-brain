"""
reliability_metrics.py -- iios.ai.learning_evaluation.metrics
===============================================================
:class:`ReliabilityMetrics` — uptime, error rate, retry count.

A7 Learning & Evaluation Platform — Phase 3, Module 7
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class ReliabilityMetrics:
    """Immutable reliability metrics for a period of operation."""

    metrics_id:       str
    total_requests:   int
    successful:       int
    failed:           int
    retried:          int
    error_rate:       float   # failed / total
    success_rate:     float   # successful / total
    retry_rate:       float   # retried / total
    uptime_pct:       float   # 0.0–100.0 (None if not measured)
    computed_at:      float

    @classmethod
    def compute(
        cls,
        total_requests: int,
        successful:     int,
        failed:         int,
        retried:        int    = 0,
        uptime_pct:     float  = 100.0,
    ) -> "ReliabilityMetrics":
        n = total_requests or 1
        return cls(
            metrics_id     = str(uuid.uuid4()),
            total_requests = total_requests,
            successful     = successful,
            failed         = failed,
            retried        = retried,
            error_rate     = round(failed / n, 6),
            success_rate   = round(successful / n, 6),
            retry_rate     = round(retried / n, 6),
            uptime_pct     = max(0.0, min(100.0, uptime_pct)),
            computed_at    = time.time(),
        )

    def meets_slo(self, max_error_rate: float = 0.01, min_uptime_pct: float = 99.0) -> bool:
        """True if both error rate and uptime SLOs are met."""
        return self.error_rate <= max_error_rate and self.uptime_pct >= min_uptime_pct
