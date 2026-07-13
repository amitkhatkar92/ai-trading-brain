"""iios/investment/company/growth/growth_quality.py
Growth data quality assessment.
"""
from __future__ import annotations

from typing import List, Optional

from iios.investment.company.growth.growth_profile import GrowthQuality
from iios.investment.company.growth.growth_statistics import clamp


def assess_growth_quality(
    has_eps_cagr:        bool,
    has_revenue_cagr:    bool,
    has_fcf_data:        bool,
    has_margin_data:     bool,
    history_depth:       int,
    eps_volatility:      Optional[float] = None,
    loss_rate:           Optional[float] = None,
) -> GrowthQuality:
    """
    Assess the quality and completeness of growth data and derived estimates.
    """
    issues: List[str] = []
    completeness_count = sum([
        has_eps_cagr, has_revenue_cagr, has_fcf_data, has_margin_data
    ])
    completeness = completeness_count / 4.0

    if not has_eps_cagr:
        issues.append("No EPS CAGR available")
    if not has_revenue_cagr:
        issues.append("No revenue CAGR available")
    if not has_fcf_data:
        issues.append("FCF growth data unavailable")
    if history_depth < 3:
        issues.append(f"Thin financial history ({history_depth} periods)")
    if eps_volatility is not None and eps_volatility > 0.8:
        issues.append("High EPS volatility reduces forecast reliability")
    if loss_rate is not None and loss_rate > 0.20:
        issues.append(f"Loss periods in {loss_rate:.0%} of history")

    # Derive quality label
    if completeness >= 0.90 and history_depth >= 8 and not issues:
        label = "exceptional"
    elif completeness >= 0.75 and history_depth >= 5:
        label = "strong"
    elif completeness >= 0.50 and history_depth >= 3:
        label = "moderate"
    elif completeness >= 0.25:
        label = "weak"
    elif completeness > 0:
        label = "poor"
    else:
        label = "insufficient"

    return GrowthQuality(
        quality_label=label,
        data_completeness=completeness,
        is_high_quality=(label in ("exceptional", "strong")),
        issues=issues,
    )
