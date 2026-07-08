"""iios/decision_evaluation/tradeoff/tradeoff_analyzer.py"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field

from ..scoring.score_calculator import AlternativeScore


@dataclass
class TradeoffPair:
    criterion_a: str
    criterion_b: str
    label:       str = ""

    def key(self) -> str:
        return f"{self.criterion_a}:{self.criterion_b}"

    def to_dict(self) -> dict:
        return {"criterion_a": self.criterion_a, "criterion_b": self.criterion_b, "label": self.label}


@dataclass
class TradeoffPoint:
    alternative_id:   str
    alternative_name: str
    score_a:          float
    score_b:          float
    is_pareto:        bool = False

    def to_dict(self) -> dict:
        return {
            "alternative_id":   self.alternative_id,
            "alternative_name": self.alternative_name,
            "score_a":          self.score_a,
            "score_b":          self.score_b,
            "is_pareto":        self.is_pareto,
        }


@dataclass
class TradeoffAnalysis:
    analysis_id:     str = field(default_factory=lambda: str(uuid.uuid4()))
    pairs:           list[TradeoffPair] = field(default_factory=list)
    points:          dict[str, list[TradeoffPoint]] = field(default_factory=dict)
    pareto_frontier: list[str] = field(default_factory=list)
    dominated:       list[str] = field(default_factory=list)
    generated_at:    float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "analysis_id":     self.analysis_id,
            "pair_count":      len(self.pairs),
            "pareto_frontier": self.pareto_frontier,
            "dominated":       self.dominated,
            "generated_at":    self.generated_at,
        }


class TradeoffAnalyzer:
    """Computes trade-off curves and Pareto frontiers."""

    def analyze(
        self,
        alternatives: list[AlternativeScore],
        pairs:        list[TradeoffPair],
    ) -> TradeoffAnalysis:
        if not alternatives:
            return TradeoffAnalysis(pairs=pairs)

        pareto = self.compute_pareto_frontier(alternatives)
        dominated = [a.alternative_id for a in alternatives
                     if a.alternative_id not in pareto]

        points: dict[str, list[TradeoffPoint]] = {}
        for pair in pairs:
            pts: list[TradeoffPoint] = []
            for alt in alternatives:
                sa = _get_norm_score(alt, pair.criterion_a)
                sb = _get_norm_score(alt, pair.criterion_b)
                pts.append(TradeoffPoint(
                    alternative_id   = alt.alternative_id,
                    alternative_name = alt.alternative_name,
                    score_a          = sa,
                    score_b          = sb,
                    is_pareto        = alt.alternative_id in pareto,
                ))
            points[pair.key()] = pts

        return TradeoffAnalysis(
            pairs           = list(pairs),
            points          = points,
            pareto_frontier = pareto,
            dominated       = dominated,
        )

    def compute_pareto_frontier(self, alternatives: list[AlternativeScore]) -> list[str]:
        """
        Returns alt_ids that are not dominated by any other alternative.
        A dominates B iff A.normalized >= B.normalized for all criteria AND
        A.normalized > B.normalized for at least one.
        """
        if not alternatives:
            return []

        frontier: list[str] = []
        for candidate in alternatives:
            dominated = False
            for other in alternatives:
                if other.alternative_id == candidate.alternative_id:
                    continue
                if _dominates(other, candidate):
                    dominated = True
                    break
            if not dominated:
                frontier.append(candidate.alternative_id)
        return frontier


def _get_norm_score(alt: AlternativeScore, criterion_id: str) -> float:
    for cs in alt.criterion_scores:
        if cs.criterion_id == criterion_id:
            return cs.normalized_score
    return alt.composite_score


def _dominates(a: AlternativeScore, b: AlternativeScore) -> bool:
    """Return True if a dominates b across all shared criteria."""
    a_scores = {cs.criterion_id: cs.normalized_score for cs in a.criterion_scores}
    b_scores = {cs.criterion_id: cs.normalized_score for cs in b.criterion_scores}
    shared   = set(a_scores) & set(b_scores)
    if not shared:
        return False
    at_least  = all(a_scores[cid] >= b_scores[cid] for cid in shared)
    strictly  = any(a_scores[cid] >  b_scores[cid] for cid in shared)
    return at_least and strictly
