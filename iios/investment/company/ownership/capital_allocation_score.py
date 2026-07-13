"""iios/investment/company/ownership/capital_allocation_score.py
Capital allocation score computation.
"""
from __future__ import annotations

from iios.investment.company.ownership.ownership_statistics import clamp


def compute_capital_allocation_score(
    dividend_policy_score:  float,
    buyback_quality_score:  float,
    reinvestment_score:     float,
    debt_management_score:  float,
    capex_efficiency_score: float = 50.0,
) -> float:
    """
    Aggregate capital allocation score from sub-components (0-100).
    Weights reflect importance from shareholder value perspective.
    """
    return clamp(
        dividend_policy_score  * 0.25
        + buyback_quality_score  * 0.20
        + reinvestment_score     * 0.25
        + debt_management_score  * 0.20
        + capex_efficiency_score * 0.10
    )
