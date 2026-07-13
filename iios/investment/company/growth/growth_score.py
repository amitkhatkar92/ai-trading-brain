"""iios/investment/company/growth/growth_score.py
Growth Intelligence Score computation (0-100, with label).
"""
from __future__ import annotations

from typing import List, Optional

from iios.investment.company.growth.growth_profile import GrowthIntelligenceScore
from iios.investment.company.growth.growth_statistics import clamp, score_from_cagr


_WEIGHTS = {
    "revenue_growth":    0.28,
    "profit_growth":     0.28,
    "cashflow_growth":   0.18,
    "sustainability":    0.18,
    "forecast_confidence": 0.08,
}


def _label(score: float) -> str:
    if score >= 80:
        return "exceptional"
    if score >= 65:
        return "strong"
    if score >= 45:
        return "moderate"
    if score >= 25:
        return "weak"
    if score > 0:
        return "poor"
    return "insufficient"


def compute_growth_score(
    revenue_cagr:      Optional[float] = None,
    eps_cagr:          Optional[float] = None,
    ni_cagr:           Optional[float] = None,
    fcf_cagr:          Optional[float] = None,
    sustainability:    float = 0.0,
    forecast_confidence: float = 0.0,
) -> GrowthIntelligenceScore:
    """
    Compute a composite Growth Intelligence Score (0-100).
    """
    explanation: List[str] = []

    # ── Component scores ─────────────────────────────────────────────────────────
    rev_score = score_from_cagr(revenue_cagr)
    eps_score = score_from_cagr(eps_cagr)
    ni_score  = score_from_cagr(ni_cagr)
    fcf_score = score_from_cagr(fcf_cagr)

    # Blend EPS + NI for profit growth score
    if eps_cagr is not None and ni_cagr is not None:
        profit_score = (eps_score + ni_score) / 2.0
    elif eps_cagr is not None:
        profit_score = eps_score
    elif ni_cagr is not None:
        profit_score = ni_score
    else:
        profit_score = 0.0

    cashflow_score = fcf_score
    sus_score      = clamp(sustainability, 0, 100)
    fc_score       = clamp(forecast_confidence * 100.0, 0, 100)

    # ── Weighted composite ────────────────────────────────────────────────────────
    overall = (
        rev_score       * _WEIGHTS["revenue_growth"]
        + profit_score  * _WEIGHTS["profit_growth"]
        + cashflow_score * _WEIGHTS["cashflow_growth"]
        + sus_score     * _WEIGHTS["sustainability"]
        + fc_score      * _WEIGHTS["forecast_confidence"]
    )

    overall = clamp(overall, 0.0, 100.0)
    label   = _label(overall)

    # ── Explanations ────────────────────────────────────────────────────────────
    if revenue_cagr is not None:
        explanation.append(f"Revenue CAGR {revenue_cagr:.1%} → score {rev_score:.1f}")
    if eps_cagr is not None:
        explanation.append(f"EPS CAGR {eps_cagr:.1%} → score {eps_score:.1f}")
    if fcf_cagr is not None:
        explanation.append(f"FCF CAGR {fcf_cagr:.1%} → score {fcf_score:.1f}")
    explanation.append(f"Sustainability {sustainability:.1f}/100 → score {sus_score:.1f}")
    explanation.append(f"Overall: {overall:.1f}/100 ({label})")

    return GrowthIntelligenceScore(
        overall_score=round(overall, 1),
        revenue_growth_score=round(rev_score, 1),
        profit_growth_score=round(profit_score, 1),
        cashflow_growth_score=round(cashflow_score, 1),
        sustainability_score=round(sus_score, 1),
        forecast_confidence_score=round(fc_score, 1),
        label=label,
        explanation=explanation,
    )
