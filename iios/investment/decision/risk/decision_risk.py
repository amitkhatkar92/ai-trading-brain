"""iios/investment/decision/risk/decision_risk.py
DecisionRisk — core output dataclass from one risk evaluation pass.
Immutable after construction.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Tuple

from iios.investment.decision.risk.risk_constants import (
    RiskDimension,
    RiskLevel,
    MARKET_RISK_WEIGHT,
    COMPANY_RISK_WEIGHT,
    STRATEGY_RISK_WEIGHT,
    EXECUTION_RISK_WEIGHT,
    CONFIDENCE_RISK_WEIGHT,
)


@dataclass(frozen=True)
class DecisionRisk:
    """
    Complete risk profile for one investment decision.
    Risk scores: 0 = no risk, 100 = maximum risk.
    Never contains investment recommendations.
    """
    risk_id:          str
    decision_id:      str
    subject_id:       str
    subject_type:     str
    # ── dimension risk scores ─────────────────────────────────────────────
    market_risk:      float    # 0–100
    company_risk:     float    # 0–100
    strategy_risk:    float    # 0–100
    execution_risk:   float    # 0–100
    confidence_risk:  float    # 0–100
    # ── aggregate ─────────────────────────────────────────────────────────
    overall_risk:     float    # 0–100 weighted
    risk_level:       RiskLevel
    # ── metadata ──────────────────────────────────────────────────────────
    dimension_weights: Tuple[Tuple[str, float], ...]
    controls_breached: bool
    scenarios_evaluated: int
    version:          int
    computed_at:      datetime

    @property
    def is_elevated(self) -> bool:
        return self.overall_risk >= 60.0

    @property
    def blocks_execution(self) -> bool:
        return self.risk_level.blocks_execution or self.controls_breached

    def dimension_risk(self, dim: RiskDimension) -> float:
        mapping = {
            RiskDimension.MARKET:     self.market_risk,
            RiskDimension.COMPANY:    self.company_risk,
            RiskDimension.STRATEGY:   self.strategy_risk,
            RiskDimension.EXECUTION:  self.execution_risk,
            RiskDimension.CONFIDENCE: self.confidence_risk,
        }
        return mapping[dim]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "risk_id":            self.risk_id,
            "decision_id":        self.decision_id,
            "subject_id":         self.subject_id,
            "subject_type":       self.subject_type,
            "market_risk":        round(self.market_risk, 2),
            "company_risk":       round(self.company_risk, 2),
            "strategy_risk":      round(self.strategy_risk, 2),
            "execution_risk":     round(self.execution_risk, 2),
            "confidence_risk":    round(self.confidence_risk, 2),
            "overall_risk":       round(self.overall_risk, 2),
            "risk_level":         self.risk_level.value,
            "controls_breached":  self.controls_breached,
            "scenarios_evaluated": self.scenarios_evaluated,
            "version":            self.version,
            "computed_at":        self.computed_at.isoformat(),
        }


def build_decision_risk(
    decision_id:     str,
    subject_id:      str,
    subject_type:    str,
    market_risk:     float,
    company_risk:    float,
    strategy_risk:   float,
    execution_risk:  float,
    confidence_risk: float,
    controls_breached: bool,
    scenarios_evaluated: int,
    version:         int,
    *,
    mw: float = MARKET_RISK_WEIGHT,
    cw: float = COMPANY_RISK_WEIGHT,
    sw: float = STRATEGY_RISK_WEIGHT,
    ew: float = EXECUTION_RISK_WEIGHT,
    cnw: float = CONFIDENCE_RISK_WEIGHT,
) -> DecisionRisk:
    overall = (
        market_risk     * mw
        + company_risk  * cw
        + strategy_risk * sw
        + execution_risk * ew
        + confidence_risk * cnw
    )
    overall = max(0.0, min(100.0, overall))

    weights: Tuple[Tuple[str, float], ...] = (
        (RiskDimension.MARKET.value,     mw),
        (RiskDimension.COMPANY.value,    cw),
        (RiskDimension.STRATEGY.value,   sw),
        (RiskDimension.EXECUTION.value,  ew),
        (RiskDimension.CONFIDENCE.value, cnw),
    )

    return DecisionRisk(
        risk_id=str(uuid.uuid4()),
        decision_id=decision_id,
        subject_id=subject_id,
        subject_type=subject_type,
        market_risk=round(market_risk, 4),
        company_risk=round(company_risk, 4),
        strategy_risk=round(strategy_risk, 4),
        execution_risk=round(execution_risk, 4),
        confidence_risk=round(confidence_risk, 4),
        overall_risk=round(overall, 4),
        risk_level=RiskLevel.from_score(overall),
        dimension_weights=weights,
        controls_breached=controls_breached,
        scenarios_evaluated=scenarios_evaluated,
        version=version,
        computed_at=datetime.now(timezone.utc),
    )
