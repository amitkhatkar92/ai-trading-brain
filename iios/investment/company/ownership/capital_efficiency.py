"""iios/investment/company/ownership/capital_efficiency.py
Capital efficiency metrics for the Ownership Intelligence Engine.
"""
from __future__ import annotations

from typing import Optional

from iios.investment.company.ownership.ownership_statistics import clamp, score_roic_spread


def score_asset_utilization(
    revenue:      Optional[float],
    total_assets: Optional[float],
) -> float:
    """
    Score asset utilization quality (revenue / assets).
    Asset-light businesses score high with lower ratio; capital-intensive lower.
    Optimal ratio depends on industry, so we use broad thresholds.
    """
    if revenue is None or total_assets is None or total_assets <= 0:
        return 50.0

    ratio = revenue / total_assets
    if ratio >= 1.5:
        return 95.0
    if ratio >= 1.0:
        return 80.0
    if ratio >= 0.6:
        return 65.0
    if ratio >= 0.3:
        return 50.0
    if ratio >= 0.1:
        return 35.0
    return 20.0


def score_invested_capital_productivity(
    fcf:          Optional[float],
    total_equity: Optional[float],
    total_debt:   Optional[float],
) -> float:
    """
    Score FCF / invested capital (a cash-based ROIC proxy).
    """
    if fcf is None or (total_equity is None and total_debt is None):
        return 50.0

    invested_capital = (total_equity or 0.0) + (total_debt or 0.0)
    if invested_capital <= 0:
        return 50.0

    ratio = fcf / invested_capital
    if ratio >= 0.20:
        return 100.0
    if ratio >= 0.12:
        return 80.0
    if ratio >= 0.07:
        return 65.0
    if ratio >= 0.03:
        return 45.0
    if ratio >= 0:
        return 25.0
    return 5.0   # negative FCF


def score_capital_efficiency_composite(
    avg_roic:     Optional[float],
    avg_roe:      Optional[float],
    fcf_margin:   Optional[float],
    revenue:      Optional[float] = None,
    total_assets: Optional[float] = None,
) -> float:
    """
    Composite capital efficiency score.
    """
    components: list[float] = []

    # ROIC economic spread
    components.append(score_roic_spread(avg_roic) * 0.40)

    # ROE signal
    if avg_roe is not None:
        if avg_roe >= 0.20:
            components.append(100.0 * 0.25)
        elif avg_roe >= 0.15:
            components.append(80.0 * 0.25)
        elif avg_roe >= 0.10:
            components.append(60.0 * 0.25)
        elif avg_roe >= 0.05:
            components.append(40.0 * 0.25)
        else:
            components.append(15.0 * 0.25)
    else:
        components.append(40.0 * 0.25)   # neutral

    # FCF margin
    if fcf_margin is not None:
        if fcf_margin >= 0.15:
            components.append(100.0 * 0.20)
        elif fcf_margin >= 0.10:
            components.append(80.0 * 0.20)
        elif fcf_margin >= 0.05:
            components.append(60.0 * 0.20)
        elif fcf_margin >= 0:
            components.append(35.0 * 0.20)
        else:
            components.append(0.0 * 0.20)
    else:
        components.append(40.0 * 0.20)

    # Asset utilization
    asset_util = score_asset_utilization(revenue, total_assets)
    components.append(asset_util * 0.15)

    return clamp(sum(components))
