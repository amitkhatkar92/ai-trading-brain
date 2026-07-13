"""iios/investment/company/ownership/ownership_quality.py
Ownership quality composite score.
"""
from __future__ import annotations

from typing import Optional

from iios.investment.company.ownership.ownership_statistics import clamp


def compute_ownership_quality_score(
    promoter_stability_score:    float,
    institutional_quality_score: float,
    insider_alignment_score:     float,
    distribution_quality_score:  float,
) -> float:
    """
    Composite ownership quality score (0-100).
    Reflects structural quality of the ownership base.
    """
    return clamp(
        promoter_stability_score    * 0.35
        + institutional_quality_score * 0.30
        + insider_alignment_score     * 0.20
        + distribution_quality_score  * 0.15
    )
