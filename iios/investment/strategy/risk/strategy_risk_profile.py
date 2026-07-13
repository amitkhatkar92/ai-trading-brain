"""iios/investment/strategy/risk/strategy_risk_profile.py
StrategyRiskProfile — mutable runtime risk state for a single strategy.
Updated by the engine as new inputs arrive.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.investment.strategy.risk.risk_score import RiskScore
from iios.investment.strategy.risk.risk_health import RiskHealth, RiskHealthStatus
from iios.investment.strategy.risk.drawdown_engine import DrawdownReport
from iios.investment.strategy.risk.stress_testing import StressTestReport
from iios.investment.strategy.risk.risk_constraints import ConstraintCheckResult
from iios.investment.strategy.risk.risk_confidence import RiskConfidence


@dataclass
class StrategyRiskProfile:
    """
    Mutable container for a strategy's current risk state.
    Updated atomically by StrategyRiskEngine on each evaluation cycle.
    """
    strategy_id:   str
    strategy_name: str

    # Current risk intelligence (set after first evaluation)
    risk_score:     Optional[RiskScore]            = None
    health:         Optional[RiskHealth]           = None
    drawdown:       Optional[DrawdownReport]       = None
    stress_report:  Optional[StressTestReport]     = None
    constraints:    Optional[ConstraintCheckResult] = None
    confidence:     Optional[RiskConfidence]       = None

    # Timestamps
    created_at:    datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_evaluated: Optional[datetime] = None
    evaluation_count: int = 0

    @property
    def is_evaluated(self) -> bool:
        return self.risk_score is not None

    @property
    def is_operational(self) -> bool:
        if self.health is None:
            return False
        return self.health.is_operational

    @property
    def overall_risk_score(self) -> float:
        return self.risk_score.overall_risk_score if self.risk_score else 0.0

    @property
    def risk_grade(self) -> str:
        return self.risk_score.risk_grade if self.risk_score else "?"

    @property
    def health_status(self) -> RiskHealthStatus:
        if self.health:
            return self.health.health_status
        return RiskHealthStatus.SAFE

    def update(
        self,
        risk_score:    RiskScore,
        health:        RiskHealth,
        drawdown:      DrawdownReport,
        stress_report: StressTestReport,
        constraints:   ConstraintCheckResult,
        confidence:    RiskConfidence,
    ) -> None:
        self.risk_score    = risk_score
        self.health        = health
        self.drawdown      = drawdown
        self.stress_report = stress_report
        self.constraints   = constraints
        self.confidence    = confidence
        self.last_evaluated = datetime.now(timezone.utc)
        self.evaluation_count += 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id":       self.strategy_id,
            "strategy_name":     self.strategy_name,
            "is_evaluated":      self.is_evaluated,
            "is_operational":    self.is_operational,
            "overall_risk_score": self.overall_risk_score,
            "risk_grade":        self.risk_grade,
            "health_status":     self.health_status.value,
            "evaluation_count":  self.evaluation_count,
            "last_evaluated":    self.last_evaluated.isoformat() if self.last_evaluated else None,
        }
