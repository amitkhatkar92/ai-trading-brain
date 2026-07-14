"""iios/investment/decision/confidence/confidence_trends.py
ConfidenceTrendAnalyzer — detects trends in a subject's confidence history.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Any, Dict, List

from iios.investment.decision.confidence.confidence_constants import (
    TrendDirection,
    TREND_WINDOW_SIZE,
)


@dataclass(frozen=True)
class TrendResult:
    sample_count:    int
    mean:            float
    std_dev:         float
    slope:           float    # per-step change (positive = improving)
    direction:       TrendDirection
    recent_mean:     float    # last TREND_WINDOW_SIZE/2 samples
    earlier_mean:    float    # first TREND_WINDOW_SIZE/2 samples
    delta:           float    # recent_mean - earlier_mean
    trend_confidence: float   # 0–100 how strong the trend signal is

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sample_count":     self.sample_count,
            "mean":             round(self.mean, 2),
            "std_dev":          round(self.std_dev, 2),
            "slope":            round(self.slope, 4),
            "direction":        self.direction.value,
            "recent_mean":      round(self.recent_mean, 2),
            "earlier_mean":     round(self.earlier_mean, 2),
            "delta":            round(self.delta, 2),
            "trend_confidence": round(self.trend_confidence, 2),
        }


class ConfidenceTrendAnalyzer:
    """Analyzes confidence trends from a time-ordered list of scores."""

    def analyze(self, series: List[float]) -> TrendResult:
        n = len(series)

        if n == 0:
            return TrendResult(
                sample_count=0, mean=0.0, std_dev=0.0, slope=0.0,
                direction=TrendDirection.STABLE, recent_mean=0.0,
                earlier_mean=0.0, delta=0.0, trend_confidence=0.0,
            )

        if n == 1:
            return TrendResult(
                sample_count=1, mean=series[0], std_dev=0.0, slope=0.0,
                direction=TrendDirection.STABLE, recent_mean=series[0],
                earlier_mean=series[0], delta=0.0, trend_confidence=0.0,
            )

        mean = statistics.mean(series)
        std_dev = statistics.stdev(series) if n > 1 else 0.0

        # Linear slope using least-squares
        xs = list(range(n))
        x_mean = statistics.mean(xs)
        num = sum((x - x_mean) * (y - mean) for x, y in zip(xs, series))
        denom = sum((x - x_mean) ** 2 for x in xs)
        slope = num / denom if denom != 0 else 0.0

        # Recent vs earlier split
        half = max(1, n // 2)
        recent_mean  = statistics.mean(series[-half:])
        earlier_mean = statistics.mean(series[:half])
        delta = recent_mean - earlier_mean

        # Direction — base on delta and residual std_dev (not raw std_dev)
        # Residuals from linear trend reflect true noise, not the trend itself.
        predicted = [mean + slope * (x - x_mean) for x in xs]
        residuals = [series[i] - predicted[i] for i in range(n)]
        residual_std = statistics.stdev(residuals) if n > 1 else 0.0

        if residual_std > 12.0:
            direction = TrendDirection.VOLATILE
        elif abs(delta) < 3.0 and abs(slope) < 0.5:
            direction = TrendDirection.STABLE
        elif delta > 3.0:
            direction = TrendDirection.IMPROVING
        else:
            direction = TrendDirection.DECLINING

        # Trend confidence: higher when sample count is large and slope is consistent
        trend_confidence = min(100.0, (n / TREND_WINDOW_SIZE) * 50.0 + abs(slope) * 5.0)

        return TrendResult(
            sample_count=n,
            mean=round(mean, 4),
            std_dev=round(std_dev, 4),
            slope=round(slope, 6),
            direction=direction,
            recent_mean=round(recent_mean, 4),
            earlier_mean=round(earlier_mean, 4),
            delta=round(delta, 4),
            trend_confidence=round(trend_confidence, 4),
        )
