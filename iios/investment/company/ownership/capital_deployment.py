"""iios/investment/company/ownership/capital_deployment.py
Capital deployment quality scoring functions.
"""
from __future__ import annotations

from typing import Optional

from iios.investment.company.ownership.ownership_statistics import clamp


def score_capex_quality(
    capex: Optional[float],
    revenue: Optional[float],
    revenue_cagr: Optional[float],
    avg_roic: Optional[float],
) -> float:
    """
    Score capital expenditure quality.
    High capex combined with high ROIC and revenue growth = disciplined investment.
    """
    if capex is None or revenue is None or revenue <= 0:
        return 50.0

    capex_intensity = abs(capex) / revenue   # fraction
    components: list[float] = []

    # ROIC context: high ROIC implies capex is deployed well
    if avg_roic is not None:
        if avg_roic >= 0.20:
            components.append(90.0)
        elif avg_roic >= 0.15:
            components.append(75.0)
        elif avg_roic >= 0.10:
            components.append(60.0)
        elif avg_roic >= 0.05:
            components.append(40.0)
        else:
            components.append(15.0)

    # Revenue growth context: high capex + high growth = good
    if revenue_cagr is not None:
        if capex_intensity > 0.10 and revenue_cagr > 0.12:
            components.append(80.0)   # investing in growth
        elif capex_intensity > 0.05 and revenue_cagr > 0.05:
            components.append(65.0)
        elif capex_intensity < 0.03:
            components.append(55.0)   # low capex may be asset-light (OK)
        else:
            components.append(45.0)

    return clamp(sum(components) / len(components)) if components else 50.0


def score_rd_investment(
    rd_expense:   Optional[float],
    revenue:      Optional[float],
    revenue_cagr: Optional[float],
) -> float:
    """
    Score R&D investment appropriateness.
    Only relevant for technology/pharma-type businesses; graceful for others.
    """
    if rd_expense is None or revenue is None or revenue <= 0:
        return 50.0   # neutral when data unavailable

    rd_intensity = abs(rd_expense) / revenue

    if rd_intensity <= 0.01:
        # Low R&D — could be appropriate for non-tech
        return 55.0
    if rd_intensity <= 0.05:
        base = 65.0
    elif rd_intensity <= 0.15:
        base = 80.0
    elif rd_intensity <= 0.25:
        base = 70.0
    else:
        base = 55.0   # excessive R&D without proven returns

    # Boost if revenue growth strong
    if revenue_cagr is not None and revenue_cagr > 0.12:
        base += 5.0

    return clamp(base)


def score_cash_utilization(
    cash: Optional[float],
    revenue: Optional[float],
    fcf: Optional[float],
) -> float:
    """
    Score cash utilization quality.
    Excess idle cash = poor capital discipline.
    Optimal: 10-25% of revenue as working cash buffer.
    """
    if cash is None or revenue is None or revenue <= 0:
        return 50.0

    cash_ratio = cash / revenue
    # Too little → liquidity risk; too much → opportunity cost
    if cash_ratio < 0.05:
        return 40.0
    if cash_ratio < 0.15:
        return 75.0
    if cash_ratio <= 0.30:
        return 85.0
    if cash_ratio <= 0.50:
        return 65.0 - (cash_ratio - 0.30) / 0.20 * 15
    # Excessive cash > 50% revenue = value destruction through inactivity
    return clamp(50.0 - (cash_ratio - 0.50) / 0.50 * 30)
