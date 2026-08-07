"""institutional_learning/ilc_score.py — Phase 11: Institutional Learning Score (ILS 0-100)."""
from __future__ import annotations

import logging
from typing import List, Optional

from .ilc_config import SCORE_WEIGHTS
from .ilc_models import ILSScore, LearningConfidence, LearningRecord, LifecycleRecord, ROIRecord

log = logging.getLogger(__name__)

# Grade thresholds
_GRADES = [
    (90, "A+", "Exceptional"),
    (80, "A",  "Strong"),
    (70, "B",  "Good"),
    (60, "C",  "Adequate"),
    (50, "D",  "Below Average"),
    (0,  "F",  "Poor — Needs Intervention"),
]


def _learning_efficiency(records: List[LearningRecord]) -> float:
    """
    Fraction of HIGH/MEDIUM confidence records vs total.
    Higher = more actionable learnings per cycle.
    """
    if not records:
        return 0.0
    high_med = sum(
        1 for r in records
        if r.confidence in (LearningConfidence.HIGH, LearningConfidence.MEDIUM)
    )
    return high_med / len(records)


def _knowledge_efficiency(lifecycle_records: List[LifecycleRecord]) -> float:
    """
    Fraction of total knowledge items that are PROMOTED or VALIDATED.
    Measures the health of the overall knowledge base.
    """
    if not lifecycle_records:
        return 0.5   # neutral baseline when no data
    active = sum(
        1 for r in lifecycle_records
        if r.current_status in ("PROMOTED", "VALIDATED", "ACTIVE")
    )
    return active / len(lifecycle_records)


def _prediction_improvement(records: List[LearningRecord]) -> float:
    """
    Fraction of verified records that show IMPROVED verdict at any window.
    """
    verified = [r for r in records if r.verification_results]
    if not verified:
        return 0.5   # neutral when nothing verified yet
    improved = sum(
        1 for r in verified
        if any(vr.verdict == "IMPROVED" for vr in r.verification_results)
    )
    return improved / len(verified)


def _research_productivity(
    records: List[LearningRecord],
    gva_score: float,
) -> float:
    """
    Combined measure of learning volume and GVA research health.
    - record_score: normalised by 20 (ILC_TOP_N) records expected per day
    - gva_score: already 0-100, normalise to 0-1
    """
    record_score = min(len(records) / 20.0, 1.0)
    gva_norm     = gva_score / 100.0
    return (record_score * 0.4) + (gva_norm * 0.6)


def _knowledge_roi(roi_records: List[ROIRecord]) -> float:
    """
    Fraction of ROI records with positive ROI.
    Capped at 1.0.
    """
    if not roi_records:
        return 0.5   # neutral
    positive = sum(1 for r in roi_records if r.roi_score > 0)
    return positive / len(roi_records)


def _grade(score: float) -> tuple[str, str]:
    """Return (letter, label) for a score 0-100."""
    for threshold, letter, label in _GRADES:
        if score >= threshold:
            return letter, label
    return "F", "Poor"


def compute_ils_score(
    learning_records: List[LearningRecord],
    verified_results: list,
    lifecycle_records: List[LifecycleRecord],
    roi_records: List[ROIRecord],
    gva_score: float = 50.0,
) -> ILSScore:
    """
    Compute the Institutional Learning Score (ILS) as a weighted composite.

    Components (defined in SCORE_WEIGHTS config):
      - learning_efficiency:    HIGH/MEDIUM ratio
      - knowledge_efficiency:   PROMOTED/VALIDATED ratio in lifecycle
      - prediction_improvement: verified improvement rate
      - research_productivity:  volume * GVA score
      - knowledge_roi:          fraction with positive ROI

    All components are 0-1 before weighting.
    Final score = weighted_sum * 100, clamped to [0, 100].
    """
    le  = _learning_efficiency(learning_records)
    ke  = _knowledge_efficiency(lifecycle_records)
    pi  = _prediction_improvement(learning_records)
    rp  = _research_productivity(learning_records, gva_score)
    roi = _knowledge_roi(roi_records)

    weights = SCORE_WEIGHTS
    raw = (
        weights["learning_efficiency"]    * le
        + weights["knowledge_efficiency"]   * ke
        + weights["prediction_improvement"] * pi
        + weights["research_productivity"]  * rp
        + weights["knowledge_roi"]          * roi
    )

    score  = max(0.0, min(100.0, raw * 100))
    letter, label = _grade(score)

    ils = ILSScore(
        overall_score=round(score, 1),
        grade=letter,
        narrative=f"{label} — {len(learning_records)} actions, {len(verified_results)} verifications, GVA={gva_score:.0f}",
        learning_efficiency=round(le, 3),
        knowledge_efficiency=round(ke, 3),
        prediction_improvement=round(pi, 3),
        research_productivity=round(rp, 3),
        knowledge_roi=round(roi, 3),
    )

    log.info(
        "[ILC] Phase 11 ILS: %.1f/100 (%s %s) "
        "[le=%.2f ke=%.2f pi=%.2f rp=%.2f roi=%.2f]",
        ils.overall_score, ils.grade, label,
        le, ke, pi, rp, roi,
    )
    return ils
