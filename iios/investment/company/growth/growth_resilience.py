"""iios/investment/company/growth/growth_resilience.py
Growth resilience scoring.
Resilience measures ability to sustain growth through adverse conditions.
"""
from __future__ import annotations

from typing import Optional

from iios.investment.company.growth.growth_statistics import clamp


def compute_resilience_score(
    resilience_score:     Optional[float] = None,  # 0-100, from BusinessQualitySnapshot
    is_cyclical:          Optional[bool]  = None,
    loss_rate:            Optional[float] = None,  # 0-1
    avg_fcf_margin:       Optional[float] = None,  # > 0 = FCF positive
    earnings_stability:   Optional[float] = None,  # 0-100 from EarningsSnapshot.risk
    moat_score:           Optional[float] = None,  # 0-100
) -> float:
    """
    Compute a 0-100 growth resilience score.
    Higher = growth likely to persist through market stress.
    """
    if resilience_score is not None:
        base = float(resilience_score)
    else:
        base = 50.0   # neutral prior

    adjustments = 0.0

    # Cyclicality reduces resilience of growth
    if is_cyclical is True:
        adjustments -= 15.0

    # Loss rate reduces resilience
    if loss_rate is not None:
        adjustments -= clamp(loss_rate * 40.0, 0, 20)

    # Positive FCF margin supports resilience
    if avg_fcf_margin is not None:
        if avg_fcf_margin > 0.10:
            adjustments += 10.0
        elif avg_fcf_margin > 0.0:
            adjustments += 5.0
        else:
            adjustments -= 10.0  # FCF-negative business

    # Earnings stability
    if earnings_stability is not None:
        adjustments += clamp((earnings_stability - 50.0) * 0.2, -10, 10)

    # Moat reinforces resilience
    if moat_score is not None:
        adjustments += clamp((moat_score - 50.0) * 0.1, -5, 10)

    return clamp(base + adjustments, 0.0, 100.0)
