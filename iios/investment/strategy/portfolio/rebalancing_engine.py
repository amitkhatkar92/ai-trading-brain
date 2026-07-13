"""iios/investment/strategy/portfolio/rebalancing_engine.py
RebalancingEngine — evaluates triggers and applies new weights to a portfolio.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.investment.strategy.portfolio.portfolio_strategy import PortfolioStrategy
from iios.investment.strategy.portfolio.strategy_portfolio import (
    StrategyPortfolio, PortfolioState
)
from iios.investment.strategy.portfolio.strategy_allocation import AllocationStatus
from iios.investment.strategy.portfolio.construction_constraints import (
    ConstructionConstraints, DEFAULT_CONSTRAINTS
)
from iios.investment.strategy.portfolio.weight_optimizer import WeightOptimizer
from iios.investment.strategy.portfolio.rebalance_policy import (
    RebalancePolicy, DEFAULT_POLICY
)
from iios.investment.strategy.portfolio.rebalance_scheduler import (
    RebalanceScheduler, RebalanceDecision
)
from iios.investment.strategy.portfolio.rebalance_history import (
    RebalanceHistory, RebalanceStatus
)
from iios.investment.strategy.portfolio.portfolio_lifecycle import PortfolioLifecycle


@dataclass(frozen=True)
class RebalanceResult:
    portfolio_id:  str
    rebalanced:    bool
    decision:      RebalanceDecision
    weight_before: Dict[str, float]
    weight_after:  Dict[str, float]
    max_drift:     float
    warnings:      List[str]
    executed_at:   datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "portfolio_id": self.portfolio_id,
            "rebalanced":   self.rebalanced,
            "triggers":     self.decision.triggers,
            "max_drift":    round(self.max_drift, 6),
            "warnings":     self.warnings,
            "executed_at":  self.executed_at.isoformat(),
        }


class RebalancingEngine:
    """
    Orchestrates the rebalancing workflow:
      1. Check if rebalancing is due (RebalanceScheduler)
      2. Compute new target weights (WeightOptimizer)
      3. Apply new weights to portfolio allocations
      4. Record in RebalanceHistory
      5. Transition portfolio state via PortfolioLifecycle
    """

    def __init__(
        self,
        lifecycle:   Optional[PortfolioLifecycle] = None,
        optimizer:   Optional[WeightOptimizer] = None,
        history:     Optional[RebalanceHistory] = None,
    ) -> None:
        self._lifecycle = lifecycle or PortfolioLifecycle()
        self._optimizer = optimizer or WeightOptimizer()
        self._history   = history   or RebalanceHistory()
        self._scheduler = RebalanceScheduler(self._history)

    def rebalance(
        self,
        portfolio:     StrategyPortfolio,
        strategies:    List[PortfolioStrategy],  # updated strategy data
        policy:        RebalancePolicy = DEFAULT_POLICY,
        constraints:   ConstructionConstraints = DEFAULT_CONSTRAINTS,
        force:         bool = False,
    ) -> RebalanceResult:
        """
        Evaluate triggers and, if due (or forced), apply new weights.
        Raises ValueError if portfolio is ARCHIVED or PAUSED.
        """
        if portfolio.state in (PortfolioState.ARCHIVED, PortfolioState.PAUSED):
            raise ValueError(
                f"Cannot rebalance portfolio in state {portfolio.state.value}"
            )

        decision = self._scheduler.is_due(portfolio, policy)
        if not decision.is_due and not force:
            return RebalanceResult(
                portfolio_id=portfolio.portfolio_id,
                rebalanced=False,
                decision=decision,
                weight_before={},
                weight_after={},
                max_drift=portfolio.max_drift,
                warnings=["Rebalancing not due"],
            )

        # Capture weights before
        active = portfolio.active_allocations()
        weight_before = {a.strategy_id: a.weight for a in active}

        # Filter strategies to those in the portfolio
        active_ids  = {a.strategy_id for a in active}
        active_strats = [s for s in strategies if s.strategy_id in active_ids and s.is_eligible]

        if not active_strats:
            return RebalanceResult(
                portfolio_id=portfolio.portfolio_id,
                rebalanced=False,
                decision=decision,
                weight_before=weight_before,
                weight_after={},
                max_drift=portfolio.max_drift,
                warnings=["No eligible strategies found for rebalancing"],
            )

        # Compute new weights
        method = portfolio.allocations[active_strats[0].strategy_id].allocation_method
        new_weights = self._optimizer.compute(active_strats, method, constraints)

        # Apply
        now = datetime.now(timezone.utc)
        for sid, w in new_weights.items():
            if sid in portfolio.allocations:
                portfolio.allocations[sid].weight = w
                portfolio.allocations[sid].target_weight = w
                portfolio.allocations[sid].updated_at = now

        # Record
        triggers = decision.triggers[0] if decision.triggers else "manual"
        self._history.record(
            portfolio_id=portfolio.portfolio_id,
            trigger=triggers,
            weight_before=weight_before,
            weight_after=new_weights,
            max_drift=portfolio.max_drift,
            reason=decision.reason,
            status=RebalanceStatus.EXECUTED,
        )

        # Lifecycle transition
        self._lifecycle.mark_rebalanced(portfolio, reason=decision.reason)

        return RebalanceResult(
            portfolio_id=portfolio.portfolio_id,
            rebalanced=True,
            decision=decision,
            weight_before=weight_before,
            weight_after=new_weights,
            max_drift=portfolio.max_drift,
            warnings=[],
        )
