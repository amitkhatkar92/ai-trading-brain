"""iios/investment/strategy/learning/recommendation_score.py
RecommendationScore — priority and urgency scoring for recommendations.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from iios.investment.strategy.learning.learning_statistics import clamp


@dataclass(frozen=True)
class RecommendationScore:
    """Priority scoring for a recommendation."""
    urgency:    float   # 0-100; time sensitivity
    impact:     float   # 0-100; expected improvement magnitude
    confidence: float   # 0-100; how confident we are it will help
    effort:     float   # 0-100; 100 = low effort (easy win)
    priority_score: float  # weighted composite

    @property
    def priority_label(self) -> str:
        if self.priority_score >= 70: return "HIGH"
        if self.priority_score >= 40: return "MEDIUM"
        return "LOW"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "urgency":        round(self.urgency, 2),
            "impact":         round(self.impact, 2),
            "confidence":     round(self.confidence, 2),
            "effort":         round(self.effort, 2),
            "priority_score": round(self.priority_score, 2),
            "priority_label": self.priority_label,
        }


def score_recommendation(
    urgency:       float,
    impact:        float,
    confidence:    float,
    effort:        float = 50.0,   # default: moderate effort
) -> RecommendationScore:
    """
    Compute a RecommendationScore.
    Weights: urgency 30%, impact 40%, confidence 20%, effort 10%.
    """
    composite = clamp(
        0.30 * urgency
        + 0.40 * impact
        + 0.20 * confidence
        + 0.10 * effort
    )
    return RecommendationScore(
        urgency=urgency,
        impact=impact,
        confidence=confidence,
        effort=effort,
        priority_score=composite,
    )
