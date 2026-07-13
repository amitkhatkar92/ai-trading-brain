"""iios/investment/company/governance/leadership_effectiveness.py
Leadership effectiveness scoring.
"""
from __future__ import annotations

from typing import List, Optional

from iios.investment.company.governance.management_statistics import (
    clamp, score_ceo_tenure, score_leadership_stability,
)


def score_execution_from_financials(
    earnings_stability_score: Optional[float],   # 0-100
    consistency_score:        Optional[float],   # 0-100 from EarningsQualityScore
    operational_quality_score: Optional[float],  # 0-100 from BusinessQualitySnapshot
    avg_roic:                 Optional[float],   # from EarningsSnapshot.profitability
) -> float:
    """
    Evaluate management execution quality from financial outcomes.
    Strong execution → consistent earnings + high ROIC + operational quality.
    """
    components = []

    if earnings_stability_score is not None:
        components.append(clamp(earnings_stability_score, 0, 100))
    if consistency_score is not None:
        components.append(clamp(consistency_score, 0, 100))
    if operational_quality_score is not None:
        components.append(clamp(operational_quality_score, 0, 100))
    if avg_roic is not None:
        roic_score = clamp(avg_roic / 0.25 * 100, 0, 100)
        components.append(roic_score)

    if not components:
        return 50.0   # neutral prior
    return sum(components) / len(components)


def score_strategic_consistency(
    moat_score:     Optional[float],   # 0-100 — moat maintenance signals strategic clarity
    growth_score:   Optional[float],   # 0-100 — growth consistency
    resilience_score: Optional[float], # 0-100 — through-cycle resilience
) -> float:
    """
    Strategic consistency — management consistently executes the stated strategy.
    Proxied by moat maintenance, growth sustainability, and resilience.
    """
    components = []
    if moat_score is not None:
        components.append(clamp(moat_score, 0, 100))
    if growth_score is not None:
        components.append(clamp(growth_score, 0, 100))
    if resilience_score is not None:
        components.append(clamp(resilience_score, 0, 100))
    if not components:
        return 50.0
    return sum(components) / len(components)


def score_long_term_orientation(
    avg_roic:                Optional[float],   # sustained ROIC = LT orientation
    earnings_stability:      Optional[float],   # 0-100
    sustainability_score:    Optional[float],   # 0-100 from GrowthSnapshot
    is_founder_led:          bool = False,
) -> float:
    """
    Long-term orientation — management prioritises sustainable compounding.
    Founder-led companies tend to have stronger LT orientation.
    """
    base = 50.0

    if avg_roic is not None:
        base = clamp(avg_roic / 0.20 * 60, 0, 60) + 20.0
    if earnings_stability is not None:
        base += (earnings_stability - 50) * 0.20
    if sustainability_score is not None:
        base += (sustainability_score - 50) * 0.10
    if is_founder_led:
        base += 8.0   # founder premium (empirically, founder-led companies often LT oriented)

    return clamp(base, 0, 100)


def score_management_credibility(
    earnings_quality_score: Optional[float],   # 0-100 — no manipulation signal
    avg_ocf_to_ni:          Optional[float],   # >1.0 = high credibility
    restatement_count:      int = 0,
    governance_incidents:   int = 0,
) -> float:
    """
    Management credibility — accounting integrity + no governance scandals.
    """
    base = 70.0

    if earnings_quality_score is not None:
        base = clamp(earnings_quality_score, 0, 100)
    if avg_ocf_to_ni is not None:
        if avg_ocf_to_ni >= 1.0:
            base = min(base + 10.0, 100.0)
        elif avg_ocf_to_ni < 0.7:
            base -= 15.0

    base -= restatement_count * 20.0
    base -= governance_incidents * 15.0

    return clamp(base, 0, 100)
