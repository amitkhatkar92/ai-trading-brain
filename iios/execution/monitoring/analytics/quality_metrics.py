"""iios/execution/monitoring/analytics/quality_metrics.py"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class QualityMetrics:
    """Per-broker or per-session execution quality snapshot."""

    broker_id:               str   = ""
    fill_ratio:              float = 0.0     # avg filled_qty / qty
    rejection_rate:          float = 0.0
    cancellation_rate:       float = 0.0
    avg_slippage_bps:        float = 0.0     # price improvement/cost vs arrival price
    avg_latency_ms:          float = 0.0
    p95_latency_ms:          float = 0.0
    order_count:             int   = 0
    execution_quality_index: float = 0.0    # composite 0–1
    computed_at:             float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "broker_id":               self.broker_id,
            "fill_ratio":              round(self.fill_ratio, 4),
            "rejection_rate":          round(self.rejection_rate, 4),
            "cancellation_rate":       round(self.cancellation_rate, 4),
            "avg_slippage_bps":        round(self.avg_slippage_bps, 2),
            "avg_latency_ms":          round(self.avg_latency_ms, 2),
            "p95_latency_ms":          round(self.p95_latency_ms, 2),
            "order_count":             self.order_count,
            "execution_quality_index": round(self.execution_quality_index, 4),
            "computed_at":             self.computed_at,
        }
