"""iios/investment/decision/core/recommendation_types.py
Metadata descriptors for each RecommendationType.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from iios.investment.decision.core.decision_constants import RecommendationType


@dataclass(frozen=True)
class RecommendationDescriptor:
    recommendation:  RecommendationType
    display_name:    str
    description:     str
    direction:       str      # "bullish" | "bearish" | "neutral" | "informational"
    strength:        int      # 1 (weak) … 3 (strong)
    urgency:         str      # "low" | "medium" | "high"
    minimum_score:   float    # 0–100 minimum decision score for this recommendation

    def to_dict(self) -> Dict[str, Any]:
        return {
            "recommendation": self.recommendation.value,
            "display_name":   self.display_name,
            "description":    self.description,
            "direction":      self.direction,
            "strength":       self.strength,
            "urgency":        self.urgency,
            "minimum_score":  self.minimum_score,
        }


RECOMMENDATION_DESCRIPTORS: Dict[RecommendationType, RecommendationDescriptor] = {
    RecommendationType.STRONG_BUY: RecommendationDescriptor(
        recommendation=RecommendationType.STRONG_BUY,
        display_name="Strong Buy",
        description="High-conviction bullish recommendation. Initiate or significantly increase position.",
        direction="bullish", strength=3, urgency="high", minimum_score=80.0,
    ),
    RecommendationType.BUY: RecommendationDescriptor(
        recommendation=RecommendationType.BUY,
        display_name="Buy",
        description="Bullish recommendation. Initiate or increase position.",
        direction="bullish", strength=2, urgency="medium", minimum_score=65.0,
    ),
    RecommendationType.ACCUMULATE: RecommendationDescriptor(
        recommendation=RecommendationType.ACCUMULATE,
        display_name="Accumulate",
        description="Gradual increase on weakness. Add on dips.",
        direction="bullish", strength=1, urgency="low", minimum_score=55.0,
    ),
    RecommendationType.HOLD: RecommendationDescriptor(
        recommendation=RecommendationType.HOLD,
        display_name="Hold",
        description="Maintain current position. No action required.",
        direction="neutral", strength=1, urgency="low", minimum_score=40.0,
    ),
    RecommendationType.REDUCE: RecommendationDescriptor(
        recommendation=RecommendationType.REDUCE,
        display_name="Reduce",
        description="Gradually reduce position to limit risk.",
        direction="bearish", strength=1, urgency="medium", minimum_score=30.0,
    ),
    RecommendationType.SELL: RecommendationDescriptor(
        recommendation=RecommendationType.SELL,
        display_name="Sell",
        description="Exit or significantly reduce position.",
        direction="bearish", strength=2, urgency="high", minimum_score=20.0,
    ),
    RecommendationType.STRONG_SELL: RecommendationDescriptor(
        recommendation=RecommendationType.STRONG_SELL,
        display_name="Strong Sell",
        description="Immediate exit. High-conviction bearish outlook.",
        direction="bearish", strength=3, urgency="high", minimum_score=0.0,
    ),
    RecommendationType.AVOID: RecommendationDescriptor(
        recommendation=RecommendationType.AVOID,
        display_name="Avoid",
        description="Do not initiate. Insufficient risk/reward.",
        direction="bearish", strength=2, urgency="medium", minimum_score=0.0,
    ),
    RecommendationType.WATCHLIST: RecommendationDescriptor(
        recommendation=RecommendationType.WATCHLIST,
        display_name="Watchlist",
        description="Monitor for a better entry or further development.",
        direction="neutral", strength=1, urgency="low", minimum_score=45.0,
    ),
    RecommendationType.RESEARCH_REQUIRED: RecommendationDescriptor(
        recommendation=RecommendationType.RESEARCH_REQUIRED,
        display_name="Research Required",
        description="Insufficient information. Further research needed before decision.",
        direction="informational", strength=1, urgency="low", minimum_score=0.0,
    ),
}


def get_recommendation_descriptor(
    recommendation: RecommendationType,
) -> RecommendationDescriptor:
    return RECOMMENDATION_DESCRIPTORS[recommendation]
