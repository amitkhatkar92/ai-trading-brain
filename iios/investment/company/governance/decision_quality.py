"""iios/investment/company/governance/decision_quality.py
Decision quality assessment — evaluates quality of management decisions
using financial outcomes as signals.
"""
from __future__ import annotations

from typing import List, Optional

from iios.investment.company.governance.management_statistics import (
    clamp, score_roic, score_debt_level, score_payout_ratio,
)


def score_decision_quality(
    avg_roic:          Optional[float] = None,   # capital allocation decisions
    debt_to_equity:    Optional[float] = None,   # leverage decisions
    payout_ratio:      Optional[float] = None,   # distribution decisions
    eps_cagr:          Optional[float] = None,   # growth execution
    sustainability_score: Optional[float] = None, # 0-100 from GrowthSnapshot
    is_cyclical:       Optional[bool] = None,
) -> float:
    """
    Composite decision quality score (0-100).
    High-quality decisions: high ROIC, appropriate leverage, balanced payout,
    and sustainable growth.
    """
    components = []

    # Capital allocation decisions
    roic_score = score_roic(avg_roic)
    if avg_roic is not None:
        components.append(roic_score)

    # Leverage decisions
    debt_score = score_debt_level(debt_to_equity)
    if debt_to_equity is not None:
        components.append(debt_score)

    # Distribution decisions
    payout_score = score_payout_ratio(payout_ratio)
    if payout_ratio is not None:
        components.append(payout_score)

    # Growth execution
    if eps_cagr is not None:
        growth_score = clamp(eps_cagr / 0.25 * 100, 0, 100) if eps_cagr >= 0 else 0.0
        components.append(growth_score)

    # Sustainability of growth decisions
    if sustainability_score is not None:
        components.append(clamp(sustainability_score, 0, 100))

    if not components:
        return 50.0
    return sum(components) / len(components)
