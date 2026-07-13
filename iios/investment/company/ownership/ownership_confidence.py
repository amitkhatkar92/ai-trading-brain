"""iios/investment/company/ownership/ownership_confidence.py
Ownership intelligence confidence estimation.
"""
from __future__ import annotations

from iios.investment.company.ownership.ownership_statistics import clamp


def compute_ownership_confidence(
    has_ownership_data:   bool,
    has_insider_data:     bool,
    has_financial_data:   bool,
    has_promoter_data:    bool,
    has_institutional_data: bool,
    has_management_data:  bool,
    history_depth:        int = 0,
    ownership_standard:   str = "generic",
) -> float:
    """
    Estimate confidence in the ownership intelligence snapshot (0-1).
    Higher confidence = more complete input data.
    """
    score = 0.0

    # Core data availability
    if has_financial_data:
        score += 0.20
    if has_ownership_data:
        score += 0.25
    if has_promoter_data:
        score += 0.15
    if has_institutional_data:
        score += 0.10
    if has_insider_data:
        score += 0.15
    if has_management_data:
        score += 0.10

    # History depth bonus
    if history_depth >= 8:
        score += 0.05
    elif history_depth >= 4:
        score += 0.03
    elif history_depth >= 2:
        score += 0.01

    # Known-standard bonus
    if ownership_standard in ("sebi", "sec", "fca", "asx"):
        score += 0.01   # known regulatory framework = marginally higher confidence

    return clamp(score, 0.0, 1.0)
