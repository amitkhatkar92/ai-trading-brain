"""iios/investment/company/integration/quality_statistics.py
Pure statistical helpers for quality dimension computation. No external dependencies.
"""
from __future__ import annotations

import math
import statistics
from typing import List, Optional, Sequence

from iios.investment.company.integration.company_statistics import (
    clamp, composite_quality_score, compute_consistency, compute_freshness,
    compute_reliability, safe_float,
)
from iios.investment.company.integration.company_state import (
    STALE_WARN_SECONDS, STALE_CRIT_SECONDS,
)


def quality_grade(score: float) -> str:
    """0-100 quality score → A/B/C/D/F grade."""
    if score >= 88:
        return "A"
    if score >= 75:
        return "B"
    if score >= 60:
        return "C"
    if score >= 45:
        return "D"
    return "F"


def coverage_score(available: int, total: int) -> float:
    """0-1 data coverage — fraction of intelligence dimensions available."""
    if total <= 0:
        return 0.0
    return clamp(available / total, 0.0, 1.0)


def freshness_from_ages(ages: Sequence[float]) -> float:
    """0-1 freshness from a list of data-age values in seconds."""
    return compute_freshness(ages, STALE_WARN_SECONDS, STALE_CRIT_SECONDS)


def consistency_from_checks(
    passed: int, total: int, critical_failures: int = 0
) -> float:
    return compute_consistency(passed, total, critical_failures)


def reliability_from_conflicts(
    conflict_count: int,
    critical_conflicts: int,
    completeness: float,
) -> float:
    return compute_reliability(conflict_count, critical_conflicts, completeness)


def overall_quality(
    completeness: float,
    consistency: float,
    freshness: float,
    reliability: float,
) -> float:
    """0-100 composite quality score."""
    return composite_quality_score(completeness, consistency, freshness, reliability)


def score_volatility(history: Sequence[float]) -> float:
    """Population std-dev of historical overall scores — used for confidence penalty."""
    vals = [safe_float(v) for v in history if v is not None]
    if len(vals) < 2:
        return 0.0
    return statistics.pstdev(vals)


def confidence_from_quality(
    completeness: float,
    consistency: float,
    freshness: float,
    score_stdev: float = 0.0,
    n_evaluations: int = 1,
) -> float:
    """
    0-1 confidence score.

    Factors:
    - completeness:  how many engines provided data
    - consistency:   fraction of validation checks passed
    - freshness:     how recent the data is
    - score stdev:   penalise volatile/unstable intelligence
    - n_evaluations: first evaluation is less reliable than repeated ones
    """
    base = (
        completeness  * 0.40
        + consistency * 0.30
        + freshness   * 0.20
    )
    # Stability bonus (max +0.10)
    stability = max(0.0, 1.0 - score_stdev / 25.0) * 0.10
    # Evaluation depth bonus: saturates after 5 evaluations
    depth = min(n_evaluations / 5.0, 1.0) * 0.05 * completeness
    raw = base + stability + depth
    return round(clamp(raw, 0.0, 1.0), 4)
