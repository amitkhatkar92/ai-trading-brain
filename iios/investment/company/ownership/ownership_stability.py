"""iios/investment/company/ownership/ownership_stability.py
Ownership stability and conviction analysis.
"""
from __future__ import annotations

from typing import Optional

from iios.investment.company.ownership.ownership_profile import PromoterStabilityLabel
from iios.investment.company.ownership.ownership_statistics import (
    clamp, score_promoter_stability, score_institutional_change, pct_to_100,
)


def classify_promoter_stability(
    promoter_pct:    Optional[float],
    change_3m:       Optional[float],
    change_1y:       Optional[float],
    pledge_pct:      Optional[float],
) -> PromoterStabilityLabel:
    """Classify promoter stability into a qualitative label."""
    # High pledge → concerning regardless of holding size
    if pledge_pct is not None and pct_to_100(pledge_pct) is not None:
        pp = pct_to_100(pledge_pct) or 0.0
        if pp >= 50:
            return PromoterStabilityLabel.CONCERNING

    if change_3m is None and change_1y is None:
        return PromoterStabilityLabel.UNKNOWN

    # Compute combined trend signal
    trend_score = score_promoter_stability(change_3m, change_1y)

    # Adjust for absolute holding level
    pct_adj = 0.0
    if promoter_pct is not None:
        pp = pct_to_100(promoter_pct) or 0.0
        if pp >= 50:
            pct_adj = 10.0
        elif pp >= 40:
            pct_adj = 5.0
        elif pp < 20:
            pct_adj = -10.0

    total = trend_score + pct_adj
    if total >= 85:
        return PromoterStabilityLabel.STRONG
    if total >= 65:
        return PromoterStabilityLabel.STABLE
    if total >= 45:
        return PromoterStabilityLabel.NEUTRAL
    if total >= 25:
        return PromoterStabilityLabel.DECLINING
    return PromoterStabilityLabel.CONCERNING


def score_ownership_stability(
    promoter_pct:    Optional[float],
    change_3m:       Optional[float],
    change_1y:       Optional[float],
    inst_change_3m:  Optional[float],
    pledge_pct:      Optional[float],
) -> float:
    """
    Overall ownership stability score (0-100; higher = more stable).
    Combines promoter stability, institutional direction, and pledge risk.
    """
    components: list[float] = []

    # Promoter stability signal (weight 50%)
    promoter_stability = score_promoter_stability(change_3m, change_1y)
    components.append(promoter_stability * 0.50)

    # Institutional direction signal (weight 30%)
    inst_stability = score_institutional_change(inst_change_3m)
    components.append(inst_stability * 0.30)

    # Pledge risk (weight 20%) — lower pledge → higher stability
    if pledge_pct is not None:
        pp = pct_to_100(pledge_pct) or 0.0
        # Convert pledge risk (higher = worse) to stability contribution
        pledge_stability = clamp(100.0 - pp * 1.2)
    else:
        pledge_stability = 75.0
    components.append(pledge_stability * 0.20)

    return clamp(sum(components))


def score_promoter_conviction(
    promoter_pct:   Optional[float],
    pledge_pct:     Optional[float],
    change_1y:      Optional[float],
) -> float:
    """
    Promoter conviction score: alignment without excess leverage.
    High holding + low pledge + stable/increasing = high conviction.
    """
    from iios.investment.company.ownership.ownership_statistics import score_promoter_holding
    hold_score   = score_promoter_holding(promoter_pct)
    pledge_adj   = 0.0
    if pledge_pct is not None:
        pp = pct_to_100(pledge_pct) or 0.0
        pledge_adj = -min(40.0, pp * 0.6)   # pledge deducts up to 40 points

    trend_adj = 0.0
    if change_1y is not None:
        if change_1y >= 2.0:
            trend_adj = 10.0
        elif change_1y >= 0.0:
            trend_adj = 3.0
        elif change_1y >= -2.0:
            trend_adj = -5.0
        else:
            trend_adj = -15.0

    return clamp(hold_score + pledge_adj + trend_adj)
