"""iios/investment/strategy/opportunity/recommendation_summary.py
RecommendationSummary — structured, auditable recommendation output.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List

from iios.investment.strategy.opportunity.evidence_collector import EvidenceBundle


@dataclass(frozen=True)
class RecommendationSummary:
    """
    Full recommendation for one strategy–opportunity pair.
    All fields are set at construction; immutable thereafter.
    """
    recommendation_id:        str
    strategy_id:              str
    strategy_name:            str
    opportunity_id:           str
    opportunity_type:         str

    # Scores
    overall_score:            float  # 0–100
    matching_score:           float
    suitability_score:        float
    ranking_score:            float
    rank:                     int

    # Narrative
    headline:                 str
    why_selected:             List[str]
    caution_factors:          List[str]
    neutral_observations:     List[str]
    confidence_explanation:   str
    net_confidence:           float  # 0–1

    # Applicable conditions
    best_regimes:             List[str]
    best_timeframes:          List[str]
    expected_risks:           List[str]

    # Audit
    evidence:                 EvidenceBundle
    generated_at:             datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "recommendation_id":      self.recommendation_id,
            "strategy_id":            self.strategy_id,
            "strategy_name":          self.strategy_name,
            "opportunity_id":         self.opportunity_id,
            "opportunity_type":       self.opportunity_type,
            "overall_score":          self.overall_score,
            "matching_score":         self.matching_score,
            "suitability_score":      self.suitability_score,
            "ranking_score":          self.ranking_score,
            "rank":                   self.rank,
            "headline":               self.headline,
            "why_selected":           self.why_selected,
            "caution_factors":        self.caution_factors,
            "neutral_observations":   self.neutral_observations,
            "confidence_explanation": self.confidence_explanation,
            "net_confidence":         self.net_confidence,
            "best_regimes":           self.best_regimes,
            "best_timeframes":        self.best_timeframes,
            "expected_risks":         self.expected_risks,
            "evidence":               self.evidence.to_dict(),
            "generated_at":           self.generated_at.isoformat(),
        }
