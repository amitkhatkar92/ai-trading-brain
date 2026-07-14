"""iios/investment/portfolio/diversification/diversification_trends.py

Trend analysis across historical diversification profiles.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from iios.investment.portfolio.diversification.diversification_types import TrendDirection


@dataclass(frozen=True)
class DiversificationTrend:
    """Trend for a single metric over time."""

    metric_name:     str            = ""
    direction:       TrendDirection = TrendDirection.INSUFFICIENT_DATA
    magnitude:       float          = 0.0    # absolute change per period
    periods_analyzed:int            = 0
    current_value:   float          = 0.0
    prior_value:     float          = 0.0
    pct_change:      float          = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric_name":     self.metric_name,
            "direction":       self.direction.value,
            "magnitude":       round(self.magnitude, 4),
            "periods_analyzed":self.periods_analyzed,
            "current_value":   round(self.current_value, 4),
            "prior_value":     round(self.prior_value, 4),
            "pct_change":      round(self.pct_change, 4),
        }


@dataclass(frozen=True)
class TrendsReport:
    """Collection of metric trends."""

    portfolio_id:    str                              = ""
    n_periods:       int                              = 0
    trends:          Dict[str, DiversificationTrend] = field(default_factory=dict)
    improving_count: int                              = 0
    deteriorating_count: int                          = 0
    stable_count:    int                              = 0
    overall_direction: TrendDirection                 = TrendDirection.INSUFFICIENT_DATA

    def to_dict(self) -> Dict[str, Any]:
        return {
            "portfolio_id":       self.portfolio_id,
            "n_periods":          self.n_periods,
            "improving_count":    self.improving_count,
            "deteriorating_count":self.deteriorating_count,
            "stable_count":       self.stable_count,
            "overall_direction":  self.overall_direction.value,
            "trends":             {k: v.to_dict() for k, v in self.trends.items()},
        }


def _compute_trend(metric_name: str, values: List[float]) -> DiversificationTrend:
    if len(values) < 2:
        return DiversificationTrend(
            metric_name=metric_name,
            direction=TrendDirection.INSUFFICIENT_DATA,
            periods_analyzed=len(values),
            current_value=values[-1] if values else 0.0,
        )
    current = values[-1]
    prior   = values[0]
    delta   = current - prior
    pct     = delta / abs(prior) if abs(prior) > 1e-10 else 0.0

    if delta > 0.02:
        direction = TrendDirection.IMPROVING
    elif delta < -0.02:
        direction = TrendDirection.DETERIORATING
    else:
        direction = TrendDirection.STABLE

    return DiversificationTrend(
        metric_name      = metric_name,
        direction        = direction,
        magnitude        = round(abs(delta), 4),
        periods_analyzed = len(values),
        current_value    = round(current, 4),
        prior_value      = round(prior, 4),
        pct_change       = round(pct, 4),
    )


class TrendAnalyzer:
    """Computes trends from a sequence of metric time-series."""

    def analyze(
        self,
        metric_series: Dict[str, List[float]],
        portfolio_id:  str = "",
    ) -> TrendsReport:
        if not metric_series:
            return TrendsReport(portfolio_id=portfolio_id)

        trends: Dict[str, DiversificationTrend] = {}
        for name, values in metric_series.items():
            trends[name] = _compute_trend(name, values)

        n_periods  = max(len(v) for v in metric_series.values()) if metric_series else 0
        improving  = sum(1 for t in trends.values() if t.direction == TrendDirection.IMPROVING)
        deteriorating = sum(1 for t in trends.values() if t.direction == TrendDirection.DETERIORATING)
        stable     = sum(1 for t in trends.values() if t.direction == TrendDirection.STABLE)

        if deteriorating > improving:
            overall = TrendDirection.DETERIORATING
        elif improving > deteriorating:
            overall = TrendDirection.IMPROVING
        elif stable > 0:
            overall = TrendDirection.STABLE
        else:
            overall = TrendDirection.INSUFFICIENT_DATA

        return TrendsReport(
            portfolio_id      = portfolio_id,
            n_periods         = n_periods,
            trends            = trends,
            improving_count   = improving,
            deteriorating_count=deteriorating,
            stable_count      = stable,
            overall_direction = overall,
        )
