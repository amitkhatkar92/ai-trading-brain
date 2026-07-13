"""iios/investment/strategy/risk/risk_health.py
RiskHealth — aggregated health assessment of a strategy's risk state.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from iios.investment.strategy.risk.risk_input import StrategyRiskInput
from iios.investment.strategy.risk.risk_score import RiskScore
from iios.investment.strategy.risk.risk_confidence import RiskConfidence
from iios.investment.strategy.risk.risk_quality import RiskQuality
from iios.investment.strategy.risk.risk_constraints import ConstraintCheckResult
from iios.investment.strategy.risk.risk_statistics import clamp


class RiskHealthStatus(str, Enum):
    SAFE       = "safe"
    ELEVATED   = "elevated"
    HIGH_RISK  = "high_risk"
    CRITICAL   = "critical"


@dataclass(frozen=True)
class RiskHealth:
    """
    Holistic health assessment of a strategy's risk state.
    Combines score, confidence, quality, and limit compliance.
    """
    strategy_id:      str
    health_score:     float             # 0-100; 0=worst health
    health_status:    RiskHealthStatus
    risk_score:       RiskScore
    confidence:       RiskConfidence
    quality:          RiskQuality
    constraints:      ConstraintCheckResult
    issues:           List[str]
    recommendations:  List[str]
    assessed_at:      datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_operational(self) -> bool:
        """Strategy is safe to include in portfolio / execution."""
        return (
            not self.constraints.emergency_stop
            and self.health_status != RiskHealthStatus.CRITICAL
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id":     self.strategy_id,
            "health_score":    round(self.health_score, 2),
            "health_status":   self.health_status.value,
            "is_operational":  self.is_operational,
            "risk_score":      self.risk_score.to_dict(),
            "confidence":      self.confidence.to_dict(),
            "quality":         self.quality.to_dict(),
            "constraints": {
                "all_passed":    self.constraints.all_passed,
                "breach_count":  self.constraints.breach_count,
                "emergency_stop": self.constraints.emergency_stop,
            },
            "issues":          self.issues,
            "recommendations": self.recommendations,
            "assessed_at":     self.assessed_at.isoformat(),
        }

    @classmethod
    def assess(
        cls,
        inp:         StrategyRiskInput,
        risk_score:  RiskScore,
        confidence:  RiskConfidence,
        quality:     RiskQuality,
        constraints: ConstraintCheckResult,
    ) -> "RiskHealth":
        issues:  List[str] = []
        recs:    List[str] = []

        if constraints.emergency_stop:
            issues.append("EMERGENCY STOP: risk score exceeds emergency threshold")
            recs.append("Immediately suspend this strategy — consult risk team before reinstating")

        for breach in constraints.breaches:
            issues.append(f"Limit breach: {breach.message}")

        if confidence.overall_confidence < 50.0:
            issues.append("Low risk assessment confidence — evaluate with caution")
            recs.append("Collect more evaluation data to improve confidence")

        if quality.overall_quality < 50.0:
            issues.append("Poor risk assessment quality")
            recs.append("Review input completeness and re-evaluate")

        if risk_score.risk_grade in ("D", "F"):
            issues.append(f"High risk grade: {risk_score.risk_grade}")
            recs.append("Consider position reduction or strategy suspension")

        # Health score: inverse-risk, modulated by confidence and quality
        inv_risk  = 100.0 - risk_score.overall_risk_score
        health    = clamp(
            0.55 * inv_risk
            + 0.25 * confidence.overall_confidence
            + 0.20 * quality.overall_quality
        )

        # Penalise for breaches
        health = clamp(health - constraints.breach_count * 10.0)

        # Status mapping (health 0-100; higher = healthier)
        if health >= 70:
            status = RiskHealthStatus.SAFE
        elif health >= 50:
            status = RiskHealthStatus.ELEVATED
        elif health >= 30:
            status = RiskHealthStatus.HIGH_RISK
        else:
            status = RiskHealthStatus.CRITICAL

        return cls(
            strategy_id=inp.strategy_id,
            health_score=health,
            health_status=status,
            risk_score=risk_score,
            confidence=confidence,
            quality=quality,
            constraints=constraints,
            issues=issues,
            recommendations=recs,
        )
