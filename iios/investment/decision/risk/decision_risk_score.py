"""iios/investment/decision/risk/decision_risk_score.py
DecisionRiskScore — weighted aggregate with scenario adjustment.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from iios.investment.decision.risk.risk_constants import RiskLevel, RiskQualityGrade


@dataclass(frozen=True)
class DecisionRiskScore:
    base_risk:        float   # 0–100 weighted dimension risk
    scenario_risk:    float   # 0–100 blended scenario risk
    overall_risk:     float   # 0–100 final composite
    risk_level:       RiskLevel
    grade:            RiskQualityGrade
    scenario_weight:  float   # 0–1 how much scenarios adjust base

    def to_dict(self) -> Dict[str, Any]:
        return {
            "base_risk":       round(self.base_risk, 2),
            "scenario_risk":   round(self.scenario_risk, 2),
            "overall_risk":    round(self.overall_risk, 2),
            "risk_level":      self.risk_level.value,
            "grade":           self.grade.value,
            "scenario_weight": round(self.scenario_weight, 4),
        }


def compute_risk_score(
    market_risk:     float,
    company_risk:    float,
    strategy_risk:   float,
    execution_risk:  float,
    confidence_risk: float,
    scenario_blended_risk: Optional[float] = None,
    *,
    dim_weights:     Tuple[float, float, float, float, float] = (0.30, 0.25, 0.20, 0.15, 0.10),
    scenario_weight: float = 0.20,
) -> DecisionRiskScore:
    """
    Compute final risk score from dimension scores and optional scenario analysis.

    Args:
        *_risk: dimension risk scores 0–100
        scenario_blended_risk: optional scenario-blended risk 0–100
        dim_weights: (market, company, strategy, execution, confidence)
        scenario_weight: 0–1 how much scenario_risk adjusts base_risk
    """
    mw, cw, sw, ew, cnw = dim_weights
    base_risk = (
        market_risk     * mw
        + company_risk  * cw
        + strategy_risk * sw
        + execution_risk * ew
        + confidence_risk * cnw
    )
    base_risk = min(100.0, max(0.0, base_risk))

    if scenario_blended_risk is not None:
        sc_weight  = min(0.40, max(0.0, scenario_weight))
        overall    = base_risk * (1.0 - sc_weight) + scenario_blended_risk * sc_weight
        sc_risk    = scenario_blended_risk
    else:
        overall    = base_risk
        sc_risk    = base_risk
        sc_weight  = 0.0

    overall = min(100.0, max(0.0, overall))
    level   = RiskLevel.from_score(overall)
    grade   = RiskQualityGrade.from_quality(100.0 - overall)

    return DecisionRiskScore(
        base_risk=round(base_risk, 4),
        scenario_risk=round(sc_risk, 4),
        overall_risk=round(overall, 4),
        risk_level=level,
        grade=grade,
        scenario_weight=round(sc_weight, 4),
    )
