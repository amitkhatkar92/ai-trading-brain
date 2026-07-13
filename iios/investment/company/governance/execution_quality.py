"""iios/investment/company/governance/execution_quality.py
Operational execution quality scoring.
"""
from __future__ import annotations

from typing import Optional

from iios.investment.company.governance.management_statistics import clamp


def score_execution_quality(
    operational_quality_score: Optional[float] = None,   # 0-100
    earnings_stability_score:  Optional[float] = None,   # 0-100
    avg_roic:                  Optional[float] = None,
    moat_score:                Optional[float] = None,
    eps_cagr:                  Optional[float] = None,   # growth delivery
    revenue_cagr:              Optional[float] = None,
) -> float:
    """
    Compute an overall execution quality score (0-100).
    Execution quality = management's ability to turn strategy into results.
    """
    components = []

    if operational_quality_score is not None:
        components.append(clamp(operational_quality_score, 0, 100))
    if earnings_stability_score is not None:
        components.append(clamp(earnings_stability_score, 0, 100))
    if avg_roic is not None:
        roic_score = clamp(avg_roic / 0.25 * 100, 0, 100)
        components.append(roic_score)
    if moat_score is not None:
        components.append(clamp(moat_score, 0, 100))

    # Growth delivery adds bonus
    if eps_cagr is not None and eps_cagr > 0.10:
        components.append(min(eps_cagr / 0.25 * 100, 100))

    if not components:
        return 50.0
    return sum(components) / len(components)
