"""iios/investment/strategy/portfolio/portfolio_health.py
PortfolioHealth — aggregated health assessment with issue flagging.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List

from iios.investment.strategy.portfolio.strategy_portfolio import StrategyPortfolio
from iios.investment.strategy.portfolio.portfolio_quality import PortfolioQuality
from iios.investment.strategy.portfolio.portfolio_confidence import PortfolioConfidence
from iios.investment.strategy.portfolio.construction_constraints import (
    ConstructionConstraints, DEFAULT_CONSTRAINTS
)


class HealthStatus(str, Enum):
    HEALTHY    = "healthy"
    DEGRADED   = "degraded"
    CRITICAL   = "critical"
    UNKNOWN    = "unknown"


@dataclass(frozen=True)
class PortfolioHealth:
    portfolio_id:  str
    health_score:  float          # 0–100
    health_status: HealthStatus
    quality:       PortfolioQuality
    confidence:    PortfolioConfidence
    issues:        List[str]       # list of detected issues
    recommendations: List[str]     # actionable suggestions
    assessed_at:   datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def assess(
        cls,
        portfolio:         StrategyPortfolio,
        strategy_conf_map: Dict[str, float],
        constraints:       ConstructionConstraints = DEFAULT_CONSTRAINTS,
    ) -> "PortfolioHealth":
        quality    = PortfolioQuality.compute(portfolio)
        confidence = PortfolioConfidence.compute(portfolio, strategy_conf_map)
        issues:   List[str] = []
        recs:     List[str] = []

        # Weight drift
        if portfolio.max_drift > constraints.rebalance_threshold:
            issues.append(
                f"Max weight drift {portfolio.max_drift:.2%} exceeds threshold "
                f"{constraints.rebalance_threshold:.2%}"
            )
            recs.append("Trigger a rebalance to restore target weights")

        # Strategy count
        n = portfolio.active_count
        if n < constraints.min_strategies:
            issues.append(
                f"Only {n} active strategies; minimum is {constraints.min_strategies}"
            )
            recs.append("Add more eligible strategies to the portfolio")

        # Concentration
        top3 = sorted(
            [a.weight for a in portfolio.active_allocations()], reverse=True
        )[:3]
        conc = sum(top3)
        if conc > constraints.max_concentration:
            issues.append(
                f"Top-3 strategies hold {conc:.2%} > max concentration {constraints.max_concentration:.2%}"
            )
            recs.append("Reduce concentration by redistributing weight to smaller allocations")

        # Low confidence
        if confidence.low_confidence_count > 0:
            issues.append(
                f"{confidence.low_confidence_count} strategies have low confidence (<40)"
            )
            recs.append("Review low-confidence strategies — consider replacement")

        # Weight sum
        tw = portfolio.total_weight
        if abs(tw - 1.0) > 0.01:
            issues.append(f"Total weight {tw:.4f} deviates from 1.0")
            recs.append("Re-optimize to correct weight sum")

        # Score
        health_score = (
            0.40 * quality.allocation_quality
            + 0.35 * confidence.weighted_confidence
            + 0.25 * (100.0 - min(100.0, len(issues) * 20.0))
        )
        health_score = max(0.0, min(100.0, health_score))

        if health_score >= 70:
            status = HealthStatus.HEALTHY
        elif health_score >= 45:
            status = HealthStatus.DEGRADED
        else:
            status = HealthStatus.CRITICAL

        return cls(
            portfolio_id=portfolio.portfolio_id,
            health_score=health_score,
            health_status=status,
            quality=quality,
            confidence=confidence,
            issues=issues,
            recommendations=recs,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "portfolio_id":    self.portfolio_id,
            "health_score":    round(self.health_score, 2),
            "health_status":   self.health_status.value,
            "quality":         self.quality.to_dict(),
            "confidence":      self.confidence.to_dict(),
            "issues":          self.issues,
            "recommendations": self.recommendations,
            "assessed_at":     self.assessed_at.isoformat(),
        }
