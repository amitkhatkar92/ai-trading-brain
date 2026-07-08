"""
iios/intelligence/forecast/forecast/forecast_statistics.py
===========================================================
Pure statistical utilities used by forecast models.
No external dependencies — standard library only.
"""
from __future__ import annotations

import math
from typing import Sequence


def mean(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def variance(values: Sequence[float], sample: bool = True) -> float:
    n = len(values)
    if n < 2:
        return 0.0
    mu    = mean(values)
    total = sum((x - mu) ** 2 for x in values)
    return total / (n - 1 if sample else n)


def std_dev(values: Sequence[float], sample: bool = True) -> float:
    return math.sqrt(variance(values, sample))


def median(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    n = len(s)
    mid = n // 2
    if n % 2 == 0:
        return (s[mid - 1] + s[mid]) / 2.0
    return s[mid]


def percentile(values: Sequence[float], p: float) -> float:
    """
    Linear-interpolation percentile.
    p must be in [0, 100].
    """
    if not values:
        return 0.0
    s = sorted(values)
    n = len(s)
    idx = (p / 100.0) * (n - 1)
    lo  = int(idx)
    hi  = min(lo + 1, n - 1)
    frac = idx - lo
    return s[lo] * (1 - frac) + s[hi] * frac


def confidence_interval(
    values:    Sequence[float],
    ci_level:  float = 0.90,
) -> tuple[float, float]:
    """
    Return (lower, upper) non-parametric percentile CI.
    ci_level should be in (0, 1).
    """
    tail = (1.0 - ci_level) / 2.0
    lo   = percentile(values, tail * 100.0)
    hi   = percentile(values, (1.0 - tail) * 100.0)
    return lo, hi


def z_score_ci(ci_level: float = 0.90) -> float:
    """
    Approximate normal z-score for a two-tailed CI.
    Only valid for levels: 0.90, 0.95, 0.99.
    """
    _TABLE = {0.90: 1.645, 0.95: 1.960, 0.99: 2.576}
    return _TABLE.get(round(ci_level, 2), 1.645)


def normal_ci(
    point_estimate: float,
    std_error:      float,
    ci_level:       float = 0.90,
) -> tuple[float, float]:
    """
    Symmetric parametric CI assuming normality.
    Returns (lower, upper).
    """
    z  = z_score_ci(ci_level)
    lo = point_estimate - z * std_error
    hi = point_estimate + z * std_error
    return lo, hi


def weighted_mean(
    values:  Sequence[float],
    weights: Sequence[float],
) -> float:
    if not values or not weights:
        return 0.0
    total_w = sum(weights)
    if total_w == 0.0:
        return mean(values)
    return sum(v * w for v, w in zip(values, weights)) / total_w


def mae(predicted: Sequence[float], actual: Sequence[float]) -> float:
    if not predicted or not actual:
        return 0.0
    n = min(len(predicted), len(actual))
    return sum(abs(p - a) for p, a in zip(predicted, actual)) / n


def rmse(predicted: Sequence[float], actual: Sequence[float]) -> float:
    if not predicted or not actual:
        return 0.0
    n = min(len(predicted), len(actual))
    mse = sum((p - a) ** 2 for p, a in zip(predicted, actual)) / n
    return math.sqrt(mse)


def mape(predicted: Sequence[float], actual: Sequence[float]) -> float:
    """Mean absolute percentage error. Returns value in [0, ∞)."""
    if not predicted or not actual:
        return 0.0
    n    = min(len(predicted), len(actual))
    vals = [
        abs((p - a) / a) if a != 0 else 0.0
        for p, a in zip(predicted, actual)
    ]
    return sum(vals[:n]) / n


def directional_accuracy(
    predicted: Sequence[float],
    actual:    Sequence[float],
    baseline:  float = 0.0,
) -> float:
    """Fraction of predictions with correct direction vs baseline."""
    if len(predicted) < 1 or len(actual) < 1:
        return 0.0
    n = min(len(predicted), len(actual))
    hits = sum(
        1 for p, a in zip(predicted, actual)
        if (p - baseline) * (a - baseline) > 0
    )
    return hits / n


def clamp_probability(p: float) -> float:
    """Clamp to [0, 1]."""
    return max(0.0, min(1.0, p))
