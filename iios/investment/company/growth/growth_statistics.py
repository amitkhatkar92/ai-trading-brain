"""iios/investment/company/growth/growth_statistics.py
Statistical utilities for growth calculations.
No numpy — stdlib only.
"""
from __future__ import annotations

import math
from typing import List, Optional, Tuple

from iios.investment.company.growth.growth_profile import GrowthTrend


def _clean(values: List[Optional[float]]) -> List[float]:
    return [v for v in values if v is not None and math.isfinite(v)]


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def safe_mean(values: List[Optional[float]]) -> Optional[float]:
    c = _clean(values)
    return sum(c) / len(c) if c else None


def safe_median(values: List[Optional[float]]) -> Optional[float]:
    c = sorted(_clean(values))
    n = len(c)
    if n == 0:
        return None
    mid = n // 2
    return (c[mid - 1] + c[mid]) / 2.0 if n % 2 == 0 else c[mid]


def safe_stdev(values: List[Optional[float]]) -> Optional[float]:
    c = _clean(values)
    if len(c) < 2:
        return None
    mean = sum(c) / len(c)
    return math.sqrt(sum((x - mean) ** 2 for x in c) / (len(c) - 1))


def coefficient_of_variation(values: List[Optional[float]]) -> Optional[float]:
    """Returns CV (stdev/mean). Returns None if mean is zero or too few values."""
    c = _clean(values)
    if len(c) < 2:
        return None
    mean = sum(c) / len(c)
    if abs(mean) < 1e-9:
        return None
    stdev = math.sqrt(sum((x - mean) ** 2 for x in c) / (len(c) - 1))
    return abs(stdev / mean)


def cagr(start: float, end: float, n_years: float) -> Optional[float]:
    """
    Compound Annual Growth Rate.
    Returns None if inputs are invalid (negative base, zero years).
    """
    if n_years <= 0 or start <= 0 or end < 0:
        return None
    try:
        return (end / start) ** (1.0 / n_years) - 1.0
    except (ZeroDivisionError, ValueError):
        return None


def cagr_from_series(values: List[Optional[float]]) -> Optional[float]:
    """
    Compute CAGR from a time-series of values (first → last, n-1 periods).
    Values must be in chronological order (oldest first).
    """
    c = _clean(values)
    if len(c) < 2:
        return None
    return cagr(c[0], c[-1], len(c) - 1)


def yoy_growth(current: Optional[float], prior: Optional[float]) -> Optional[float]:
    """Year-over-year growth rate."""
    if current is None or prior is None or prior == 0:
        return None
    if prior < 0:
        # Can't compute meaningful YoY when prior is negative
        return None
    return (current - prior) / abs(prior)


def growth_rates_from_series(values: List[Optional[float]]) -> List[float]:
    """Compute YoY growth rates for consecutive pairs in a series."""
    c = _clean(values)
    rates = []
    for i in range(1, len(c)):
        g = yoy_growth(c[i], c[i - 1])
        if g is not None:
            rates.append(g)
    return rates


def trend_from_growth_rates(rates: List[float]) -> GrowthTrend:
    """
    Determine growth trend from a series of growth rates.
    Compares first-half average to second-half average.
    """
    if not rates:
        return GrowthTrend.INSUFFICIENT_DATA
    if len(rates) == 1:
        if rates[0] > 0.02:
            return GrowthTrend.STABLE
        if rates[0] < -0.02:
            return GrowthTrend.DECLINING
        return GrowthTrend.STABLE

    mid = len(rates) // 2
    first_half = rates[:mid] if mid > 0 else rates[:1]
    second_half = rates[mid:] if mid < len(rates) else rates[-1:]

    avg_first  = sum(first_half)  / len(first_half)
    avg_second = sum(second_half) / len(second_half)

    # CV for volatility
    cv = coefficient_of_variation(rates)
    if cv is not None and cv > 0.8:
        return GrowthTrend.VOLATILE

    diff = avg_second - avg_first
    if diff > 0.03:
        return GrowthTrend.ACCELERATING
    if diff < -0.03:
        if avg_second < 0:
            return GrowthTrend.DECLINING
        return GrowthTrend.DECELERATING
    if avg_second < 0 and avg_first < 0:
        return GrowthTrend.DECLINING
    if avg_second > 0 and avg_first < 0:
        return GrowthTrend.RECOVERING
    return GrowthTrend.STABLE


def trend_from_direction_string(direction: Optional[str]) -> GrowthTrend:
    """Map direction strings from EarningsSnapshot to GrowthTrend."""
    if direction is None:
        return GrowthTrend.INSUFFICIENT_DATA
    d = direction.lower()
    if "accelerat" in d:
        return GrowthTrend.ACCELERATING
    if "improv" in d or "increas" in d:
        return GrowthTrend.STABLE   # improving → at least stable
    if "declin" in d or "decreas" in d:
        return GrowthTrend.DECLINING
    if "deceler" in d:
        return GrowthTrend.DECELERATING
    if "recover" in d:
        return GrowthTrend.RECOVERING
    if "volat" in d or "mixed" in d:
        return GrowthTrend.VOLATILE
    return GrowthTrend.STABLE


def score_from_cagr(rate: Optional[float]) -> float:
    """Convert a CAGR to a 0-100 score."""
    if rate is None:
        return 0.0
    if rate >= 0.30:
        return 100.0
    if rate >= 0.20:
        return 80.0 + (rate - 0.20) / 0.10 * 20.0
    if rate >= 0.10:
        return 50.0 + (rate - 0.10) / 0.10 * 30.0
    if rate >= 0.0:
        return rate / 0.10 * 50.0
    # Negative
    return clamp(50.0 + rate * 100.0, 0, 50.0)


def mean_reversion_estimate(
    historical_cagr: Optional[float],
    long_run_mean:   float = 0.10,
    weight:          float = 0.60,  # weight on historical (1-weight on mean-reversion)
) -> Optional[float]:
    """
    Forecast growth by blending historical CAGR with long-run mean.
    Conservative: high-growth companies drift toward the mean.
    """
    if historical_cagr is None:
        return long_run_mean
    return historical_cagr * weight + long_run_mean * (1.0 - weight)
