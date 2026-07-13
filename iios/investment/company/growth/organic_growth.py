"""iios/investment/company/growth/organic_growth.py
Organic growth estimation (separating acquisition-driven from organic growth).
Uses margin stability and profitability changes as proxies.
"""
from __future__ import annotations

from typing import Optional

from iios.investment.company.growth.growth_statistics import clamp


def estimate_organic_revenue_growth(
    reported_revenue_growth: Optional[float],
    margin_expansion_bps:    Optional[float] = None,   # positive = expanding
    avg_roic:                Optional[float] = None,   # from BusinessQualitySnapshot
    operational_quality:     Optional[float] = None,   # 0-100 score
) -> Optional[float]:
    """
    Estimate organic revenue growth using heuristics.

    Rationale:
    - Acquisition-led growth is often accompanied by margin dilution and lower ROIC.
    - If margins are expanding and ROIC is high, growth is likely more organic.
    - We apply a discount to reported growth proportional to perceived inorganicity.

    This is a statistical estimate, not an audit-level attribution.
    """
    if reported_revenue_growth is None:
        return None

    discount = 0.0   # discount applied to reported growth

    # Margin contraction → likely some inorganic dilution
    if margin_expansion_bps is not None and margin_expansion_bps < -100:
        discount += 0.10   # 10% of reported growth may be inorganic

    # Low ROIC → capital deployed into lower-quality acquisitions
    if avg_roic is not None and avg_roic < 0.10:
        discount += 0.10

    # Poor operational quality → efficiency-driven growth less likely
    if operational_quality is not None and operational_quality < 40:
        discount += 0.05

    organic_estimate = reported_revenue_growth * (1.0 - clamp(discount, 0.0, 0.30))
    return organic_estimate
