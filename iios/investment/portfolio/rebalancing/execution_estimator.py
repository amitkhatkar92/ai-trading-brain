"""iios/investment/portfolio/rebalancing/execution_estimator.py

Transaction cost and market impact estimation.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List

from iios.investment.portfolio.rebalancing.position_changes import PositionChange
from iios.investment.portfolio.rebalancing.rebalancing_types import (
    MARKET_IMPACT_FACTOR, MARKET_IMPACT_THRESHOLD,
    TRANSACTION_COST_EQUITY, TRANSACTION_COST_BOND, TRANSACTION_COST_FIXED_INR,
    TradeSide,
)


@dataclass(frozen=True)
class TradeEstimate:
    """Cost / impact estimate for a single trade."""

    symbol:              str
    abs_change:          float = 0.0
    trade_side:          TradeSide = TradeSide.BUY

    transaction_cost_pct:float = 0.0   # fraction of portfolio value
    market_impact_pct:   float = 0.0   # price slippage cost
    tax_cost_pct:        float = 0.0   # estimated tax (from PositionChange)
    total_cost_pct:      float = 0.0   # sum of all costs

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol":               self.symbol,
            "transaction_cost_pct": round(self.transaction_cost_pct, 5),
            "market_impact_pct":    round(self.market_impact_pct, 5),
            "tax_cost_pct":         round(self.tax_cost_pct, 5),
            "total_cost_pct":       round(self.total_cost_pct, 5),
        }


@dataclass(frozen=True)
class ExecutionEstimate:
    """Aggregate cost estimates for all trades in a rebalancing plan."""

    result_id:              str   = field(default_factory=lambda: str(uuid.uuid4()))

    total_transaction_cost: float = 0.0   # as fraction of portfolio value
    total_market_impact:    float = 0.0
    total_tax_cost:         float = 0.0
    total_cost_pct:         float = 0.0   # total all-in cost

    # Turnover metrics
    total_turnover:         float = 0.0   # Σ abs(weight_change) / 2
    n_trades:               int   = 0
    n_buys:                 int   = 0
    n_sells:                int   = 0

    trade_estimates:        tuple = field(default_factory=tuple)  # TradeEstimate

    # Cost in portfolio value terms (if portfolio_value provided)
    portfolio_value:        float = 0.0
    total_cost_inr:         float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_transaction_cost": round(self.total_transaction_cost, 5),
            "total_market_impact":    round(self.total_market_impact, 5),
            "total_tax_cost":         round(self.total_tax_cost, 5),
            "total_cost_pct":         round(self.total_cost_pct, 5),
            "total_turnover":         round(self.total_turnover, 4),
            "n_trades":               self.n_trades,
        }


class ExecutionEstimator:
    """
    Estimates transaction costs, market impact, and tax costs for
    a list of position changes.
    """

    def __init__(
        self,
        equity_cost_rate: float = TRANSACTION_COST_EQUITY,
        bond_cost_rate:   float = TRANSACTION_COST_BOND,
        impact_factor:    float = MARKET_IMPACT_FACTOR,
        impact_threshold: float = MARKET_IMPACT_THRESHOLD,
    ) -> None:
        self._equity_rate = equity_cost_rate
        self._bond_rate   = bond_cost_rate
        self._impact_fac  = impact_factor
        self._impact_thr  = impact_threshold

    def estimate(
        self,
        changes:          List[PositionChange],
        portfolio_value:  float = 0.0,
    ) -> ExecutionEstimate:
        if not changes:
            return ExecutionEstimate()

        trade_ests: List[TradeEstimate] = []
        for c in changes:
            est = self._estimate_trade(c)
            trade_ests.append(est)

        total_tc  = sum(e.transaction_cost_pct for e in trade_ests)
        total_mi  = sum(e.market_impact_pct    for e in trade_ests)
        total_tax = sum(e.tax_cost_pct          for e in trade_ests)
        total_all = total_tc + total_mi + total_tax

        turnover  = sum(c.abs_change for c in changes) / 2.0
        n_buys    = sum(1 for c in changes if c.trade_side == TradeSide.BUY)
        n_sells   = len(changes) - n_buys

        cost_inr = total_all * portfolio_value if portfolio_value > 0 else 0.0

        return ExecutionEstimate(
            total_transaction_cost = round(total_tc, 6),
            total_market_impact    = round(total_mi, 6),
            total_tax_cost         = round(total_tax, 6),
            total_cost_pct         = round(total_all, 6),
            total_turnover         = round(turnover, 4),
            n_trades               = len(changes),
            n_buys                 = n_buys,
            n_sells                = n_sells,
            trade_estimates        = tuple(trade_ests),
            portfolio_value        = portfolio_value,
            total_cost_inr         = round(cost_inr, 2),
        )

    def _estimate_trade(self, c: PositionChange) -> TradeEstimate:
        # Transaction cost: pct of portfolio × cost_rate per leg
        cost_rate = self._bond_rate if c.asset_class == "bond" else self._equity_rate
        tc = c.abs_change * cost_rate

        # Market impact: applies only to large trades
        mi = 0.0
        if c.abs_change >= self._impact_thr:
            # Impact scales with size above threshold
            excess = c.abs_change - self._impact_thr
            mi = excess * self._impact_fac / c.liquidity if c.liquidity > 0.01 else 0.0

        tax = c.applicable_tax   # already computed in PositionChange
        total = tc + mi + tax

        return TradeEstimate(
            symbol               = c.symbol,
            abs_change           = c.abs_change,
            trade_side           = c.trade_side,
            transaction_cost_pct = round(tc, 7),
            market_impact_pct    = round(mi, 7),
            tax_cost_pct         = round(tax, 7),
            total_cost_pct       = round(total, 7),
        )
