"""
iios/intelligence/governance/evaluation/evaluation_metrics.py
=============================================================
Pure stateless metric functions for the governance evaluation layer.
No external dependencies; all inputs are basic Python types.
"""
from __future__ import annotations

from ..quality_constants import ApprovalStatus, CertificationStatus
from ..quality_result import QualityRecord


def approval_rate(records: list[QualityRecord]) -> float:
    """Fraction of records that have been approved."""
    if not records:
        return 0.0
    approved = sum(1 for r in records if r.approval_status == ApprovalStatus.APPROVED)
    return approved / len(records)


def rejection_rate(records: list[QualityRecord]) -> float:
    """Fraction of records that have been rejected."""
    if not records:
        return 0.0
    rejected = sum(1 for r in records if r.approval_status == ApprovalStatus.REJECTED)
    return rejected / len(records)


def certification_rate(records: list[QualityRecord]) -> float:
    """Fraction of records that are certified."""
    if not records:
        return 0.0
    certified = sum(
        1 for r in records
        if r.certification_status == CertificationStatus.CERTIFIED
    )
    return certified / len(records)


def avg_quality_score(records: list[QualityRecord]) -> float:
    """Mean quality score across all records."""
    if not records:
        return 0.0
    return sum(r.quality_score for r in records) / len(records)


def min_quality_score(records: list[QualityRecord]) -> float:
    if not records:
        return 0.0
    return min(r.quality_score for r in records)


def max_quality_score(records: list[QualityRecord]) -> float:
    if not records:
        return 0.0
    return max(r.quality_score for r in records)


def consistency_rate(records: list[QualityRecord]) -> float:
    """
    Fraction of records whose quality level is consistent with their score.
    A record is consistent if quality_level matches the level implied by its score.
    """
    from ..quality_constants import (
        QUALITY_SCORE_EXCELLENT,
        QUALITY_SCORE_GOOD,
        QUALITY_SCORE_ACCEPTABLE,
        QualityLevel,
    )
    if not records:
        return 0.0

    def _expected(score: float) -> QualityLevel:
        if score >= QUALITY_SCORE_EXCELLENT:
            return QualityLevel.EXCELLENT
        if score >= QUALITY_SCORE_GOOD:
            return QualityLevel.GOOD
        if score >= QUALITY_SCORE_ACCEPTABLE:
            return QualityLevel.ACCEPTABLE
        if score >= 0.40:
            return QualityLevel.POOR
        return QualityLevel.REJECTED

    consistent = sum(1 for r in records if r.quality_level == _expected(r.quality_score))
    return consistent / len(records)


def drift_score(baseline_scores: list[float], current_scores: list[float]) -> float:
    """
    Measure of distributional drift between two sets of quality scores.
    Returns the absolute difference of means (0.0 = no drift).
    """
    if not baseline_scores or not current_scores:
        return 0.0
    base_mean    = sum(baseline_scores) / len(baseline_scores)
    current_mean = sum(current_scores) / len(current_scores)
    return abs(base_mean - current_mean)


def warning_density(records: list[QualityRecord]) -> float:
    """Average number of warnings per record."""
    if not records:
        return 0.0
    return sum(len(r.warnings) for r in records) / len(records)
