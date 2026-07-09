"""iios/investment/models/investment_statistics.py"""
from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class InvestmentStatistics:
    """Cumulative runtime statistics for the Investment Intelligence Engine."""

    total_requests:       int         = 0
    completed:            int         = 0
    failed:               int         = 0
    cancelled:            int         = 0
    total_analyses:       int         = 0
    total_duration_ms:    float       = 0.0
    by_asset_class:       dict        = field(default_factory=dict)   # AssetClass.value → int
    by_intelligence_type: dict        = field(default_factory=dict)   # IntelligenceType.value → int
    snapshot_at:          float       = field(default_factory=time.time)

    @property
    def avg_duration_ms(self) -> float:
        return self.total_duration_ms / self.total_requests if self.total_requests else 0.0

    @property
    def success_rate(self) -> float:
        return self.completed / self.total_requests if self.total_requests else 0.0

    def to_dict(self) -> dict:
        return {
            "total_requests":       self.total_requests,
            "completed":            self.completed,
            "failed":               self.failed,
            "cancelled":            self.cancelled,
            "total_analyses":       self.total_analyses,
            "avg_duration_ms":      self.avg_duration_ms,
            "success_rate":         self.success_rate,
            "by_asset_class":       self.by_asset_class,
            "by_intelligence_type": self.by_intelligence_type,
            "snapshot_at":          self.snapshot_at,
        }
