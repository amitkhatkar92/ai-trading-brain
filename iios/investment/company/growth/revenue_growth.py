"""iios/investment/company/growth/revenue_growth.py
Revenue growth analysis engine.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from iios.investment.company.growth.growth_profile import (
    CAGRProfile, RevenueGrowthProfile, GrowthTrend, classify_growth,
)
from iios.investment.company.growth.growth_statistics import (
    cagr, cagr_from_series, yoy_growth, growth_rates_from_series,
    trend_from_growth_rates, trend_from_direction_string, clamp,
)


class RevenueGrowthEngine:
    """
    Compute revenue growth intelligence from available data.

    Primary sources (in priority order):
    1. Explicit revenue time series (most precise)
    2. EarningsSnapshot trend and risk data (aggregated)
    3. Qualitative direction indicators
    """

    def compute(
        self,
        revenue_series:         Optional[List[float]] = None,  # chronological, oldest first
        current_revenue:        Optional[float] = None,
        prior_revenue:          Optional[float] = None,
        revenue_direction:      Optional[str]  = None,   # from EarningsSnapshot.trend
        revenue_volatility:     Optional[float] = None,  # CV from EarningsSnapshot.risk
        history_depth:          int = 0,
    ) -> RevenueGrowthProfile:
        profile = RevenueGrowthProfile()
        explanation: List[str] = []

        # ── CAGR from series ───────────────────────────────────────────────────
        if revenue_series and len(revenue_series) >= 2:
            profile = self._from_series(revenue_series, explanation)
        else:
            profile = self._from_aggregated(
                current_revenue, prior_revenue, revenue_direction,
                revenue_volatility, history_depth, explanation,
            )

        profile.explanation = explanation
        return profile

    def _from_series(
        self,
        series:      List[float],
        explanation: List[str],
    ) -> RevenueGrowthProfile:
        n = len(series)
        profile = RevenueGrowthProfile()
        rates = growth_rates_from_series(series)

        # CAGRs
        cagr_1y = cagr(series[-2], series[-1], 1) if n >= 2 else None
        cagr_3y = cagr(series[-4], series[-1], 3) if n >= 4 else None
        cagr_5y = cagr(series[-6], series[-1], 5) if n >= 6 else None
        cagr_10y = cagr(series[0],  series[-1], n - 1) if n >= 11 else None

        best = cagr_5y or cagr_3y or cagr_1y

        trend = trend_from_growth_rates(rates) if rates else GrowthTrend.INSUFFICIENT_DATA

        profile.cagr = CAGRProfile(
            cagr_1y=cagr_1y, cagr_3y=cagr_3y, cagr_5y=cagr_5y, cagr_10y=cagr_10y,
            best_available=best, trend=trend, periods_used=n,
            label=classify_growth(best),
        )
        profile.yoy = cagr_1y
        profile.trend = trend

        if best is not None:
            explanation.append(f"Revenue CAGR (best available): {best:.1%}")
        explanation.append(f"Trend: {trend.value} over {n} periods")
        return profile

    def _from_aggregated(
        self,
        current:     Optional[float],
        prior:       Optional[float],
        direction:   Optional[str],
        volatility:  Optional[float],
        depth:       int,
        explanation: List[str],
    ) -> RevenueGrowthProfile:
        profile = RevenueGrowthProfile()

        yoy = yoy_growth(current, prior)
        trend = trend_from_direction_string(direction)

        # Best CAGR estimate from YoY + direction
        best = yoy  # YoY is the most precise single-period estimate

        # If we have direction but no YoY, create a qualitative estimate
        if best is None and direction:
            if "strong" in direction.lower() or "accelerat" in direction.lower():
                best = 0.15  # qualitative estimate
            elif "improv" in direction.lower():
                best = 0.10
            elif "declin" in direction.lower():
                best = -0.05
            elif direction.lower() in ("stable", "flat"):
                best = 0.03

        # Confidence adjustments from volatility
        profile.cagr = CAGRProfile(
            cagr_1y=yoy,
            best_available=best,
            trend=trend,
            periods_used=depth,
            label=classify_growth(best),
        )
        profile.yoy   = yoy
        profile.trend  = trend

        if yoy is not None:
            explanation.append(f"Revenue YoY growth: {yoy:.1%}")
        if direction:
            explanation.append(f"Revenue direction: {direction}")
        if best is None:
            explanation.append("Insufficient data for revenue CAGR")
        return profile
