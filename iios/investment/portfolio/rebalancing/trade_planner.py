"""iios/investment/portfolio/rebalancing/trade_planner.py

Trade planner: generates a complete trade plan from position changes.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from iios.investment.portfolio.rebalancing.execution_estimator import (
    ExecutionEstimate, ExecutionEstimator,
)
from iios.investment.portfolio.rebalancing.position_changes import (
    PositionChange, compute_position_changes,
)
from iios.investment.portfolio.rebalancing.rebalance_policy import RebalancePolicy
from iios.investment.portfolio.rebalancing.rebalancing_types import (
    MAX_TURNOVER_SINGLE_REBAL, CurrentPosition, DriftLevel,
    RebalanceTrigger, TargetPosition, TradePriority, TradeSide, now_utc,
)
from iios.investment.portfolio.rebalancing.trade_priority import prioritize_trades


@dataclass(frozen=True)
class TradePlan:
    """Complete trade plan for a single portfolio rebalancing."""

    plan_id:            str   = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:       str   = ""
    created_at:         str   = field(default_factory=now_utc)

    # Trades (sorted by priority)
    changes:            tuple = field(default_factory=tuple)   # PositionChange
    n_buys:             int   = 0
    n_sells:            int   = 0
    n_holds:            int   = 0

    # Turnover
    total_turnover:     float = 0.0   # Σ abs(weight_change) / 2
    buy_turnover:       float = 0.0
    sell_turnover:      float = 0.0
    exceeds_max_turn:   bool  = False

    # Cost estimate
    execution_estimate: Optional[ExecutionEstimate] = None

    # Key priorities
    overall_priority:   TradePriority = TradePriority.MEDIUM
    has_immediate:      bool  = False
    has_urgent:         bool  = False

    # Summary
    buys:               tuple = field(default_factory=tuple)    # symbols to buy
    sells:              tuple = field(default_factory=tuple)    # symbols to sell
    exits:              tuple = field(default_factory=tuple)    # full exits
    new_positions:      tuple = field(default_factory=tuple)    # new entries

    def to_dict(self) -> Dict[str, Any]:
        return {
            "n_buys":            self.n_buys,
            "n_sells":           self.n_sells,
            "total_turnover":    round(self.total_turnover, 4),
            "exceeds_max_turn":  self.exceeds_max_turn,
            "overall_priority":  self.overall_priority.value,
            "has_immediate":     self.has_immediate,
            "buys":              list(self.buys),
            "sells":             list(self.sells),
            "cost": self.execution_estimate.to_dict() if self.execution_estimate else {},
        }


class TradePlanner:
    """Generates a prioritized trade plan from current and target positions."""

    def __init__(
        self,
        estimator: Optional[ExecutionEstimator] = None,
    ) -> None:
        self._estimator = estimator or ExecutionEstimator()

    def plan(
        self,
        current:          List[CurrentPosition],
        target:           List[TargetPosition],
        policy:           RebalancePolicy,
        portfolio_id:     str   = "",
        portfolio_value:  float = 0.0,
    ) -> TradePlan:
        """
        Generate a complete, prioritized trade plan.
        """
        # 1. Compute required changes
        raw_changes = compute_position_changes(
            current, target, policy.parameters.min_trade_size
        )

        if not raw_changes:
            return TradePlan(
                portfolio_id = portfolio_id,
                overall_priority = TradePriority.LOW,
            )

        # 2. Prioritize
        ordered_changes = prioritize_trades(raw_changes, policy)

        # 3. Estimate execution costs
        est = self._estimator.estimate(ordered_changes, portfolio_value)

        # 4. Aggregate turnover
        buy_turn  = sum(c.abs_change for c in ordered_changes if c.trade_side == TradeSide.BUY)
        sell_turn = sum(c.abs_change for c in ordered_changes if c.trade_side == TradeSide.SELL)
        total_turn = (buy_turn + sell_turn) / 2.0

        # 5. Priority summary
        from iios.investment.portfolio.rebalancing.trade_priority import _PRIORITY_ORDER
        max_prio = max(ordered_changes, key=lambda c: _PRIORITY_ORDER[c.priority]).priority
        has_imm  = any(c.priority == TradePriority.IMMEDIATE for c in ordered_changes)
        has_urg  = any(c.priority == TradePriority.URGENT    for c in ordered_changes)

        buys  = tuple(c.symbol for c in ordered_changes if c.trade_side == TradeSide.BUY)
        sells = tuple(c.symbol for c in ordered_changes if c.trade_side == TradeSide.SELL)
        exits = tuple(c.symbol for c in ordered_changes if c.is_full_exit)
        newps = tuple(c.symbol for c in ordered_changes if c.is_new_position)

        return TradePlan(
            portfolio_id       = portfolio_id,
            changes            = tuple(ordered_changes),
            n_buys             = sum(1 for c in ordered_changes if c.trade_side == TradeSide.BUY),
            n_sells            = sum(1 for c in ordered_changes if c.trade_side == TradeSide.SELL),
            total_turnover     = round(total_turn, 4),
            buy_turnover       = round(buy_turn / 2.0, 4),
            sell_turnover      = round(sell_turn / 2.0, 4),
            exceeds_max_turn   = total_turn > MAX_TURNOVER_SINGLE_REBAL,
            execution_estimate = est,
            overall_priority   = max_prio,
            has_immediate      = has_imm,
            has_urgent         = has_urg,
            buys               = buys,
            sells              = sells,
            exits              = exits,
            new_positions      = newps,
        )
