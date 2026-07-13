"""iios/investment/company/growth/growth_confidence.py
Overall confidence scorer for GrowthSnapshot.
"""
from __future__ import annotations

from typing import Optional

from iios.investment.company.growth.growth_statistics import clamp


def compute_overall_confidence(
    history_depth:      int,
    has_eps_cagr:       bool,
    has_revenue_cagr:   bool,
    has_fcf_data:       bool,
    quality_label:      str,
    sustainability:     float,    # 0-100
    eps_volatility:     Optional[float] = None,
) -> float:
    """
    Compute a 0-1 confidence that the GrowthSnapshot is reliable.
    """
    score = 0.0

    # Data availability
    if has_eps_cagr:     score += 0.25
    if has_revenue_cagr: score += 0.20
    if has_fcf_data:     score += 0.10

    # History depth
    if history_depth >= 10:
        score += 0.20
    elif history_depth >= 5:
        score += 0.12
    elif history_depth >= 3:
        score += 0.06

    # Quality label
    quality_map = {
        "exceptional": 0.20, "strong": 0.16, "moderate": 0.10,
        "weak": 0.05, "poor": 0.02, "insufficient": 0.0,
    }
    score += quality_map.get(quality_label, 0.0)

    # Volatility penalty
    if eps_volatility is not None and eps_volatility > 0.5:
        score -= 0.08

    # Sustainability bonus
    score += clamp(sustainability / 100.0 * 0.05, 0, 0.05)

    return clamp(score, 0.0, 1.0)
