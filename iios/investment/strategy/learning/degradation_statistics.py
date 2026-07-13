"""iios/investment/strategy/learning/degradation_statistics.py
Pure-math utilities for drift and degradation detection.
"""
from __future__ import annotations

import math
import statistics
from typing import List, Optional, Tuple

from iios.investment.strategy.learning.learning_statistics import (
    clamp, safe_div, z_score
)


def degradation_score(baseline: float, current: float, ceiling: float = 0.40) -> float:
    """
    0-100 degradation severity.
    0 = no degradation (current >= baseline).
    100 = current has dropped by ceiling fraction or more.
    """
    if current >= baseline:
        return 0.0
    pct_drop = (baseline - current) / max(abs(baseline), 1e-9)
    return clamp(pct_drop / ceiling * 100.0)


def improvement_score(baseline: float, current: float, ceiling: float = 0.40) -> float:
    """0-100 improvement score. 0 = no improvement, 100 = improved by ceiling or more."""
    if current <= baseline:
        return 0.0
    pct_gain = (current - baseline) / max(abs(baseline), 1e-9)
    return clamp(pct_gain / ceiling * 100.0)


def rolling_z_scores(values: List[float], window: int = 10) -> List[float]:
    """
    Compute rolling z-scores using a trailing window mean and std.
    Returns list same length as values.
    """
    if not values:
        return []
    result: List[float] = []
    for i, v in enumerate(values):
        start = max(0, i - window)
        window_vals = values[start:i]
        if len(window_vals) < 2:
            result.append(0.0)
        else:
            mean = statistics.mean(window_vals)
            std  = statistics.stdev(window_vals)
            result.append(z_score(v, mean, std))
    return result


def cumulative_drift(values: List[float]) -> float:
    """
    Cumulative percentage drift from first value to last value.
    Positive = overall improvement; negative = overall degradation.
    """
    if len(values) < 2:
        return 0.0
    return safe_div(values[-1] - values[0], abs(values[0]), 0.0)


def max_drawdown_from_scores(scores: List[float]) -> float:
    """
    Maximum drawdown in the score series (as a fraction of peak).
    Analogous to price drawdown but applied to evaluation scores.
    """
    if not scores:
        return 0.0
    peak = scores[0]
    max_dd = 0.0
    for s in scores:
        peak = max(peak, s)
        dd   = safe_div(peak - s, peak, 0.0)
        max_dd = max(max_dd, dd)
    return max_dd


def drift_acceleration(recent: List[float], older: List[float]) -> float:
    """
    How much faster the drift is in 'recent' vs 'older' window.
    Negative = drift accelerating downward; positive = recovery accelerating.
    """
    if not recent or not older:
        return 0.0
    recent_mean = statistics.mean(recent)
    older_mean  = statistics.mean(older)
    return recent_mean - older_mean


def signal_to_noise_ratio(values: List[float]) -> float:
    """
    SNR = |mean| / std. Higher = cleaner / more predictable signal.
    Returns 0 if std is zero.
    """
    if len(values) < 2:
        return 0.0
    mean = statistics.mean(values)
    std  = statistics.stdev(values)
    return safe_div(abs(mean), std, 0.0)


def is_statistically_significant(
    baseline: List[float],
    current: List[float],
    threshold_z: float = 1.65,   # 95th percentile
) -> bool:
    """
    Welch's t-test simplified: check if means differ by more than threshold_z * pooled_se.
    Returns True if the difference is likely real (not noise).
    """
    if len(baseline) < 2 or len(current) < 2:
        return False
    b_mean = statistics.mean(baseline)
    c_mean = statistics.mean(current)
    b_var  = statistics.variance(baseline)
    c_var  = statistics.variance(current)
    se     = math.sqrt(b_var / len(baseline) + c_var / len(current))
    if se < 1e-9:
        # Zero variance: if means differ, the difference is certain
        return abs(c_mean - b_mean) > 1e-9
    t_stat = (c_mean - b_mean) / se
    return abs(t_stat) >= threshold_z
