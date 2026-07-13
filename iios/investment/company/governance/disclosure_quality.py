"""iios/investment/company/governance/disclosure_quality.py
Disclosure and reporting quality scoring.
"""
from __future__ import annotations

from typing import Optional

from iios.investment.company.governance.management_statistics import (
    clamp, score_accruals, score_ocf_to_ni,
)


def score_disclosure_quality(
    earnings_quality_score: Optional[float] = None,   # 0-100
    consistency_score:      Optional[float] = None,   # 0-100
    restatement_count:      int = 0,
) -> float:
    """
    Score disclosure quality.
    High earnings quality + consistent reporting + no restatements = excellent disclosure.
    """
    base = 65.0

    if earnings_quality_score is not None:
        base = clamp(earnings_quality_score, 0, 100)
    if consistency_score is not None:
        base = (base + clamp(consistency_score, 0, 100)) / 2.0

    base -= restatement_count * 20.0
    return clamp(base, 0, 100)


def score_reporting_transparency(
    avg_accruals_ratio: Optional[float] = None,
    avg_ocf_to_ni:      Optional[float] = None,
) -> float:
    """
    Score reporting transparency from accounting quality metrics.
    Lower accruals + higher OCF/NI = more transparent reporting.
    """
    components = []
    if avg_accruals_ratio is not None:
        components.append(score_accruals(avg_accruals_ratio))
    if avg_ocf_to_ni is not None:
        components.append(score_ocf_to_ni(avg_ocf_to_ni))

    return sum(components) / len(components) if components else 50.0
