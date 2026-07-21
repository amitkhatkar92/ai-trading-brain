"""
decision_ranking_engine.py — iios.decision.optimization
=========================================================
DecisionRanking      — ranked position for one candidate.
DecisionRankingEngine — ranks all candidates by score.

C9 Decision Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from .decision_candidate import CandidateScore


@dataclass(frozen=True)
class DecisionRanking:
    """
    Ranked position for a single candidate.

    Parameters
    ----------
    rank :                     1-based position (1 = best).
    candidate_id :             Candidate this ranking belongs to.
    final_score :              Score used for primary ranking.
    confidence_adjusted_score: Score adjusted for candidate confidence.
    is_feasible :              Whether all hard constraints are satisfied.
    is_optimal :               ``True`` for rank 1 (best feasible candidate).
    """

    rank:                      int
    candidate_id:              str
    final_score:               float
    confidence_adjusted_score: float
    is_feasible:               bool
    is_optimal:                bool


class DecisionRankingEngine:
    """
    Ranks :class:`DecisionCandidate` objects by their
    :class:`CandidateScore`.

    Ranking rules
    -------------
    1. Feasible candidates always rank above infeasible ones.
    2. Within the feasible tier, rank by ``confidence_adjusted_score`` desc.
    3. Within the infeasible tier, rank by ``final_score`` desc.
    4. Ties are broken by ``candidate_id`` (deterministic).
    """

    def rank(
        self,
        scores: List[CandidateScore],
    ) -> List[DecisionRanking]:
        """
        Return a ranked list of :class:`DecisionRanking` objects,
        ordered from best (rank=1) to worst.
        """
        if not scores:
            return []

        feasible   = [s for s in scores if s.is_feasible]
        infeasible = [s for s in scores if not s.is_feasible]

        def sort_key(s: CandidateScore):
            return (-s.confidence_adjusted_score, -s.final_score, s.candidate_id)

        feasible.sort(key=sort_key)
        infeasible.sort(key=sort_key)

        ordered = feasible + infeasible
        rankings: List[DecisionRanking] = []

        for pos, score in enumerate(ordered, start=1):
            rankings.append(DecisionRanking(
                rank                      = pos,
                candidate_id              = score.candidate_id,
                final_score               = score.final_score,
                confidence_adjusted_score = score.confidence_adjusted_score,
                is_feasible               = score.is_feasible,
                is_optimal                = (pos == 1 and score.is_feasible),
            ))

        return rankings

    def best_feasible(
        self, rankings: List[DecisionRanking]
    ) -> Optional[DecisionRanking]:
        """Return the rank-1 feasible ranking, or ``None`` if none exist."""
        for r in rankings:
            if r.is_feasible:
                return r
        return None
