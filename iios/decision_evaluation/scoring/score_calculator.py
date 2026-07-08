"""iios/decision_evaluation/scoring/score_calculator.py — CriterionScore, AlternativeScore, ScoreCalculator."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field

from ..evaluation_constants import CriterionDirection
from ..evaluation_context import Alternative
from ..criteria.criterion import Criterion


@dataclass
class CriterionScore:
    criterion_id:     str
    criterion_name:   str
    alternative_id:   str
    raw_score:        float             = 0.0
    normalized_score: float             = 0.0
    weight:           float             = 1.0
    weighted_score:   float             = 0.0
    direction:        CriterionDirection = CriterionDirection.MAXIMIZE
    applicable:       bool              = True
    metadata:         dict              = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "criterion_id":     self.criterion_id,
            "alternative_id":   self.alternative_id,
            "raw_score":        self.raw_score,
            "normalized_score": self.normalized_score,
            "weight":           self.weight,
            "weighted_score":   self.weighted_score,
            "direction":        self.direction.value,
        }


@dataclass
class AlternativeScore:
    alternative_id:   str
    alternative_name: str
    criterion_scores: list[CriterionScore] = field(default_factory=list)
    composite_score:  float                = 0.0
    rank:             int                  = 0
    metadata:         dict                 = field(default_factory=dict)
    scored_at:        float                = field(default_factory=time.time)

    def get_criterion_score(self, criterion_id: str) -> CriterionScore | None:
        for cs in self.criterion_scores:
            if cs.criterion_id == criterion_id:
                return cs
        return None

    def to_dict(self) -> dict:
        return {
            "alternative_id":   self.alternative_id,
            "alternative_name": self.alternative_name,
            "composite_score":  self.composite_score,
            "rank":             self.rank,
            "criterion_count":  len(self.criterion_scores),
        }


class ScoreCalculator:
    """Computes raw scores for each (alternative, criterion) pair."""

    def calculate(
        self,
        alternatives: list[Alternative],
        criteria:     list[Criterion],
    ) -> dict[str, dict[str, float]]:
        """
        Returns: {alt_id: {criterion_id: raw_score}}
        """
        result: dict[str, dict[str, float]] = {}
        for alt in alternatives:
            result[alt.alternative_id] = {}
            for crit in criteria:
                if crit.is_applicable(alt):
                    try:
                        result[alt.alternative_id][crit.criterion_id] = float(crit.score(alt))
                    except Exception:  # noqa: BLE001
                        result[alt.alternative_id][crit.criterion_id] = 0.0
                else:
                    result[alt.alternative_id][crit.criterion_id] = 0.0
        return result
