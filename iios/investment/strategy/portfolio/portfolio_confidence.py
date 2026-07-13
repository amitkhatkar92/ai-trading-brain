"""iios/investment/strategy/portfolio/portfolio_confidence.py
PortfolioConfidence — composite confidence derived from constituent strategies.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from iios.investment.strategy.portfolio.strategy_portfolio import StrategyPortfolio
from iios.investment.strategy.portfolio.portfolio_statistics import (
    weighted_average, safe_div
)


@dataclass(frozen=True)
class PortfolioConfidence:
    """
    Portfolio confidence score aggregated from individual strategy confidence scores.
    Higher confidence means the evaluation engine had strong conviction on more strategies.
    All scores in [0, 100].
    """
    portfolio_id:        str
    weighted_confidence: float   # weight-avg of strategy confidence_scores
    min_confidence:      float   # worst strategy confidence
    max_confidence:      float   # best strategy confidence
    confidence_spread:   float   # max - min
    low_confidence_count: int    # strategies with confidence < 40

    @property
    def grade(self) -> str:
        if self.weighted_confidence >= 75:
            return "HIGH"
        if self.weighted_confidence >= 50:
            return "MEDIUM"
        return "LOW"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "portfolio_id":        self.portfolio_id,
            "weighted_confidence": round(self.weighted_confidence, 2),
            "min_confidence":      round(self.min_confidence, 2),
            "max_confidence":      round(self.max_confidence, 2),
            "confidence_spread":   round(self.confidence_spread, 2),
            "low_confidence_count": self.low_confidence_count,
            "grade":               self.grade,
        }

    @classmethod
    def compute(
        cls,
        portfolio:         StrategyPortfolio,
        strategy_conf_map: Dict[str, float],   # strategy_id → confidence_score (0–100)
    ) -> "PortfolioConfidence":
        active = portfolio.active_allocations()
        pid    = portfolio.portfolio_id

        if not active:
            return cls(pid, 0.0, 0.0, 0.0, 0.0, 0)

        scores  = [strategy_conf_map.get(a.strategy_id, 0.0) for a in active]
        weights = [a.weight for a in active]

        weighted_conf = weighted_average(scores, weights)
        low_count = sum(1 for s in scores if s < 40.0)

        return cls(
            portfolio_id=pid,
            weighted_confidence=weighted_conf,
            min_confidence=min(scores),
            max_confidence=max(scores),
            confidence_spread=max(scores) - min(scores),
            low_confidence_count=low_count,
        )
