"""iios/investment/company/growth/growth_risk.py
Growth risk assessment.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from iios.investment.company.growth.growth_statistics import clamp


@dataclass
class GrowthRiskAssessment:
    """Risk factors that could impair growth sustainability."""
    risk_score:    float       = 0.0    # 0-100; higher = more risky
    risk_factors:  List[str]   = field(default_factory=list)
    explanation:   List[str]   = field(default_factory=list)


def assess_growth_risk(
    eps_volatility:     Optional[float] = None,
    revenue_volatility: Optional[float] = None,
    loss_rate:          Optional[float] = None,
    is_cyclical:        Optional[bool]  = None,
    avg_fcf_margin:     Optional[float] = None,
    net_margin:         Optional[float] = None,
    avg_net_margin:     Optional[float] = None,
    history_depth:      int = 0,
) -> GrowthRiskAssessment:
    """
    Assess risks that could impair growth sustainability.
    Returns a GrowthRiskAssessment with a 0-100 risk score (higher = more risky).
    """
    result = GrowthRiskAssessment()
    risk  = 0.0
    factors: List[str] = []
    explanation: List[str] = []

    # High EPS volatility
    if eps_volatility is not None and eps_volatility > 0.5:
        risk += 20.0
        factors.append("high_earnings_volatility")
        explanation.append(f"EPS volatility (CV={eps_volatility:.2f}) indicates unpredictable earnings")

    # High revenue volatility
    if revenue_volatility is not None and revenue_volatility > 0.4:
        risk += 15.0
        factors.append("high_revenue_volatility")
        explanation.append(f"Revenue volatility (CV={revenue_volatility:.2f}) indicates unstable top-line")

    # History of losses
    if loss_rate is not None and loss_rate > 0.0:
        penalty = clamp(loss_rate * 50.0, 0, 25)
        risk += penalty
        factors.append("loss_periods_in_history")
        explanation.append(f"Company reported losses in {loss_rate:.0%} of historical periods")

    # Cyclicality
    if is_cyclical is True:
        risk += 10.0
        factors.append("cyclical_business")
        explanation.append("Cyclical business model; growth tied to economic cycle")

    # Negative FCF
    if avg_fcf_margin is not None and avg_fcf_margin < 0:
        risk += 20.0
        factors.append("negative_fcf")
        explanation.append("Negative average FCF margin; growth funded by external capital")

    # Margin contraction (current < avg)
    if net_margin is not None and avg_net_margin is not None:
        if net_margin < avg_net_margin - 0.05:
            risk += 15.0
            factors.append("margin_contraction")
            explanation.append(
                f"Net margin contracting ({net_margin:.1%} vs avg {avg_net_margin:.1%})"
            )

    # Thin history
    if history_depth < 3:
        risk += 10.0
        factors.append("thin_history")
        explanation.append("Limited financial history reduces growth forecast reliability")

    result.risk_score   = clamp(risk, 0.0, 100.0)
    result.risk_factors = factors
    result.explanation  = explanation
    return result
