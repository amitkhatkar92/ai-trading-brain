"""iios/investment/company/earnings/earnings_statistics.py
Statistical helpers for earnings series — no external dependencies.
"""
from __future__ import annotations

import math
from typing import List, Optional, Tuple


def _clean(values: List[Optional[float]]) -> List[float]:
    """Remove None values."""
    return [v for v in values if v is not None]


def safe_mean(values: List[Optional[float]]) -> Optional[float]:
    clean = _clean(values)
    return sum(clean) / len(clean) if clean else None


def safe_stdev(values: List[Optional[float]]) -> Optional[float]:
    clean = _clean(values)
    if len(clean) < 2:
        return None
    m = sum(clean) / len(clean)
    var = sum((x - m) ** 2 for x in clean) / (len(clean) - 1)
    return math.sqrt(var)


def coefficient_of_variation(values: List[Optional[float]]) -> Optional[float]:
    """CV = stdev / |mean|; lower = more stable."""
    m  = safe_mean(values)
    sd = safe_stdev(values)
    if m is None or sd is None or m == 0:
        return None
    return abs(sd / m)


def growth_rates(values: List[Optional[float]]) -> List[Optional[float]]:
    """YoY / sequential growth rates between consecutive pairs."""
    rates: List[Optional[float]] = []
    clean = list(values)   # preserve None gaps
    for i in range(1, len(clean)):
        prev = clean[i - 1]
        curr = clean[i]
        if prev is None or curr is None or prev == 0:
            rates.append(None)
        else:
            rates.append((curr - prev) / abs(prev))
    return rates


def compound_growth_rate(values: List[Optional[float]]) -> Optional[float]:
    """CAGR-style: (last / first) ^ (1/(n-1)) - 1."""
    clean = _clean(values)
    if len(clean) < 2 or clean[0] == 0 or clean[0] < 0:
        return None
    n = len(clean) - 1
    try:
        return (clean[-1] / clean[0]) ** (1.0 / n) - 1.0
    except (ValueError, ZeroDivisionError):
        return None


def linear_slope(values: List[float]) -> float:
    """OLS slope of the series; positive = uptrend."""
    n = len(values)
    if n < 2:
        return 0.0
    xs = list(range(n))
    xm = n / 2.0 - 0.5
    ym = sum(values) / n
    num = sum((xs[i] - xm) * (values[i] - ym) for i in range(n))
    den = sum((xs[i] - xm) ** 2 for i in range(n))
    return num / den if den != 0 else 0.0


def normalised_slope(values: List[float]) -> Optional[float]:
    """Slope divided by mean (so 0.1 = 10% change per period)."""
    m = sum(values) / len(values) if values else 0
    if m == 0:
        return None
    return linear_slope(values) / abs(m)


def trend_acceleration(values: List[float]) -> Optional[float]:
    """
    Second derivative of the series: positive = acceleration, negative = deceleration.
    Requires at least 3 points.
    """
    if len(values) < 3:
        return None
    rates_raw = [
        (values[i] - values[i - 1]) / abs(values[i - 1])
        if values[i - 1] != 0 else None
        for i in range(1, len(values))
    ]
    clean = _clean(rates_raw)
    if len(clean) < 2:
        return None
    return linear_slope(clean)


def percentile_rank(value: float, series: List[float]) -> float:
    """Return what percentile value is in series (0-100)."""
    if not series:
        return 50.0
    below = sum(1 for x in series if x < value)
    return 100.0 * below / len(series)


def rolling_mean(values: List[float], window: int) -> List[Optional[float]]:
    """Rolling mean of width `window`."""
    result: List[Optional[float]] = []
    for i in range(len(values)):
        if i + 1 < window:
            result.append(None)
        else:
            w = values[i + 1 - window: i + 1]
            result.append(sum(w) / len(w))
    return result


def r_squared(values: List[float]) -> Optional[float]:
    """R² of a linear fit to the series (0=random, 1=perfect trend)."""
    n = len(values)
    if n < 3:
        return None
    xs = list(range(n))
    xm = (n - 1) / 2.0
    ym = sum(values) / n

    ss_res = 0.0
    ss_tot = sum((y - ym) ** 2 for y in values)
    if ss_tot == 0:
        return 1.0

    slope = linear_slope(values)
    intercept = ym - slope * xm
    for i, y in enumerate(values):
        ss_res += (y - (slope * xs[i] + intercept)) ** 2

    return max(0.0, 1.0 - ss_res / ss_tot)
