"""iios/investment/market/market_state/market_statistics.py"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MarketStatistics:
    """Aggregate statistics for the Market Intelligence Engine."""

    total_snapshots:   int   = 0
    total_analyses:    int   = 0
    failed_analyses:   int   = 0
    total_markets:     int   = 0
    active_markets:    int   = 0
    avg_duration_ms:   float = 0.0

    regime_counts:     dict[str, int] = field(default_factory=dict)
    trend_counts:      dict[str, int] = field(default_factory=dict)
    volatility_counts: dict[str, int] = field(default_factory=dict)

    # Running sum for avg calculation (excluded from to_dict)
    _sum_duration: float = 0.0

    @property
    def success_rate(self) -> float:
        if self.total_analyses == 0:
            return 0.0
        return (self.total_analyses - self.failed_analyses) / self.total_analyses

    def record_analysis(self, duration_ms: float, *, failed: bool = False) -> None:
        self.total_analyses += 1
        if failed:
            self.failed_analyses += 1
        self._sum_duration  += duration_ms
        self.avg_duration_ms = self._sum_duration / self.total_analyses

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_snapshots":   self.total_snapshots,
            "total_analyses":    self.total_analyses,
            "failed_analyses":   self.failed_analyses,
            "total_markets":     self.total_markets,
            "active_markets":    self.active_markets,
            "avg_duration_ms":   self.avg_duration_ms,
            "success_rate":      self.success_rate,
            "regime_counts":     self.regime_counts,
            "trend_counts":      self.trend_counts,
            "volatility_counts": self.volatility_counts,
        }
