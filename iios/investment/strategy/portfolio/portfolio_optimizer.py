"""iios/investment/strategy/portfolio/portfolio_optimizer.py
PortfolioOptimizer — public facade for portfolio optimization.
"""
from __future__ import annotations

from typing import Optional

from iios.investment.strategy.portfolio.strategy_portfolio import (
    StrategyPortfolio, PortfolioState
)
from iios.investment.strategy.portfolio.construction_constraints import (
    ConstructionConstraints, DEFAULT_CONSTRAINTS
)
from iios.investment.strategy.portfolio.constraint_solver import ConstraintSolver
from iios.investment.strategy.portfolio.optimization_engine import (
    OptimizationEngine, OptimizationResult
)


class PortfolioOptimizer:
    """
    Applies ConstraintSolver-backed optimization to a StrategyPortfolio.
    Transitions the portfolio state to OPTIMIZED on success.
    """

    def __init__(
        self,
        engine: Optional[OptimizationEngine] = None,
    ) -> None:
        self._engine = engine or OptimizationEngine()

    def optimize(
        self,
        portfolio:   StrategyPortfolio,
        constraints: ConstructionConstraints = DEFAULT_CONSTRAINTS,
    ) -> OptimizationResult:
        """
        Optimise portfolio weights and transition state to OPTIMIZED.
        Raises ValueError if portfolio is in ARCHIVED state.
        """
        if portfolio.state == PortfolioState.ARCHIVED:
            raise ValueError("Cannot optimise an archived portfolio")

        result = self._engine.optimize(portfolio, constraints)

        if result.is_valid and portfolio.can_transition_to(PortfolioState.OPTIMIZED):
            portfolio.apply_transition(PortfolioState.OPTIMIZED, reason="optimization completed")

        return result
