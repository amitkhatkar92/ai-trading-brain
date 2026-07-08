"""iios/decision_optimization/objectives/objective_result.py"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field

from ..optimization_constants import ObjectiveAggregation, ObjectiveType
from ..optimization_context import Candidate
from .objective import Objective


@dataclass
class ObjectiveScore:
    objective_id:    str
    objective_name:  str
    candidate_id:    str
    raw_score:       float = 0.0
    effective_score: float = 0.0    # direction-adjusted: higher = better
    weight:          float = 1.0
    weighted_score:  float = 0.0

    def to_dict(self) -> dict:
        return {
            "objective_id":   self.objective_id,
            "candidate_id":   self.candidate_id,
            "raw_score":      self.raw_score,
            "effective_score": self.effective_score,
            "weight":         self.weight,
            "weighted_score": self.weighted_score,
        }


@dataclass
class ObjectiveResult:
    result_id:        str  = field(default_factory=lambda: str(uuid.uuid4()))
    objective_count:  int  = 0
    candidate_count:  int  = 0
    scores:           dict[str, dict[str, float]] = field(default_factory=dict)
    composite_scores: dict[str, float]            = field(default_factory=dict)
    aggregation:      ObjectiveAggregation = ObjectiveAggregation.WEIGHTED_SUM
    generated_at:     float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "result_id":        self.result_id,
            "objective_count":  self.objective_count,
            "candidate_count":  self.candidate_count,
            "composite_scores": self.composite_scores,
            "aggregation":      self.aggregation.value,
        }


def build_objective_result(
    candidates:  list[Candidate],
    objectives:  list[Objective],
    aggregation: ObjectiveAggregation = ObjectiveAggregation.WEIGHTED_SUM,
) -> ObjectiveResult:
    scores:    dict[str, dict[str, float]] = {}
    composite: dict[str, float]            = {}

    total_w = sum(o.weight for o in objectives) or 1.0

    for cand in candidates:
        obj_scores: dict[str, float] = {}
        weighted_total = 0.0

        for obj in objectives:
            try:
                raw  = obj.evaluate(cand)
                eff  = obj.effective_score(cand)
            except Exception:  # noqa: BLE001
                raw  = 0.0
                eff  = 0.0
            obj_scores[obj.objective_id] = eff
            weighted_total += eff * obj.weight

        scores[cand.candidate_id]    = obj_scores
        composite[cand.candidate_id] = weighted_total / total_w if objectives else 0.0

    return ObjectiveResult(
        objective_count  = len(objectives),
        candidate_count  = len(candidates),
        scores           = scores,
        composite_scores = composite,
        aggregation      = aggregation,
    )
