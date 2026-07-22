"""
portfolio_ranking_engine.py — iios.portfolio.optimization
==========================================================
Ranks a list of PortfolioSolution objects.

Ranking rule: feasible solutions always rank above infeasible ones;
within each group, solutions are sorted by score descending.

C10 Portfolio Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

from typing import List

from .portfolio_solution import PortfolioSolution


class PortfolioRankingEngine:
    """
    Assigns ranks to portfolio solutions.

    Rule
    ----
    1. Feasible solutions (``is_feasible=True``) before infeasible ones.
    2. Within each group, higher score comes first.
    3. Ranks are 1-based (rank 1 = best).
    4. Returns a *new* list of PortfolioSolution objects with ``rank``
       mutated in-place (PortfolioSolution is mutable).
    """

    def rank(self, solutions: List[PortfolioSolution]) -> List[PortfolioSolution]:
        """
        Rank *solutions* and return the ordered list.

        The returned list contains the same PortfolioSolution objects
        with their ``rank`` field updated.
        """
        feasible   = sorted(
            [s for s in solutions if s.is_feasible],
            key=lambda s: s.score, reverse=True,
        )
        infeasible = sorted(
            [s for s in solutions if not s.is_feasible],
            key=lambda s: s.score, reverse=True,
        )

        ordered = feasible + infeasible
        for i, solution in enumerate(ordered, start=1):
            solution.rank = i

        return ordered
