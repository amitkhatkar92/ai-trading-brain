"""iios/investment/company/opportunity/opportunity_statistics.py
Pure, side-effect-free statistical helpers for the Opportunity Engine.
No external dependencies; no numpy.
"""
from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

from iios.investment.company.opportunity.opportunity_profile import (
    ConfidenceLevel, OpportunityLifecycle, OpportunityPriority,
    OpportunityStrength,
)


# ── Numeric utilities ─────────────────────────────────────────────────────────

def clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    """Clamp *value* to [lo, hi]."""
    return max(lo, min(hi, value))


def safe_float(v: object, default: float = 0.0) -> float:
    """Convert *v* to float; return *default* on failure."""
    if v is None:
        return default
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def safe_average(values: Sequence[Optional[float]], default: float = 50.0) -> float:
    """Return mean of non-None values; *default* if all None."""
    valid = [float(v) for v in values if v is not None]
    return sum(valid) / len(valid) if valid else default


def weighted_average(
    components: List[Tuple[float, float]],   # [(score, weight), ...]
    default: float = 50.0,
) -> float:
    """
    Weighted average of (score, weight) pairs.
    Weights need NOT sum to 1; they are normalised internally.
    Returns *default* if total_weight == 0.
    """
    total_w = sum(w for _, w in components if w > 0)
    if total_w == 0:
        return default
    return sum(s * w for s, w in components if w > 0) / total_w


def percentile_rank(value: float, population: List[float]) -> float:
    """
    Return 0-100 percentile rank of *value* within *population*.
    100 = best (highest), 0 = worst.
    Returns 50.0 for empty population.
    """
    if not population:
        return 50.0
    below = sum(1 for x in population if x < value)
    return clamp(below / len(population) * 100.0)


def score_delta(
    current: float,
    previous: Optional[float],
    *,
    scale: float = 5.0,
) -> float:
    """
    Normalised delta between two scores (0-100 range).
    Returns 0.0 if previous is None.
    *scale*: +/- change that maps to ±1.0 normalised delta.
    """
    if previous is None:
        return 0.0
    return (current - previous) / scale


def moving_average(series: List[float], window: int) -> List[float]:
    """Simple moving average over a list (returns same length as input)."""
    if not series or window <= 0:
        return series
    result: List[float] = []
    for i in range(len(series)):
        start = max(0, i - window + 1)
        window_vals = series[start : i + 1]
        result.append(sum(window_vals) / len(window_vals))
    return result


def trend_slope(series: List[float]) -> float:
    """
    Simple linear regression slope of the series.
    Returns 0.0 for series with fewer than 2 points.
    """
    n = len(series)
    if n < 2:
        return 0.0
    xs = list(range(n))
    x_mean = sum(xs) / n
    y_mean = sum(series) / n
    num = sum((xs[i] - x_mean) * (series[i] - y_mean) for i in range(n))
    den = sum((xs[i] - x_mean) ** 2 for i in range(n))
    return num / den if den != 0 else 0.0


# ── Mapping helpers ───────────────────────────────────────────────────────────

def score_to_strength(score: float) -> OpportunityStrength:
    if score >= 80:
        return OpportunityStrength.EXCEPTIONAL
    if score >= 65:
        return OpportunityStrength.STRONG
    if score >= 50:
        return OpportunityStrength.MODERATE
    if score >= 35:
        return OpportunityStrength.WEAK
    return OpportunityStrength.POOR


def score_to_priority(
    score: float,
    lifecycle: OpportunityLifecycle,
) -> OpportunityPriority:
    if lifecycle in (OpportunityLifecycle.EXPIRED, OpportunityLifecycle.ARCHIVED):
        return OpportunityPriority.WATCHLIST
    if score >= 75 and lifecycle in (
        OpportunityLifecycle.HIGH_CONVICTION, OpportunityLifecycle.CONFIRMED
    ):
        return OpportunityPriority.CRITICAL
    if score >= 65:
        return OpportunityPriority.HIGH
    if score >= 50:
        return OpportunityPriority.MEDIUM
    if score >= 35:
        return OpportunityPriority.LOW
    return OpportunityPriority.WATCHLIST


def confidence_to_level(confidence: float) -> ConfidenceLevel:
    if confidence >= 0.80:
        return ConfidenceLevel.VERY_HIGH
    if confidence >= 0.65:
        return ConfidenceLevel.HIGH
    if confidence >= 0.50:
        return ConfidenceLevel.MODERATE
    if confidence >= 0.35:
        return ConfidenceLevel.LOW
    return ConfidenceLevel.VERY_LOW


def strength_to_label(strength: OpportunityStrength) -> str:
    return strength.value


def compute_data_completeness(available: int, total: int) -> float:
    """Return fraction of available data sources (0-1)."""
    if total <= 0:
        return 0.0
    return clamp(available / total, 0.0, 1.0)
