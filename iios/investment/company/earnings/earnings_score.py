"""iios/investment/company/earnings/earnings_score.py
Overall earnings intelligence scoring framework.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class EarningsIntelligenceScore:
    """
    Composite score summarising all earnings intelligence dimensions.
    Scores range 0–100. This is NOT an investment recommendation.
    """
    # Dimension scores
    quality_score:       float = 0.0
    profitability_score: float = 0.0
    trend_score:         float = 0.0
    risk_score:          float = 0.0
    confidence_score:    float = 0.0

    # Composite
    overall_score:       float = 0.0

    # Weights (must sum to 1.0)
    _W_QUALITY       = 0.25
    _W_PROFITABILITY = 0.25
    _W_TREND         = 0.20
    _W_RISK          = 0.15   # inverted: low risk → high score
    _W_CONFIDENCE    = 0.15

    explanation: List[str] = field(default_factory=list)

    def recompute(self) -> None:
        """Recompute overall_score from dimension scores."""
        self.overall_score = (
            self.quality_score       * self._W_QUALITY
            + self.profitability_score * self._W_PROFITABILITY
            + self.trend_score         * self._W_TREND
            + self.risk_score          * self._W_RISK
            + self.confidence_score    * self._W_CONFIDENCE
        )

    @staticmethod
    def from_components(
        quality_score:       float,
        profitability_score: float,
        trend_score:         float,
        risk_stability_score: float,   # high = good (stable earnings)
        confidence_score:    float,
    ) -> "EarningsIntelligenceScore":
        s = EarningsIntelligenceScore(
            quality_score=quality_score,
            profitability_score=profitability_score,
            trend_score=trend_score,
            risk_score=risk_stability_score,
            confidence_score=confidence_score,
        )
        s.recompute()
        return s

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_score":       round(self.overall_score, 1),
            "quality_score":       round(self.quality_score, 1),
            "profitability_score": round(self.profitability_score, 1),
            "trend_score":         round(self.trend_score, 1),
            "risk_score":          round(self.risk_score, 1),
            "confidence_score":    round(self.confidence_score, 1),
            "explanation":         self.explanation,
        }


def profitability_to_score(
    avg_net_margin: float | None,
    avg_roic: float | None,
) -> float:
    """Convert profitability metrics into a 0-100 score."""
    scores = []
    if avg_net_margin is not None:
        # Net margin: 0% → 0, 20%+ → 100
        scores.append(min(100.0, max(0.0, avg_net_margin * 5.0)))
    if avg_roic is not None:
        # ROIC: 0% → 0, 20%+ → 100
        scores.append(min(100.0, max(0.0, avg_roic * 5.0)))
    return sum(scores) / len(scores) if scores else 50.0


def trend_to_score(direction_value: str) -> float:
    """Convert TrendDirection to a 0-100 score."""
    mapping = {
        "accelerating":      90.0,
        "recovering":        75.0,
        "stable":            60.0,
        "decelerating":      40.0,
        "deteriorating":     20.0,
        "reversal_up":       80.0,
        "reversal_down":     25.0,
        "insufficient_data": 50.0,
    }
    return mapping.get(direction_value, 50.0)
