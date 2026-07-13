"""iios/investment/company/ownership/ownership_score.py
Ownership Intelligence Score computation.
"""
from __future__ import annotations

from iios.investment.company.ownership.ownership_profile import (
    OwnershipIntelligenceScore, OwnershipQualityLabel,
)
from iios.investment.company.ownership.ownership_statistics import clamp


def _label(score: float) -> OwnershipQualityLabel:
    if score >= 80:
        return OwnershipQualityLabel.EXCEPTIONAL
    if score >= 65:
        return OwnershipQualityLabel.STRONG
    if score >= 50:
        return OwnershipQualityLabel.ADEQUATE
    if score >= 35:
        return OwnershipQualityLabel.WEAK
    if score >= 20:
        return OwnershipQualityLabel.POOR
    return OwnershipQualityLabel.INSUFFICIENT


# Composite weights
_WEIGHTS = {
    "ownership_quality":  0.30,
    "capital_allocation": 0.25,
    "shareholder_value":  0.25,
    "insider_alignment":  0.20,
}

_RISK_PENALTY_MAX = 15.0   # maximum score deduction for high ownership risk


def compute_ownership_score(
    ownership_quality_score:  float,
    capital_allocation_score: float,
    shareholder_value_score:  float,
    insider_alignment_score:  float,
    ownership_risk_score:     float,   # 0-100; higher = more risky
) -> OwnershipIntelligenceScore:
    """
    Compute composite Ownership Intelligence Score.
    Risk penalty is applied: higher ownership risk reduces overall score.
    """
    expl: list[str] = []

    composite = (
        ownership_quality_score   * _WEIGHTS["ownership_quality"]
        + capital_allocation_score  * _WEIGHTS["capital_allocation"]
        + shareholder_value_score   * _WEIGHTS["shareholder_value"]
        + insider_alignment_score   * _WEIGHTS["insider_alignment"]
    )

    # Risk penalty: scales from 0 (risk=0) to _RISK_PENALTY_MAX (risk=100)
    risk_penalty = (ownership_risk_score / 100.0) * _RISK_PENALTY_MAX
    final = clamp(composite - risk_penalty)

    if risk_penalty >= 10:
        expl.append(
            f"Score reduced by {risk_penalty:.1f}pts due to elevated ownership risk."
        )

    label = _label(final)
    return OwnershipIntelligenceScore(
        overall_score=round(final, 1),
        ownership_quality_score=round(ownership_quality_score, 1),
        capital_allocation_score=round(capital_allocation_score, 1),
        shareholder_value_score=round(shareholder_value_score, 1),
        insider_alignment_score=round(insider_alignment_score, 1),
        label=label,
        explanation=expl,
    )
