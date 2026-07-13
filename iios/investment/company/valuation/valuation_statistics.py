"""iios/investment/company/valuation/valuation_statistics.py
Statistical utilities for valuation calculations.
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional


def _clean(values: List[Optional[float]]) -> List[float]:
    return [v for v in values if v is not None and math.isfinite(v)]


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
    c = _clean(values)
    if len(c) < 2:
        return None
    mean = sum(c) / len(c)
    stdev = safe_stdev(values)
    if stdev is None or mean == 0:
        return None
    return abs(stdev / mean)


def clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, v))


def present_value(cash_flows: List[float], discount_rate: float) -> float:
    """Discount a series of cash flows to present value (t=1..n)."""
    total = 0.0
    for t, cf in enumerate(cash_flows, start=1):
        total += cf / (1.0 + discount_rate) ** t
    return total


def gordon_growth_terminal_value(
    fcf_terminal: float,
    discount_rate: float,
    terminal_growth: float,
) -> float:
    """
    Gordon Growth Model terminal value.
    TV = FCF_{n+1} / (r - g) = FCF_n * (1 + g) / (r - g)
    """
    if discount_rate <= terminal_growth:
        # WACC must exceed terminal growth — clamp growth to 90% of WACC
        terminal_growth = discount_rate * 0.90
    return fcf_terminal * (1.0 + terminal_growth) / (discount_rate - terminal_growth)


def percentile_rank(value: float, series: List[float]) -> float:
    """Fraction of series ≤ value (0-100)."""
    if not series:
        return 50.0
    return 100.0 * sum(1 for x in series if x <= value) / len(series)


def weighted_average(values: Dict[str, float], weights: Dict[str, float]) -> float:
    """
    Weighted average of values using provided weights.
    Only includes keys present in both dicts.
    Normalises weights automatically.
    """
    total_w = 0.0
    total   = 0.0
    for key, val in values.items():
        w = weights.get(key, 0.0)
        total   += val * w
        total_w += w
    return total / total_w if total_w > 0 else 0.0
