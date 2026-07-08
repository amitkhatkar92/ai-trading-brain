"""
iios/decisions/evaluation/decision_ranker.py
============================================
DecisionRanker — sorts evaluated candidates and assigns ranks.
"""
from __future__ import annotations

from ..decision_constants import CandidateStatus
from ..models.decision_candidate import DecisionCandidate


class DecisionRanker:
    """
    Sorts a list of evaluated DecisionCandidates by composite_score
    (descending) and assigns integer ranks starting at 1.

    Candidates with policy failures are placed below passing candidates
    regardless of score.
    """

    def rank(
        self,
        candidates: list[DecisionCandidate],
        descending: bool = True,
    ) -> list[DecisionCandidate]:
        """
        Return a new list with ``rank`` populated.
        Does NOT mutate the original list order.
        """
        if not candidates:
            return []

        # Separate passing from failing
        passing = [c for c in candidates if not c.has_policy_failure]
        failing = [c for c in candidates if c.has_policy_failure]

        # Sort each group by composite_score
        passing.sort(key=lambda c: c.composite_score, reverse=descending)
        failing.sort(key=lambda c: c.composite_score, reverse=descending)

        ranked = passing + failing
        for i, c in enumerate(ranked, start=1):
            c.rank = i

        return ranked

    def select_best(
        self,
        ranked_candidates: list[DecisionCandidate],
    ) -> DecisionCandidate | None:
        """Return the top-ranked candidate that passed all policies, or None."""
        for c in ranked_candidates:
            if not c.has_policy_failure:
                c.selected = True
                c.status   = CandidateStatus.SELECTED
                return c
        return None
