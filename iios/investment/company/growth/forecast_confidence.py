"""iios/investment/company/growth/forecast_confidence.py
Forecast confidence scoring.
"""
from __future__ import annotations

from typing import Optional

from iios.investment.company.growth.growth_statistics import clamp


def compute_forecast_confidence(
    history_depth:      int,
    has_eps_cagr:       bool,
    has_revenue_cagr:   bool,
    sustainability:     float,   # 0-100
    eps_volatility:     Optional[float] = None,
    revenue_volatility: Optional[float] = None,
) -> float:
    """
    Compute a 0-1 confidence score for the growth forecast.
    Considers data completeness, history depth, and volatility.
    """
    score = 0.0

    # Data availability
    if has_eps_cagr:
        score += 0.30
    if has_revenue_cagr:
        score += 0.20

    # History depth
    if history_depth >= 10:
        score += 0.25
    elif history_depth >= 5:
        score += 0.15
    elif history_depth >= 3:
        score += 0.08
    else:
        score += 0.0

    # Sustainability
    score += clamp(sustainability / 100.0 * 0.20, 0, 0.20)

    # Volatility penalties
    if eps_volatility is not None and eps_volatility > 0.5:
        score -= 0.10
    if revenue_volatility is not None and revenue_volatility > 0.5:
        score -= 0.05

    return clamp(score, 0.0, 1.0)
