"""iios/investment/strategy/opportunity/ranking_score.py
RankingScore — the composite ranking dataclass for strategy opportunities.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass(frozen=True)
class RankingScore:
    """
    Weighted composite score used to rank StrategyOpportunity objects.
    All sub-scores in [0, 100].  overall_score is a weighted combination.
    """
    strategy_id:       str
    opportunity_id:    str

    strategy_score:    float  # from EvaluationEngine
    opportunity_score: float  # from matching + suitability combined
    risk_score:        float  # risk-adjusted quality
    robustness_score:  float  # from EvaluationEngine robustness
    confidence_score:  float  # from ConfidenceScoreCalculator
    historical_score:  float  # past match pass-rate for this strategy

    overall_score:     float  # weighted composite

    rank:              int = 0  # assigned by RankingEngine

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id":       self.strategy_id,
            "opportunity_id":    self.opportunity_id,
            "strategy_score":    self.strategy_score,
            "opportunity_score": self.opportunity_score,
            "risk_score":        self.risk_score,
            "robustness_score":  self.robustness_score,
            "confidence_score":  self.confidence_score,
            "historical_score":  self.historical_score,
            "overall_score":     self.overall_score,
            "rank":              self.rank,
        }
