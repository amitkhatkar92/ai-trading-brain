"""iios/investment/company/governance/capital_efficiency.py
Capital efficiency metrics derived from financial snapshots.
"""
from __future__ import annotations

from typing import Optional

from iios.investment.company.governance.management_statistics import (
    clamp, score_roic, score_debt_level,
)


def score_capital_efficiency(
    avg_roic:            Optional[float] = None,
    avg_roe:             Optional[float] = None,
    fcf_margin:          Optional[float] = None,
    avg_ocf_to_ni:       Optional[float] = None,
    moat_score:          Optional[float] = None,
) -> float:
    """
    Compute capital efficiency score (0-100).
    High ROIC + positive FCF + strong earnings quality = capital efficient management.
    """
    components = []

    roic_s = score_roic(avg_roic)
    if avg_roic is not None:
        components.append(roic_s)

    if avg_roe is not None:
        roe_s = clamp(avg_roe / 0.20 * 80, 0, 90)
        components.append(roe_s)

    if fcf_margin is not None:
        if fcf_margin > 0.15:
            components.append(90.0)
        elif fcf_margin > 0.08:
            components.append(70.0)
        elif fcf_margin > 0.0:
            components.append(50.0)
        else:
            components.append(10.0)

    if avg_ocf_to_ni is not None:
        if avg_ocf_to_ni >= 1.0:
            components.append(80.0)
        elif avg_ocf_to_ni >= 0.80:
            components.append(60.0)
        else:
            components.append(30.0)

    if not components:
        return 50.0
    return sum(components) / len(components)
