"""iios/investment/portfolio/core/portfolio_statistics.py"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PortfolioStatistics:
    """Aggregate operational statistics for the portfolio engine."""

    portfolios_tracked:   int   = 0
    analyses_total:       int   = 0
    analyses_successful:  int   = 0
    analyses_failed:      int   = 0
    avg_duration_ms:      float = 0.0
    uptime_sec:           float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "portfolios_tracked":   self.portfolios_tracked,
            "analyses_total":       self.analyses_total,
            "analyses_successful":  self.analyses_successful,
            "analyses_failed":      self.analyses_failed,
            "avg_duration_ms":      round(self.avg_duration_ms, 2),
            "uptime_sec":           round(self.uptime_sec, 2),
        }
