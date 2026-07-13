"""iios/investment/company/business_quality/quality_statistics.py
Statistical utilities and quality statistics aggregator.
"""
from __future__ import annotations

import math
from typing import List, Optional


# ─────────────────────────── Core statistics ──────────────────────────────────

def _clean(values: List[Optional[float]]) -> List[float]:
    return [v for v in values if v is not None and math.isfinite(v)]


def safe_mean(values: List[Optional[float]]) -> Optional[float]:
    c = _clean(values)
    return sum(c) / len(c) if c else None


def safe_stdev(values: List[Optional[float]]) -> Optional[float]:
    c = _clean(values)
    if len(c) < 2:
        return None
    mean = sum(c) / len(c)
    variance = sum((x - mean) ** 2 for x in c) / (len(c) - 1)
    return math.sqrt(variance)


def coefficient_of_variation(values: List[Optional[float]]) -> Optional[float]:
    c = _clean(values)
    if len(c) < 2:
        return None
    mean = sum(c) / len(c)
    if mean == 0:
        return None
    stdev = safe_stdev(values)
    return abs(stdev / mean) if stdev is not None else None


def growth_rates(values: List[Optional[float]]) -> List[Optional[float]]:
    """Period-over-period growth rates."""
    result: List[Optional[float]] = []
    for i in range(1, len(values)):
        a, b = values[i - 1], values[i]
        if a is None or b is None or a == 0:
            result.append(None)
        else:
            result.append((b - a) / abs(a) * 100.0)
    return result


def linear_slope(values: List[Optional[float]]) -> Optional[float]:
    """OLS slope of clean values (indexed 0..n-1)."""
    c = _clean(values)
    n = len(c)
    if n < 2:
        return None
    xs = list(range(n))
    x_mean = sum(xs) / n
    y_mean = sum(c) / n
    num = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, c))
    den = sum((x - x_mean) ** 2 for x in xs)
    return num / den if den != 0 else 0.0


def percentile_rank(value: float, series: List[float]) -> float:
    """Fraction of series values ≤ value (0-100)."""
    if not series:
        return 50.0
    return 100.0 * sum(1 for x in series if x <= value) / len(series)


def normalised_slope(values: List[Optional[float]]) -> Optional[float]:
    """Slope / |mean| — scale-independent trend."""
    slope = linear_slope(values)
    c = _clean(values)
    if slope is None or not c:
        return None
    mean = abs(sum(c) / len(c))
    return slope / mean if mean != 0 else slope


def clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))
