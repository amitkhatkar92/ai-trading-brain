"""iios/investment/company/ownership/economic_return.py
Economic return metrics for shareholder value analysis.
"""
from __future__ import annotations

from typing import Optional

from iios.investment.company.ownership.ownership_statistics import (
    clamp, score_roic_spread, score_roe_sustainability,
)


def score_economic_value_added(
    avg_roic:     Optional[float],
    avg_roe:      Optional[float],
    fcf_margin:   Optional[float],
) -> float:
    """
    Score economic value added to shareholders.
    Combines ROIC spread with ROE sustainability and FCF generation.
    """
    components: list[float] = []

    # ROIC above cost of capital (primary signal)
    roic_score = score_roic_spread(avg_roic)
    components.append(roic_score * 0.50)

    # ROE sustainability (secondary signal)
    roe_score = score_roe_sustainability(avg_roe, 0.35)   # assume 35% payout as default
    components.append(roe_score * 0.30)

    # FCF generation (cash backing earnings)
    if fcf_margin is not None:
        if fcf_margin >= 0.15:
            fcf_score = 100.0
        elif fcf_margin >= 0.10:
            fcf_score = 80.0
        elif fcf_margin >= 0.05:
            fcf_score = 60.0
        elif fcf_margin >= 0:
            fcf_score = 35.0
        else:
            fcf_score = 5.0
    else:
        fcf_score = 45.0
    components.append(fcf_score * 0.20)

    return clamp(sum(components))


def score_earnings_power(
    net_margin:    Optional[float],
    avg_net_margin: Optional[float],
    eps_cagr:      Optional[float],
    consistency_score: Optional[float],
) -> float:
    """
    Score earnings power and sustainability from shareholder value perspective.
    """
    base = 50.0

    # Margin quality
    margin = avg_net_margin or net_margin
    if margin is not None:
        if margin >= 0.20:
            base = 90.0
        elif margin >= 0.15:
            base = 80.0
        elif margin >= 0.10:
            base = 65.0
        elif margin >= 0.05:
            base = 50.0
        elif margin >= 0:
            base = 35.0
        else:
            base = 10.0

    # EPS growth adjustment
    if eps_cagr is not None:
        if eps_cagr >= 0.20:
            base += 10.0
        elif eps_cagr >= 0.10:
            base += 5.0
        elif eps_cagr < 0:
            base -= 15.0

    # Consistency adjustment
    if consistency_score is not None:
        if consistency_score >= 75:
            base += 5.0
        elif consistency_score < 40:
            base -= 10.0

    return clamp(base)


def score_growth_value(
    revenue_cagr:       Optional[float],
    eps_cagr:           Optional[float],
    sustainability_score: Optional[float],
) -> float:
    """
    Score long-term growth value creation potential.
    """
    components: list[float] = []

    if revenue_cagr is not None:
        if revenue_cagr >= 0.20:
            components.append(100.0)
        elif revenue_cagr >= 0.12:
            components.append(80.0)
        elif revenue_cagr >= 0.06:
            components.append(60.0)
        elif revenue_cagr >= 0:
            components.append(40.0)
        else:
            components.append(10.0)

    if eps_cagr is not None:
        if eps_cagr >= 0.20:
            components.append(100.0)
        elif eps_cagr >= 0.12:
            components.append(80.0)
        elif eps_cagr >= 0.05:
            components.append(60.0)
        elif eps_cagr >= 0:
            components.append(35.0)
        else:
            components.append(5.0)

    if sustainability_score is not None:
        components.append(sustainability_score)

    if not components:
        return 50.0

    import statistics
    return clamp(statistics.mean(components))
