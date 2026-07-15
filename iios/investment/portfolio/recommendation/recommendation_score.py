"""iios/investment/portfolio/recommendation/recommendation_score.py

Composite quality scoring for portfolio recommendations.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from iios.investment.portfolio.recommendation.recommendation_types import (
    PortfolioIntelligence,
    RecommendationGrade, RecommendationLevel, RecommendationPriority,
    recommendation_score_to_grade, recommendation_score_to_level,
)

_WEIGHTS = {
    "confidence": 0.40,
    "evidence":   0.30,
    "urgency":    0.20,
    "quality":    0.10,
}


@dataclass(frozen=True)
class RecommendationDimensionScore:
    """Score for one quality dimension."""

    dimension:    str
    raw_value:    float = 0.0
    score:        float = 0.0    # [0, 1]
    weight:       float = 0.0
    contribution: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dimension":    self.dimension,
            "raw_value":    round(self.raw_value, 4),
            "score":        round(self.score, 4),
            "contribution": round(self.contribution, 4),
        }


@dataclass(frozen=True)
class RecommendationScore:
    """Composite quality score for a recommendation."""

    result_id:          str                 = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:       str                 = ""

    overall:            float               = 0.0   # [0, 1]
    confidence_score:   float               = 0.0
    evidence_score:     float               = 0.0
    urgency_score:      float               = 0.0
    quality_score:      float               = 0.0

    grade:              RecommendationGrade = RecommendationGrade.F
    level:              RecommendationLevel = RecommendationLevel.POOR
    is_publishable:     bool                = False
    dimensions:         tuple               = field(default_factory=tuple)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall":        round(self.overall, 4),
            "grade":          self.grade.value,
            "level":          self.level.value,
            "is_publishable": self.is_publishable,
            "dimensions":     [d.to_dict() for d in self.dimensions],
        }


class RecommendationScoreCalculator:
    """Calculates composite quality score for a recommendation candidate."""

    def __init__(
        self,
        min_confidence_to_publish: float = 0.50,
        weights:                   Optional[Dict[str, float]] = None,
    ) -> None:
        self._min_pub = min_confidence_to_publish
        self._weights = weights or _WEIGHTS

    def calculate(
        self,
        confidence:            float,
        n_evidence:            int,
        priority:              RecommendationPriority,
        intelligence_quality:  float,
        portfolio_id:          str = "",
    ) -> RecommendationScore:

        # 1. Confidence score = raw confidence
        conf_score = max(0.0, min(1.0, confidence))

        # 2. Evidence score: each evidence item contributes
        ev_score = min(1.0, n_evidence * 0.20)   # 5 items = perfect score

        # 3. Urgency score: based on priority
        urgency_map = {
            RecommendationPriority.IMMEDIATE:     1.00,
            RecommendationPriority.HIGH:          0.80,
            RecommendationPriority.MEDIUM:        0.60,
            RecommendationPriority.LOW:           0.30,
            RecommendationPriority.INFORMATIONAL: 0.10,
        }
        urg_score = urgency_map.get(priority, 0.50)

        # 4. Quality score = intelligence quality
        qual_score = max(0.0, min(1.0, intelligence_quality))

        # Composite
        w = self._weights
        overall = (
            conf_score * w.get("confidence", 0.40)
            + ev_score  * w.get("evidence",   0.30)
            + urg_score * w.get("urgency",     0.20)
            + qual_score * w.get("quality",    0.10)
        )
        overall = max(0.0, min(1.0, overall))

        dimensions = tuple(
            RecommendationDimensionScore(
                dimension    = k,
                raw_value    = round(rv, 4),
                score        = round(sc, 4),
                weight       = w.get(k, 0.0),
                contribution = round(sc * w.get(k, 0.0), 4),
            )
            for k, rv, sc in [
                ("confidence", confidence,         conf_score),
                ("evidence",   float(n_evidence),  ev_score),
                ("urgency",    urg_score,           urg_score),
                ("quality",    intelligence_quality,qual_score),
            ]
        )

        return RecommendationScore(
            portfolio_id     = portfolio_id,
            overall          = round(overall, 4),
            confidence_score = round(conf_score, 4),
            evidence_score   = round(ev_score, 4),
            urgency_score    = round(urg_score, 4),
            quality_score    = round(qual_score, 4),
            grade            = recommendation_score_to_grade(overall),
            level            = recommendation_score_to_level(overall),
            is_publishable   = confidence >= self._min_pub,
            dimensions       = dimensions,
        )
