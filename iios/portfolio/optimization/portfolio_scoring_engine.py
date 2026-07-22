"""
portfolio_scoring_engine.py — iios.portfolio.optimization
==========================================================
Produces a composite score in [0.0, 1.0] for a portfolio candidate
by aggregating objective results using the strategy's scoring method.

Hard constraint violations override the score to 0.0.

C10 Portfolio Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

from typing import Any, Dict, List

from .constants import ScoringMethod
from .portfolio_candidate import PortfolioCandidate
from .portfolio_constraint import ConstraintResult
from .portfolio_objective import ObjectiveResult, PortfolioObjective


class PortfolioScoringEngine:
    """
    Aggregates objective scores into a single portfolio score.

    Scoring methods
    ---------------
    WEIGHTED :   Weighted sum normalised by total weight.
    NORMALIZED : Equal-weight average of all objective scores.
    COMPOSITE :  Weighted sum with soft-constraint penalty deductions.
    PARETO :     Minimum score across all objectives (Pareto dominance proxy).
    """

    def score(
        self,
        candidate:          PortfolioCandidate,
        objectives:         List[PortfolioObjective],
        constraint_results: List[ConstraintResult],
        inputs:             Dict[str, Any],
        method:             ScoringMethod = ScoringMethod.WEIGHTED,
    ) -> float:
        """
        Return a composite score in [0.0, 1.0] for *candidate*.

        Returns 0.0 immediately if any hard constraint is violated.
        """
        # Hard-constraint veto
        for cr in constraint_results:
            if not cr.satisfied and cr.is_hard:
                return 0.0

        if not objectives:
            return 0.5  # no objectives → neutral score

        # Evaluate all objectives
        results: List[ObjectiveResult] = [
            obj.score(candidate, inputs) for obj in objectives
        ]

        base = self._aggregate(results, method)

        # Apply soft-constraint penalties (COMPOSITE & WEIGHTED)
        if method in (ScoringMethod.COMPOSITE, ScoringMethod.WEIGHTED):
            for cr in constraint_results:
                if not cr.satisfied and not cr.is_hard:
                    base *= max(0.0, 1.0 - cr.penalty)

        return max(0.0, min(1.0, base))

    def objective_results(
        self,
        candidate:  PortfolioCandidate,
        objectives: List[PortfolioObjective],
        inputs:     Dict[str, Any],
    ) -> List[ObjectiveResult]:
        """Return raw ObjectiveResult objects for each objective."""
        return [obj.score(candidate, inputs) for obj in objectives]

    # ------------------------------------------------------------------
    # Private aggregators
    # ------------------------------------------------------------------

    def _aggregate(self, results: List[ObjectiveResult], method: ScoringMethod) -> float:
        if method == ScoringMethod.WEIGHTED:
            total_w = sum(r.weight for r in results)
            if total_w == 0:
                return 0.0
            return sum(r.score * r.weight for r in results) / total_w

        if method == ScoringMethod.NORMALIZED:
            return sum(r.score for r in results) / len(results)

        if method == ScoringMethod.COMPOSITE:
            total_w = sum(r.weight for r in results)
            if total_w == 0:
                return 0.0
            return sum(r.score * r.weight for r in results) / total_w

        if method == ScoringMethod.PARETO:
            return min(r.score for r in results)

        # Default: weighted
        total_w = sum(r.weight for r in results)
        if total_w == 0:
            return 0.0
        return sum(r.score * r.weight for r in results) / total_w
