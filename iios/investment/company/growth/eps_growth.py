"""iios/investment/company/growth/eps_growth.py
EPS-specific growth analysis.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from iios.investment.company.growth.growth_profile import (
    CAGRProfile, GrowthTrend, classify_growth,
)
from iios.investment.company.growth.growth_statistics import (
    cagr, cagr_from_series, yoy_growth, growth_rates_from_series,
    trend_from_growth_rates, trend_from_direction_string, clamp,
)


def compute_eps_cagr_profile(
    cagr_eps:      Optional[float],   # from EarningsSnapshot.trend
    eps_direction: Optional[str],     # from EarningsSnapshot.trend
    eps_series:    Optional[List[float]] = None,  # optional explicit series
    history_depth: int = 0,
) -> CAGRProfile:
    """
    Build a CAGRProfile for EPS from available data.
    Prefers explicit time-series; falls back to EarningsSnapshot aggregates.
    """
    if eps_series and len(eps_series) >= 2:
        rates = growth_rates_from_series(eps_series)
        n = len(eps_series)
        trend = trend_from_growth_rates(rates) if rates else GrowthTrend.INSUFFICIENT_DATA
        c1  = cagr(eps_series[-2], eps_series[-1], 1)  if n >= 2 else None
        c3  = cagr(eps_series[-4], eps_series[-1], 3)  if n >= 4 else None
        c5  = cagr(eps_series[-6], eps_series[-1], 5)  if n >= 6 else None
        c10 = cagr(eps_series[0],  eps_series[-1], n - 1) if n >= 11 else None
        best = c5 or c3 or c1
        return CAGRProfile(
            cagr_1y=c1, cagr_3y=c3, cagr_5y=c5, cagr_10y=c10,
            best_available=best, trend=trend, periods_used=n,
            label=classify_growth(best),
        )

    # Fall back to EarningsSnapshot aggregate
    trend = trend_from_direction_string(eps_direction)
    return CAGRProfile(
        cagr_3y=cagr_eps,  # EarningsSnapshot typically computes a ~3-5y CAGR
        best_available=cagr_eps,
        trend=trend,
        periods_used=history_depth,
        label=classify_growth(cagr_eps),
    )
