"""
portfolio_solution_selector.py — iios.portfolio.optimization
=============================================================
Selects the optimal portfolio solution from a ranked list.

C10 Portfolio Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

from typing import List, Optional

from .portfolio_solution import PortfolioSolution


class PortfolioSolutionSelector:
    """
    Selects the top-ranked feasible portfolio solution.

    If no feasible solution exists, returns None — the caller is
    responsible for raising PortfolioOptimizationSolutionError.
    """

    def select(
        self, ranked_solutions: List[PortfolioSolution]
    ) -> Optional[PortfolioSolution]:
        """
        Return the best feasible solution, or None if none exist.

        The list is expected to be pre-ranked (rank 1 = best) by the
        ranking and priority engines.  This method returns the first
        feasible solution it encounters.

        Side effect: sets ``is_selected = True`` on the returned object.
        """
        for solution in ranked_solutions:
            if solution.is_feasible:
                solution.is_selected = True
                return solution
        return None
