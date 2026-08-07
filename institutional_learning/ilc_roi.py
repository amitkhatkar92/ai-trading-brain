"""institutional_learning/ilc_roi.py — Phase 9: Learning ROI Calculation."""
from __future__ import annotations

import logging
from typing import List

from .ilc_config import TARGET_COST
from .ilc_models import LearningRecord, ROIRecord

log = logging.getLogger(__name__)

# Expected improvement gain per verdict (as % of baseline)
_VERDICT_IMPROVEMENT = {
    "IMPROVED":   0.10,   # +10% assumed
    "NO_CHANGE":  0.00,
    "DECLINED":  -0.05,
}

# Research hours equivalent per target system (cost proxy)
_RESEARCH_HOURS = {
    "CALIBRATION": 1.0,
    "IDR":         2.0,
    "HYPOTHESIS":  1.5,
    "RC":          4.0,
    "HKAP":        3.0,
    "KDE":         3.0,
    "SD":          2.5,
}


def compute_roi(record: LearningRecord) -> ROIRecord:
    """
    Compute ROI for a single learning record.

    ROI = (observed_improvement - implementation_cost) / implementation_cost
    Where:
        implementation_cost = normalised cost (TARGET_COST map)
        observed_improvement = sum of change_pct across verified windows / n_windows
    """
    impl_cost = TARGET_COST.get(record.target_system, 0.30)

    if not record.verification_results:
        # No verification yet — use EIG as expected benefit proxy
        observed = record.eig_score * 0.5   # conservative estimate
    else:
        changes   = [vr.change_pct for vr in record.verification_results]
        observed  = sum(changes) / len(changes)

    if impl_cost > 0:
        roi_score = (observed - impl_cost) / impl_cost
    else:
        roi_score = observed

    return ROIRecord(
        learning_id=record.learning_id,
        symbol=record.symbol,
        category=record.category,
        target_system=record.target_system,
        implementation_cost=round(impl_cost, 3),
        observed_improvement=round(observed, 4),
        roi_score=round(roi_score, 3),
        confidence=record.confidence,
    )


def compute_all_roi(records: List[LearningRecord]) -> List[ROIRecord]:
    """Compute ROI for all records and return sorted by roi_score descending."""
    rois = [compute_roi(r) for r in records if r.status != "PENDING"]
    rois.sort(key=lambda r: r.roi_score, reverse=True)

    if rois:
        positive    = sum(1 for r in rois if r.roi_score > 0)
        avg_roi     = sum(r.roi_score for r in rois) / len(rois)
        pos_pct     = 100 * positive / len(rois)
        log.info(
            "[ILC] Phase 9 ROI: records=%d positive=%d(%.0f%%) avg_roi=%.3f",
            len(rois), positive, pos_pct, avg_roi,
        )

    return rois
