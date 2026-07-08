"""iios/decision_evaluation/ranking/ranking_report.py"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field

from ..evaluation_constants import RankingMethod
from ..scoring.score_calculator import AlternativeScore


@dataclass
class RankingReport:
    report_id:          str          = field(default_factory=lambda: str(uuid.uuid4()))
    ranking_method:     RankingMethod = RankingMethod.SCORE
    ranked_ids:         list[str]    = field(default_factory=list)
    scores:             dict[str, float] = field(default_factory=dict)
    top_alternative_id: str | None   = None
    pareto_frontier:    list[str]    = field(default_factory=list)
    generated_at:       float        = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "report_id":          self.report_id,
            "ranking_method":     self.ranking_method.value,
            "ranked_ids":         self.ranked_ids,
            "scores":             self.scores,
            "top_alternative_id": self.top_alternative_id,
            "pareto_frontier":    self.pareto_frontier,
        }


def build_ranking_report(
    ranked:         list[AlternativeScore],
    method:         RankingMethod = RankingMethod.SCORE,
    pareto_frontier: list[str] | None = None,
) -> RankingReport:
    ranked_ids = [a.alternative_id for a in ranked]
    scores     = {a.alternative_id: a.composite_score for a in ranked}
    top        = ranked[0].alternative_id if ranked else None
    # Pareto frontier = alternatives with rank 1
    pareto     = pareto_frontier or [a.alternative_id for a in ranked if a.rank == 1]
    return RankingReport(
        ranking_method     = method,
        ranked_ids         = ranked_ids,
        scores             = scores,
        top_alternative_id = top,
        pareto_frontier    = pareto,
    )
