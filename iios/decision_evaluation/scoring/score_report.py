"""iios/decision_evaluation/scoring/score_report.py"""
from __future__ import annotations

import statistics
import time
import uuid
from dataclasses import dataclass, field

from ..evaluation_constants import NormalizationMethod, ScoringMethod
from .score_calculator import AlternativeScore


@dataclass
class ScoreReport:
    report_id:             str  = field(default_factory=lambda: str(uuid.uuid4()))
    total_alternatives:    int  = 0
    total_criteria:        int  = 0
    scoring_method:        ScoringMethod        = ScoringMethod.WEIGHTED_SUM
    normalization_method:  NormalizationMethod  = NormalizationMethod.MINMAX
    scores:                dict[str, float]     = field(default_factory=dict)
    min_score:             float = 0.0
    max_score:             float = 0.0
    avg_score:             float = 0.0
    std_score:             float = 0.0
    generated_at:          float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "report_id":            self.report_id,
            "total_alternatives":   self.total_alternatives,
            "total_criteria":       self.total_criteria,
            "scoring_method":       self.scoring_method.value,
            "normalization_method": self.normalization_method.value,
            "scores":               self.scores,
            "min_score":            self.min_score,
            "max_score":            self.max_score,
            "avg_score":            self.avg_score,
            "std_score":            self.std_score,
        }


def build_score_report(
    scored_alternatives: list[AlternativeScore],
    total_criteria:      int = 0,
    scoring_method:      ScoringMethod        = ScoringMethod.WEIGHTED_SUM,
    normalization:       NormalizationMethod  = NormalizationMethod.MINMAX,
) -> ScoreReport:
    scores = {a.alternative_id: a.composite_score for a in scored_alternatives}
    vals   = list(scores.values())
    return ScoreReport(
        total_alternatives   = len(scored_alternatives),
        total_criteria       = total_criteria,
        scoring_method       = scoring_method,
        normalization_method = normalization,
        scores               = scores,
        min_score            = min(vals) if vals else 0.0,
        max_score            = max(vals) if vals else 0.0,
        avg_score            = statistics.mean(vals) if vals else 0.0,
        std_score            = statistics.stdev(vals) if len(vals) > 1 else 0.0,
    )
