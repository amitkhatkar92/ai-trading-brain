"""iios/investment/company/integration/company_statistics.py
Pure statistical helpers for the integration layer. No external dependencies.
"""
from __future__ import annotations

import math
import statistics
from typing import Dict, List, Optional, Sequence, Tuple


# ── Numeric utilities ─────────────────────────────────────────────────────────

def clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    """Clamp *value* to [lo, hi]."""
    return max(lo, min(hi, value))


def safe_float(value: object, default: float = 0.0) -> float:
    """Convert *value* to float; return *default* on failure."""
    if value is None:
        return default
    try:
        result = float(value)
        return result if math.isfinite(result) else default
    except (TypeError, ValueError):
        return default


def safe_float_or_none(value: object) -> Optional[float]:
    """Convert *value* to float or return None on failure."""
    if value is None:
        return None
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


# ── Aggregation helpers ───────────────────────────────────────────────────────

def weighted_average(
    pairs: Sequence[Tuple[Optional[float], float]],
    neutral: float = 50.0,
    redistribute: bool = False,
) -> float:
    """
    Compute weighted average of (value, weight) pairs.

    If *redistribute* is False (default) unavailable values use *neutral*.
    If *redistribute* is True the weight of unavailable values is distributed
    among available ones.
    """
    if not pairs:
        return neutral

    if redistribute:
        available = [(v, w) for v, w in pairs if v is not None]
        if not available:
            return neutral
        total_w = sum(w for _, w in available)
        if total_w == 0:
            return neutral
        return sum(v * w for v, w in available) / total_w
    else:
        total_w = sum(w for _, w in pairs)
        if total_w == 0:
            return neutral
        total = sum(
            (safe_float(v, neutral) * w if v is not None else neutral * w)
            for v, w in pairs
        )
        return total / total_w


def safe_average(
    values: Sequence[Optional[float]],
    default: float = 50.0,
) -> float:
    """Average of available (non-None) values; *default* if all missing."""
    valid = [safe_float(v) for v in values if v is not None]
    return statistics.mean(valid) if valid else default


def score_to_label(score: float) -> str:
    """Generic 0-100 score → label."""
    if score >= 80:
        return "excellent"
    if score >= 65:
        return "good"
    if score >= 50:
        return "moderate"
    if score >= 35:
        return "weak"
    return "poor"


def score_divergence(a: float, b: float) -> float:
    """Absolute divergence between two 0-100 scores."""
    return abs(a - b)


# ── Quality helpers ───────────────────────────────────────────────────────────

def compute_completeness(
    available: int,
    total: int,
) -> float:
    """Fraction of engines providing data (0-1)."""
    if total <= 0:
        return 0.0
    return clamp(available / total, 0.0, 1.0)


def compute_freshness(
    ages_seconds: Sequence[float],
    stale_warn: float = 3_600.0,
    stale_crit: float = 86_400.0,
) -> float:
    """
    0-1 freshness score from a collection of data-age values (seconds).
    Perfect freshness = 1.0; completely stale = 0.0.
    """
    if not ages_seconds:
        return 0.0
    scores = []
    for age in ages_seconds:
        if age <= stale_warn:
            scores.append(1.0)
        elif age <= stale_crit:
            # Linear decay between warn and crit
            scores.append(1.0 - (age - stale_warn) / (stale_crit - stale_warn) * 0.5)
        else:
            # Beyond critical: rapid decay, floor at 0.05
            over = (age - stale_crit) / stale_crit
            scores.append(max(0.05, 0.5 - over * 0.4))
    return statistics.mean(scores)


def compute_consistency(
    passed: int,
    total_checks: int,
    critical_failures: int = 0,
) -> float:
    """
    0-1 consistency score.
    Critical failures penalise heavily.
    """
    if total_checks <= 0:
        return 1.0
    base = passed / total_checks
    crit_penalty = min(0.40, critical_failures * 0.15)
    return clamp(base - crit_penalty, 0.0, 1.0)


def compute_reliability(
    conflict_count: int,
    critical_conflicts: int,
    completeness: float,
) -> float:
    """0-1 reliability based on conflicts and coverage."""
    base = completeness
    conflict_penalty = min(0.35, conflict_count * 0.05)
    crit_penalty = min(0.25, critical_conflicts * 0.15)
    return clamp(base - conflict_penalty - crit_penalty, 0.0, 1.0)


def composite_quality_score(
    completeness: float,
    consistency: float,
    freshness: float,
    reliability: float,
) -> float:
    """0-100 composite quality from 0-1 dimensions."""
    raw = (
        completeness  * 0.35
        + consistency * 0.30
        + freshness   * 0.20
        + reliability * 0.15
    ) * 100.0
    return round(clamp(raw), 1)


def stdev_or_zero(values: Sequence[float]) -> float:
    """Population std-dev; 0 if fewer than 2 values."""
    valid = [v for v in values if math.isfinite(v)]
    if len(valid) < 2:
        return 0.0
    return statistics.pstdev(valid)
