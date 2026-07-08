"""iios/decision_evaluation/tradeoff/decision_matrix.py"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field

from ..evaluation_context import Alternative
from ..criteria.criterion import Criterion
from ..scoring.score_calculator import AlternativeScore


@dataclass
class DecisionMatrix:
    """
    Full score matrix with alternatives × criteria,
    holding both raw and normalized scores.
    """
    matrix_id:         str = field(default_factory=lambda: str(uuid.uuid4()))
    alternative_ids:   list[str] = field(default_factory=list)
    criterion_ids:     list[str] = field(default_factory=list)
    raw_scores:        dict[str, dict[str, float]] = field(default_factory=dict)
    normalized_scores: dict[str, dict[str, float]] = field(default_factory=dict)
    weights:           dict[str, float]             = field(default_factory=dict)
    composite_scores:  dict[str, float]             = field(default_factory=dict)
    created_at:        float = field(default_factory=time.time)

    def get_score(self, alt_id: str, criterion_id: str, normalized: bool = True) -> float:
        src = self.normalized_scores if normalized else self.raw_scores
        return src.get(alt_id, {}).get(criterion_id, 0.0)

    def tabular(self) -> dict:
        """Returns a dict with 'headers' and 'rows' suitable for tabular display."""
        headers = ["alternative"] + self.criterion_ids + ["composite"]
        rows: list[list] = []
        for alt_id in self.alternative_ids:
            row: list = [alt_id]
            for cid in self.criterion_ids:
                row.append(self.normalized_scores.get(alt_id, {}).get(cid, 0.0))
            row.append(self.composite_scores.get(alt_id, 0.0))
            rows.append(row)
        return {"headers": headers, "rows": rows}

    def to_dict(self) -> dict:
        return {
            "matrix_id":        self.matrix_id,
            "alternatives":     self.alternative_ids,
            "criteria":         self.criterion_ids,
            "composite_scores": self.composite_scores,
            "created_at":       self.created_at,
        }


def build_decision_matrix(
    alternatives:      list[Alternative],
    criteria:          list[Criterion],
    raw_scores:        dict[str, dict[str, float]],
    normalized_scores: dict[str, dict[str, float]],
    weights:           dict[str, float],
    scored_alternatives: list[AlternativeScore],
) -> DecisionMatrix:
    alt_ids   = [a.alternative_id for a in alternatives]
    crit_ids  = [c.criterion_id   for c in criteria]
    composite = {a.alternative_id: a.composite_score for a in scored_alternatives}
    return DecisionMatrix(
        alternative_ids   = alt_ids,
        criterion_ids     = crit_ids,
        raw_scores        = raw_scores,
        normalized_scores = normalized_scores,
        weights           = weights,
        composite_scores  = composite,
    )
