"""iios/investment/company/governance/management_score.py
Management Intelligence Score computation.
"""
from __future__ import annotations

from typing import List

from iios.investment.company.governance.management_profile import ManagementIntelligenceScore
from iios.investment.company.governance.management_statistics import clamp


_WEIGHTS = {
    "management_quality": 0.30,
    "governance":         0.25,
    "capital_allocation": 0.25,
    "transparency":       0.20,
}


def _label(score: float) -> str:
    if score >= 80:
        return "exceptional"
    if score >= 65:
        return "strong"
    if score >= 45:
        return "adequate"
    if score >= 25:
        return "weak"
    return "poor"


def compute_management_score(
    management_quality_score: float = 0.0,
    governance_score:         float = 0.0,
    capital_allocation_score: float = 0.0,
    transparency_score:       float = 0.0,
    governance_risk_score:    float = 0.0,
) -> ManagementIntelligenceScore:
    """
    Compute the composite Management Intelligence Score (0-100).
    Governance risk reduces the final score proportionally.
    """
    explanation: List[str] = []

    # Weighted base score
    base = (
        management_quality_score * _WEIGHTS["management_quality"]
        + governance_score       * _WEIGHTS["governance"]
        + capital_allocation_score * _WEIGHTS["capital_allocation"]
        + transparency_score     * _WEIGHTS["transparency"]
    )
    base = clamp(base, 0, 100)

    # Risk penalty: high governance risk can reduce score by up to 15 points
    risk_penalty = clamp(governance_risk_score / 100.0 * 15.0, 0, 15)
    overall = clamp(base - risk_penalty, 0, 100)
    label = _label(overall)

    explanation.append(
        f"Management quality: {management_quality_score:.1f} "
        f"| Governance: {governance_score:.1f} "
        f"| Capital allocation: {capital_allocation_score:.1f} "
        f"| Transparency: {transparency_score:.1f}"
    )
    if risk_penalty > 2:
        explanation.append(f"Governance risk penalty: -{risk_penalty:.1f} points")
    explanation.append(f"Overall: {overall:.1f}/100 ({label})")

    return ManagementIntelligenceScore(
        overall_score=round(overall, 1),
        management_quality_score=round(management_quality_score, 1),
        governance_score=round(governance_score, 1),
        capital_allocation_score=round(capital_allocation_score, 1),
        transparency_score=round(transparency_score, 1),
        risk_penalty=round(risk_penalty, 1),
        label=label,
        explanation=explanation,
    )
