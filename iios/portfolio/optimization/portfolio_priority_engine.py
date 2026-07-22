"""
portfolio_priority_engine.py — iios.portfolio.optimization
===========================================================
Applies tie-breaking and confidence-adjustment rules to an already-
ranked list of PortfolioSolution objects.

C10 Portfolio Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

from typing import List

from .portfolio_solution import PortfolioSolution

# Score margin within which two solutions are considered "tied"
_TIE_MARGIN: float = 1e-6


class PortfolioPriorityEngine:
    """
    Post-ranking priority adjustor.

    Applies tie-breaking rules when two adjacent solutions have
    identical scores.  Current rules (applied in order):

    1. Feasible beats infeasible (already guaranteed by the ranking
       engine, but preserved here as a safety net).
    2. Within a tie, the solution with fewer constraint violations wins.
    3. Within a tie, the solution with a higher ``objectives_evaluated``
       count wins (more objectives evaluated → more confident).
    4. Stable fallback: preserve the existing rank order.

    ``rank`` values are reassigned after tie-breaking.
    """

    def apply_priority(
        self, ranked_solutions: List[PortfolioSolution]
    ) -> List[PortfolioSolution]:
        """
        Apply priority rules to *ranked_solutions*.

        Returns the same objects (possibly reordered) with updated ranks.
        """
        if len(ranked_solutions) <= 1:
            return ranked_solutions

        reordered = list(ranked_solutions)

        # Simple insertion-based sort using priority key (stable)
        reordered.sort(key=self._priority_key, reverse=True)

        for i, solution in enumerate(reordered, start=1):
            solution.rank = i

        return reordered

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _priority_key(s: PortfolioSolution):
        """
        Composite sort key — higher is better.

        Tuple ordering (Python sorts tuples lexicographically):
          (is_feasible, score, -constraints_violated, objectives_evaluated)
        """
        return (
            int(s.is_feasible),
            s.score,
            -s.constraints_violated,
            s.objectives_evaluated,
        )
