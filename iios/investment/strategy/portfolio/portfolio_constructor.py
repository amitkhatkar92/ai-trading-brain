"""iios/investment/strategy/portfolio/portfolio_constructor.py
PortfolioConstructor — facade that creates StrategyPortfolio objects.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.investment.strategy.portfolio.portfolio_strategy import PortfolioStrategy
from iios.investment.strategy.portfolio.strategy_portfolio import (
    StrategyPortfolio, PortfolioType, PortfolioState
)
from iios.investment.strategy.portfolio.strategy_allocation import AllocationMethod
from iios.investment.strategy.portfolio.construction_constraints import (
    ConstructionConstraints, DEFAULT_CONSTRAINTS
)
from iios.investment.strategy.portfolio.allocation_engine import (
    AllocationEngine, AllocationResult
)
from iios.investment.strategy.portfolio.weight_optimizer import WeightOptimizer


_TYPE_TO_METHOD: Dict[PortfolioType, AllocationMethod] = {
    PortfolioType.EQUAL_WEIGHT:       AllocationMethod.EQUAL_WEIGHT,
    PortfolioType.RISK_PARITY:        AllocationMethod.RISK_PARITY,
    PortfolioType.PERFORMANCE_WEIGHT: AllocationMethod.PERFORMANCE_WEIGHT,
    PortfolioType.CONFIDENCE_WEIGHT:  AllocationMethod.CONFIDENCE_WEIGHT,
    PortfolioType.VOLATILITY_WEIGHT:  AllocationMethod.VOLATILITY_WEIGHT,
    PortfolioType.COMPOSITE_WEIGHT:   AllocationMethod.COMPOSITE_WEIGHT,
    PortfolioType.HIERARCHICAL:       AllocationMethod.COMPOSITE_WEIGHT,
    PortfolioType.CUSTOM:             AllocationMethod.EQUAL_WEIGHT,
}


class PortfolioConstructionError(Exception):
    """Raised when a portfolio cannot be constructed under given constraints."""


class PortfolioConstructor:
    """
    Facade for portfolio construction.
    build() → StrategyPortfolio ready for optimization.
    """

    def __init__(
        self,
        allocation_engine: Optional[AllocationEngine] = None,
    ) -> None:
        self._engine = allocation_engine or AllocationEngine()

    def build(
        self,
        strategies:       List[PortfolioStrategy],
        portfolio_type:   PortfolioType = PortfolioType.COMPOSITE_WEIGHT,
        constraints:      ConstructionConstraints = DEFAULT_CONSTRAINTS,
        portfolio_name:   str = "",
        total_capital:    float = 0.0,
        portfolio_id:     Optional[str] = None,
        metadata:         Optional[Dict[str, Any]] = None,
        method_override:  Optional[AllocationMethod] = None,
    ) -> StrategyPortfolio:
        """
        Build a StrategyPortfolio from a list of PortfolioStrategy inputs.
        Raises PortfolioConstructionError if eligibility or count constraints fail.
        """
        method = method_override or _TYPE_TO_METHOD.get(
            portfolio_type, AllocationMethod.COMPOSITE_WEIGHT
        )

        result: AllocationResult = self._engine.allocate(strategies, method, constraints)

        if result.strategy_count < constraints.min_strategies:
            raise PortfolioConstructionError(
                f"Insufficient eligible strategies: {result.strategy_count} "
                f"(minimum {constraints.min_strategies}). "
                f"Rejected: {result.rejected_ids}"
            )

        pid  = portfolio_id or str(uuid.uuid4())
        name = portfolio_name or f"Portfolio-{pid[:8]}"

        portfolio = StrategyPortfolio(
            portfolio_id=pid,
            portfolio_name=name,
            portfolio_type=portfolio_type,
            state=PortfolioState.CREATED,
            total_capital=total_capital,
            version=1,
            allocations=result.allocations,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            metadata=metadata or {},
        )
        return portfolio
