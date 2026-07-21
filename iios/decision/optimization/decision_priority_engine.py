"""
decision_priority_engine.py — iios.decision.optimization
=========================================================
Priority-based candidate ordering independent of objective scoring.

Used by PRIORITY_BASED strategy and as a tie-breaker.

C9 Decision Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

from typing import List

from .decision_candidate import DecisionCandidate
from .decision_optimization_context import DecisionOptimizationContext


class DecisionPriorityEngine:
    """
    Ranks candidates by intrinsic priority (confidence × expected_return)
    without objective weighting.

    Priority score = ``confidence × max(expected_return, 0)``.
    Ties are broken by ``candidate_id`` for determinism.
    """

    def prioritize(
        self,
        candidates: List[DecisionCandidate],
        context:    DecisionOptimizationContext,
    ) -> List[DecisionCandidate]:
        """
        Return candidates sorted from highest to lowest priority.
        """
        def priority_score(c: DecisionCandidate) -> tuple:
            score = c.confidence * max(c.expected_return, 0.0)
            return (-score, c.candidate_id)

        return sorted(candidates, key=priority_score)

    def top_priority(
        self,
        candidates: List[DecisionCandidate],
        context:    DecisionOptimizationContext,
    ) -> DecisionCandidate:
        """Return the highest-priority candidate."""
        if not candidates:
            raise ValueError("Cannot select from empty candidate list")
        ranked = self.prioritize(candidates, context)
        return ranked[0]
