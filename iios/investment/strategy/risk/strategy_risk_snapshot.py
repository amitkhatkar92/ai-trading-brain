"""iios/investment/strategy/risk/strategy_risk_snapshot.py
StrategyRiskSnapshot — immutable point-in-time capture of a risk profile.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from iios.investment.strategy.risk.strategy_risk_profile import StrategyRiskProfile


@dataclass(frozen=True)
class StrategyRiskSnapshot:
    """Immutable risk state snapshot."""
    snapshot_id:         str
    strategy_id:         str
    strategy_name:       str
    overall_risk_score:  float
    risk_grade:          str
    health_status:       str
    is_operational:      bool
    max_drawdown:        float
    drawdown_risk_score: float
    stress_rating:       str      # ROBUST | MODERATE | VULNERABLE | FRAGILE
    evaluation_count:   int
    captured_at:         datetime

    @classmethod
    def from_profile(cls, profile: StrategyRiskProfile) -> "StrategyRiskSnapshot":
        return cls(
            snapshot_id=str(uuid.uuid4()),
            strategy_id=profile.strategy_id,
            strategy_name=profile.strategy_name,
            overall_risk_score=profile.overall_risk_score,
            risk_grade=profile.risk_grade,
            health_status=profile.health_status.value,
            is_operational=profile.is_operational,
            max_drawdown=profile.drawdown.profile.max_drawdown if profile.drawdown else 0.0,
            drawdown_risk_score=profile.drawdown.overall_drawdown_risk_score if profile.drawdown else 0.0,
            stress_rating=profile.stress_report.overall_stress_rating if profile.stress_report else "UNKNOWN",
            evaluation_count=profile.evaluation_count,
            captured_at=datetime.now(timezone.utc),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id":        self.snapshot_id,
            "strategy_id":        self.strategy_id,
            "strategy_name":      self.strategy_name,
            "overall_risk_score": round(self.overall_risk_score, 2),
            "risk_grade":         self.risk_grade,
            "health_status":      self.health_status,
            "is_operational":     self.is_operational,
            "max_drawdown":       round(self.max_drawdown, 4),
            "drawdown_risk_score": round(self.drawdown_risk_score, 2),
            "stress_rating":      self.stress_rating,
            "evaluation_count":   self.evaluation_count,
            "captured_at":        self.captured_at.isoformat(),
        }
