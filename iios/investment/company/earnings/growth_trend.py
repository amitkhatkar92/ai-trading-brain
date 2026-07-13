"""iios/investment/company/earnings/growth_trend.py
Computes growth rates for earnings series and categorises direction.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from iios.investment.company.earnings.earnings_report import EarningsReport, TrendDirection
from iios.investment.company.earnings.earnings_statistics import (
    growth_rates, compound_growth_rate, _clean, linear_slope,
)


@dataclass
class GrowthTrendMetrics:
    field_name:      str
    values:          List[Optional[float]] = field(default_factory=list)
    growth_rate_series: List[Optional[float]] = field(default_factory=list)

    latest_growth:   Optional[float] = None   # most recent period-on-period
    cagr:            Optional[float] = None   # CAGR over all periods
    avg_growth:      Optional[float] = None
    growth_slope:    Optional[float] = None   # slope of the growth rates

    direction:       TrendDirection = TrendDirection.INSUFFICIENT
    periods_used:    int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "field_name":    self.field_name,
            "latest_growth": self.latest_growth,
            "cagr":          self.cagr,
            "avg_growth":    self.avg_growth,
            "growth_slope":  self.growth_slope,
            "direction":     self.direction.value,
            "periods_used":  self.periods_used,
        }


def _classify(values: List[Optional[float]], growth: List[Optional[float]]) -> TrendDirection:
    """Classify trend from growth rates."""
    clean_g = _clean(growth)
    clean_v = _clean(values)

    if len(clean_g) < 2:
        return TrendDirection.INSUFFICIENT

    recent     = clean_g[-1]
    prior_avg  = sum(clean_g[:-1]) / len(clean_g[:-1])
    latest_val = clean_v[-1] if clean_v else None
    prior_val  = clean_v[-2] if len(clean_v) >= 2 else None

    # Detect reversal (sign change)
    if prior_val is not None and latest_val is not None:
        if prior_val < 0 and latest_val > 0:
            return TrendDirection.REVERSAL_UP
        if prior_val > 0 and latest_val < 0:
            return TrendDirection.REVERSAL_DOWN

    # Acceleration vs deceleration
    positive_trend = all(r >= 0 for r in clean_g[-3:]) if len(clean_g) >= 3 else recent >= 0
    negative_trend = all(r <= 0 for r in clean_g[-3:]) if len(clean_g) >= 3 else recent < 0

    if positive_trend:
        if abs(prior_avg) < 0.005:
            slope = linear_slope(clean_g)
            return TrendDirection.ACCELERATING if slope > 0 else TrendDirection.STABLE
        if recent > prior_avg * 1.15:
            return TrendDirection.ACCELERATING
        if recent < prior_avg * 0.70:
            return TrendDirection.DECELERATING
        return TrendDirection.STABLE
    elif negative_trend:
        if recent > prior_avg * 0.70:
            return TrendDirection.RECOVERING
        return TrendDirection.DETERIORATING

    return TrendDirection.STABLE


class GrowthTrendAnalyzer:
    """Computes growth trends for any numeric earnings field."""

    def analyze(
        self,
        history: List[EarningsReport],
        field_name: str,
    ) -> GrowthTrendMetrics:
        values = [getattr(r, field_name, None) for r in history]
        rates  = growth_rates(values)

        m = GrowthTrendMetrics(
            field_name=field_name,
            values=values,
            growth_rate_series=rates,
            periods_used=len(history),
        )

        clean_rates = _clean(rates)
        clean_vals  = _clean(values)

        if clean_rates:
            m.latest_growth = clean_rates[-1]
            m.avg_growth    = sum(clean_rates) / len(clean_rates)
            if len(clean_rates) >= 3:
                m.growth_slope = linear_slope(clean_rates)

        m.cagr      = compound_growth_rate(values)
        m.direction = _classify(values, rates)

        return m
