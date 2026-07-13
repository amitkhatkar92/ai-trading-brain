"""iios/investment/company/ownership/capital_productivity.py
Capital productivity metrics.
"""
from __future__ import annotations

from typing import Optional

from iios.investment.company.ownership.ownership_statistics import clamp
from iios.investment.company.ownership.capital_efficiency import score_invested_capital_productivity


def score_reinvestment_effectiveness(
    revenue_cagr:  Optional[float],
    avg_roic:      Optional[float],
    capex:         Optional[float],
    revenue:       Optional[float],
) -> float:
    """
    Score how effectively reinvested capital generates incremental revenue.
    High capex intensity + high revenue growth + high ROIC = excellent reinvestment.
    """
    if avg_roic is None and revenue_cagr is None:
        return 50.0

    components: list[float] = []

    if avg_roic is not None:
        from iios.investment.company.ownership.ownership_statistics import score_roic_spread
        components.append(score_roic_spread(avg_roic))

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
            components.append(5.0)

    # If reinvesting heavily (high capex) AND growing fast → premium
    if (capex is not None and revenue is not None and revenue > 0
            and revenue_cagr is not None and revenue_cagr > 0.12
            and abs(capex) / revenue > 0.08):
        components.append(90.0)

    if not components:
        return 50.0

    import statistics
    return clamp(statistics.mean(components))


def score_capital_productivity(
    fcf:          Optional[float],
    total_equity: Optional[float],
    total_debt:   Optional[float],
    avg_roic:     Optional[float],
    revenue_cagr: Optional[float],
) -> float:
    """
    Composite capital productivity score (0-100).
    """
    components: list[float] = []

    # FCF / Invested capital
    fcf_ic = score_invested_capital_productivity(fcf, total_equity, total_debt)
    components.append(fcf_ic * 0.40)

    # Reinvestment effectiveness
    re_score = score_reinvestment_effectiveness(revenue_cagr, avg_roic, None, None)
    components.append(re_score * 0.35)

    # ROIC spread contribution
    if avg_roic is not None:
        from iios.investment.company.ownership.ownership_statistics import score_roic_spread
        components.append(score_roic_spread(avg_roic) * 0.25)
    else:
        components.append(40.0 * 0.25)

    return clamp(sum(components))
