"""iios/investment/company/governance/investment_quality.py
Reinvestment and investment quality scoring.
"""
from __future__ import annotations

from typing import Optional

from iios.investment.company.governance.management_statistics import clamp, score_roic


def score_reinvestment_quality(
    avg_roic:          Optional[float] = None,
    eps_cagr:          Optional[float] = None,
    revenue_cagr:      Optional[float] = None,
    sustainability:    Optional[float] = None,
) -> float:
    """
    Score reinvestment quality.
    High-quality reinvestment = capital deployed at high ROIC → sustained growth.
    """
    components = []
    if avg_roic is not None:
        components.append(score_roic(avg_roic))

    if eps_cagr is not None and eps_cagr > 0:
        growth_score = clamp(eps_cagr / 0.25 * 100, 0, 100)
        components.append(growth_score)

    if sustainability is not None:
        components.append(clamp(sustainability, 0, 100))

    if not components:
        return 50.0
    return sum(components) / len(components)


def score_acquisition_quality(
    avg_roic:          Optional[float] = None,
    avg_net_margin:    Optional[float] = None,
    net_margin:        Optional[float] = None,
) -> float:
    """
    Acquisition quality proxy.
    Poor acquisitions often: dilute margins, reduce ROIC, destroy value.
    If current margins ≥ historical avg → acquisitions have been accretive.
    """
    if avg_roic is None and avg_net_margin is None:
        return 50.0

    score = 60.0

    if avg_roic is not None:
        score = score_roic(avg_roic)

    # Margin stability as acquisition quality signal
    if avg_net_margin is not None and net_margin is not None:
        delta = net_margin - avg_net_margin
        if delta > 0.02:
            score += 10.0  # accretive acquisitions expanded margins
        elif delta < -0.05:
            score -= 15.0  # acquisitions diluted margins

    return clamp(score, 0, 100)
