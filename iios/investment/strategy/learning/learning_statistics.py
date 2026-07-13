"""iios/investment/strategy/learning/learning_statistics.py
Pure-math utilities for the Strategy Learning Engine.
No external dependencies — only math and statistics from the standard library.
"""
from __future__ import annotations

import math
import statistics
from typing import List, Optional, Sequence, Tuple


# ── basic helpers ─────────────────────────────────────────────────────────────

def clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, v))


def safe_div(num: float, den: float, default: float = 0.0) -> float:
    return num / den if den != 0.0 else default


# ── moving averages ───────────────────────────────────────────────────────────

def ewma(values: List[float], alpha: float = 0.2) -> float:
    """Exponential weighted moving average. Most recent value weighted highest."""
    if not values:
        return 0.0
    result = values[0]
    for v in values[1:]:
        result = alpha * v + (1.0 - alpha) * result
    return result


def rolling_mean(values: List[float], window: int) -> List[float]:
    """Unweighted rolling mean of given window size."""
    if not values or window <= 0:
        return []
    result = []
    for i in range(len(values)):
        start = max(0, i - window + 1)
        result.append(statistics.mean(values[start: i + 1]))
    return result


# ── trend / regression ────────────────────────────────────────────────────────

def linear_trend(values: List[float]) -> float:
    """
    Slope of the best-fit line through (index, value) pairs.
    Positive → improving trend; negative → declining trend.
    Returns 0 if fewer than 2 values.
    """
    n = len(values)
    if n < 2:
        return 0.0
    xs = list(range(n))
    x_mean = (n - 1) / 2.0
    y_mean = statistics.mean(values)
    num = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, values))
    den = sum((x - x_mean) ** 2 for x in xs)
    return safe_div(num, den, 0.0)


def normalised_trend(values: List[float], scale: float = 10.0) -> float:
    """
    Normalised trend: raw slope / (mean * scale), clamped to [-100, 100].
    Removes the effect of absolute score magnitude.
    """
    if not values:
        return 0.0
    mean = statistics.mean(values)
    slope = linear_trend(values)
    return clamp(safe_div(slope, max(abs(mean), 1.0)) * scale * 100.0, -100.0, 100.0)


# ── drift / deviation ─────────────────────────────────────────────────────────

def drift_magnitude(baseline: float, current: float) -> float:
    """
    Signed percentage drift from baseline.
    Positive → improvement; negative → degradation.
    """
    return safe_div(current - baseline, abs(baseline), 0.0)


def drift_score(baseline: float, current: float, ceiling: float = 0.30) -> float:
    """
    0-100 drift severity score.
    0 = no change from baseline, 100 = drift >= ceiling (30% by default).
    Sign-aware: improvement → score < 50, degradation → score > 50.
    """
    pct = drift_magnitude(baseline, current)
    # Normalise to 0-100 degradation score
    degradation = clamp(-pct / ceiling * 100.0, -100.0, 100.0)
    # Map [-100, 100] to [0, 100] where 50=no change
    return clamp(50.0 + degradation / 2.0)


def z_score(value: float, mean: float, std: float) -> float:
    """Standardised z-score. Returns 0 if std is zero."""
    return safe_div(value - mean, std, 0.0)


# ── consistency / quality ─────────────────────────────────────────────────────

def coefficient_of_variation(values: List[float]) -> float:
    """CV = std / |mean|. Returns 0 for constant series or empty list."""
    if len(values) < 2:
        return 0.0
    mean = statistics.mean(values)
    std  = statistics.stdev(values)
    return safe_div(std, abs(mean), 0.0)


def consistency_score(values: List[float]) -> float:
    """
    0-100; 100 = perfectly consistent (zero variation).
    Inverse of the coefficient of variation, clamped.
    """
    if len(values) < 2:
        return 100.0
    cv = coefficient_of_variation(values)
    return clamp(max(0.0, 100.0 - cv * 100.0))


def improvement_rate(prev: float, curr: float) -> float:
    """Signed improvement: positive = better, negative = worse."""
    return curr - prev


# ── window utilities ──────────────────────────────────────────────────────────

def last_n(values: List[float], n: int) -> List[float]:
    """Return the last n values from a list."""
    return values[-n:] if values else []


def split_baseline_recent(
    values: List[float],
    baseline_n: int,
    recent_n: int,
) -> Tuple[List[float], List[float]]:
    """
    Split a list into baseline (first N) and recent (last M) windows.
    Windows may overlap if the list is short.
    """
    if not values:
        return [], []
    baseline = values[:baseline_n]
    recent   = values[-recent_n:]
    return baseline, recent


# ── pattern helpers ───────────────────────────────────────────────────────────

def percentile(values: List[float], p: float) -> float:
    """Simple linear-interpolation percentile (0 <= p <= 100)."""
    if not values:
        return 0.0
    sv = sorted(values)
    n  = len(sv)
    idx = (p / 100.0) * (n - 1)
    lo  = int(idx)
    hi  = min(lo + 1, n - 1)
    frac = idx - lo
    return sv[lo] * (1.0 - frac) + sv[hi] * frac


def above_threshold_rate(values: List[float], threshold: float) -> float:
    """Fraction of values > threshold. Returns 0.0 for empty list."""
    if not values:
        return 0.0
    return sum(1 for v in values if v > threshold) / len(values)
