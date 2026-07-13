"""iios/investment/company/growth/growth_consistency.py
Growth consistency scoring.
Consistency measures how smooth and predictable growth is over time.
"""
from __future__ import annotations

from typing import List, Optional

from iios.investment.company.growth.growth_statistics import clamp


def compute_consistency_score(
    eps_volatility:     Optional[float] = None,   # CV from EarningsSnapshot.risk
    revenue_volatility: Optional[float] = None,   # CV
    margin_volatility:  Optional[float] = None,   # CV
    consistency_score:  Optional[float] = None,   # 0-100, from EarningsSnapshot.quality
    loss_rate:          Optional[float] = None,   # fraction of periods with losses
    history_depth:      int = 0,
) -> float:
    """
    Compute a 0-100 growth consistency score.
    Higher = more consistent and predictable growth.

    If EarningsSnapshot provides a consistency_score, we use it as the anchor
    and adjust using volatility and loss data.
    """
    if consistency_score is not None:
        base = float(consistency_score)
    else:
        base = 60.0   # neutral prior

    penalties = 0.0

    # Earnings volatility (CV) → high CV = inconsistent growth
    if eps_volatility is not None:
        if eps_volatility > 1.0:
            penalties += 30.0
        elif eps_volatility > 0.5:
            penalties += 15.0
        elif eps_volatility > 0.3:
            penalties += 7.0

    # Revenue volatility
    if revenue_volatility is not None:
        if revenue_volatility > 0.8:
            penalties += 15.0
        elif revenue_volatility > 0.4:
            penalties += 7.0

    # Margin volatility
    if margin_volatility is not None:
        if margin_volatility > 0.5:
            penalties += 10.0
        elif margin_volatility > 0.25:
            penalties += 5.0

    # Loss rate
    if loss_rate is not None:
        penalties += clamp(loss_rate * 50.0, 0, 25)

    # History depth bonus — more data = more confidence
    if history_depth >= 10:
        pass   # no penalty for sufficient history
    elif history_depth >= 5:
        penalties += 5.0
    else:
        penalties += 15.0  # thin history → reduce consistency confidence

    return clamp(base - penalties, 0.0, 100.0)
