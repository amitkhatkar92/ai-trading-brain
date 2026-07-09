"""iios/investment/monitoring/investment_metrics.py"""
from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class InvestmentMetrics:
    """Point-in-time snapshot of engine performance metrics."""

    total_requests:    int   = 0
    completed:         int   = 0
    failed:            int   = 0
    total_analyses:    int   = 0
    avg_duration_ms:   float = 0.0
    active_sessions:   int   = 0
    registered_workflows: int = 0
    snapshot_at:       float = field(default_factory=time.time)

    @property
    def success_rate(self) -> float:
        return self.completed / self.total_requests if self.total_requests else 0.0

    def to_dict(self) -> dict:
        return {
            "total_requests":       self.total_requests,
            "completed":            self.completed,
            "failed":               self.failed,
            "total_analyses":       self.total_analyses,
            "avg_duration_ms":      self.avg_duration_ms,
            "success_rate":         self.success_rate,
            "active_sessions":      self.active_sessions,
            "registered_workflows": self.registered_workflows,
            "snapshot_at":          self.snapshot_at,
        }
