"""
production_readiness/ph8_learning_impact.py — Phase 8: Learning Impact.

Reuses the ILC verification engine to measure and summarise whether
past learning actions have produced measurable system improvements.

No new storage or logic — pure wrapper over ilc_verification.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from .prr_models import LearningImpactSummary

log = logging.getLogger(__name__)


def get_learning_impact_summary(
    today: Optional[str] = None,
) -> LearningImpactSummary:
    """
    Load the ILC learning registry and summarise impact across all records.
    """
    today = today or datetime.now().date().isoformat()

    try:
        from institutional_learning.ilc_verification import get_all_records
        records = get_all_records()
    except Exception as e:
        log.warning("[LearningImpact] Cannot load ILC records: %s", e)
        return LearningImpactSummary(
            date=today,
            total_actions=0,
            pending_verification=0,
            under_verification=0,
            improved=0,
            no_change=0,
            declined=0,
            retired=0,
            avg_improvement_pct=0.0,
            roi_positive_pct=0.0,
        )

    pending    = sum(1 for r in records if getattr(r, "status", "") == "PENDING")
    verifying  = sum(1 for r in records if getattr(r, "status", "") in ("30D", "60D", "90D"))
    improved   = sum(1 for r in records if getattr(r, "last_verdict", "") == "IMPROVED")
    no_change  = sum(1 for r in records if getattr(r, "last_verdict", "") == "NO_CHANGE")
    declined   = sum(1 for r in records if getattr(r, "last_verdict", "") == "DECLINED")
    retired    = sum(1 for r in records if getattr(r, "status", "") == "RETIRED")

    # Average improvement from verified/improved records
    improvement_vals = []
    for r in records:
        if getattr(r, "last_verdict", "") == "IMPROVED":
            pre  = getattr(r, "baseline_metric", 0.0) or 0.0
            post = getattr(r, "latest_metric", 0.0) or 0.0
            if pre > 0:
                improvement_vals.append(100.0 * (post - pre) / pre)

    avg_improvement = round(
        sum(improvement_vals) / len(improvement_vals) if improvement_vals else 0.0, 1
    )

    # ROI positive = improved / (improved + declined) among verified
    verified_total = improved + declined
    roi_positive   = round(100.0 * improved / max(verified_total, 1), 1)

    # Top improved: action names sorted by improvement magnitude
    top_improved  = []
    top_declined  = []
    for r in records:
        name = getattr(r, "action_name", "") or str(getattr(r, "action_id", ""))
        pre  = getattr(r, "baseline_metric", 0.0) or 0.0
        post = getattr(r, "latest_metric", 0.0) or 0.0
        if getattr(r, "last_verdict", "") == "IMPROVED" and pre > 0:
            pct = 100.0 * (post - pre) / pre
            top_improved.append((pct, name))
        elif getattr(r, "last_verdict", "") == "DECLINED" and pre > 0:
            pct = 100.0 * (post - pre) / pre
            top_declined.append((pct, name))

    top_improved.sort(reverse=True)
    top_declined.sort()

    log.info(
        "[LearningImpact] total=%d pending=%d improved=%d declined=%d avg_improvement=%.1f%%",
        len(records), pending, improved, declined, avg_improvement,
    )

    return LearningImpactSummary(
        date=today,
        total_actions=len(records),
        pending_verification=pending,
        under_verification=verifying,
        improved=improved,
        no_change=no_change,
        declined=declined,
        retired=retired,
        avg_improvement_pct=avg_improvement,
        roi_positive_pct=roi_positive,
        top_improved=[n for _, n in top_improved[:5]],
        top_declined=[n for _, n in top_declined[:5]],
    )
