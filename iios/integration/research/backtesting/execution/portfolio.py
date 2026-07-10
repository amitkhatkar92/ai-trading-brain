"""execution/portfolio.py — Portfolio and Position tracking during simulation."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from iios.integration.research.backtesting.backtest_constants import (
    OrderDirection,
    PositionSide,
)
from iios.integration.research.backtesting.execution.order import Fill
from iios.integration.research.backtesting.execution.trade import Trade


@dataclass
class Position:
    """Open position held in the portfolio."""
    symbol:          str          = ""
    side:            PositionSide = PositionSide.LONG
    quantity:        float        = 0.0
    avg_entry_price: float        = 0.0
    current_price:   float        = 0.0
    unrealized_pnl:  float        = 0.0
    realized_pnl:    float        = 0.0
    opened_at:       float        = field(default_factory=time.time)
    last_updated:    float        = field(default_factory=time.time)

    @property
    def market_value(self) -> float:
        return self.quantity * self.current_price

    @property
    def cost_basis(self) -> float:
        return self.quantity * self.avg_entry_price

    def update_price(self, price: float, ts: float) -> None:
        self.current_price  = price
        self.last_updated   = ts
        if self.side == PositionSide.LONG:
            self.unrealized_pnl = (price - self.avg_entry_price) * self.quantity
        else:
            self.unrealized_pnl = (self.avg_entry_price - price) * self.quantity

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol":          self.symbol,
            "side":            self.side.value,
            "quantity":        self.quantity,
            "avg_entry_price": self.avg_entry_price,
            "current_price":   self.current_price,
            "unrealized_pnl":  self.unrealized_pnl,
            "realized_pnl":    self.realized_pnl,
            "market_value":    self.market_value,
            "opened_at":       self.opened_at,
        }


@dataclass(frozen=True)
class PortfolioSnapshot:
    """Immutable view of portfolio state passed to the strategy."""
    timestamp:       float
    cash:            float
    total_equity:    float
    open_positions:  int
    total_pnl:       float
    return_pct:      float
    positions:       dict[str, dict[str, Any]]   # symbol → position summary


class Portfolio:
    """
    Mutable portfolio state updated bar-by-bar during simulation.

    All monetary units are in the same currency as initial_capital.
    """

    def __init__(self, initial_capital: float) -> None:
        self._initial_capital = initial_capital
        self._cash:          float                   = initial_capital
        self._positions:     dict[str, Position]     = {}
        self._trades:        list[Trade]             = []
        self._equity_curve:  list[tuple[float, float]] = []

    # ── Read-only properties ──────────────────────────────────────────────────

    @property
    def cash(self) -> float:
        return self._cash

    @property
    def initial_capital(self) -> float:
        return self._initial_capital

    @property
    def positions(self) -> dict[str, Position]:
        return dict(self._positions)

    @property
    def completed_trades(self) -> list[Trade]:
        return list(self._trades)

    @property
    def equity_curve(self) -> list[tuple[float, float]]:
        return list(self._equity_curve)

    def total_equity(self) -> float:
        position_value = sum(p.market_value for p in self._positions.values())
        return self._cash + position_value

    # ── Fill application ──────────────────────────────────────────────────────

    def apply_fill(self, fill: Fill) -> None:
        direction = fill.direction

        if direction in (OrderDirection.LONG, OrderDirection.SHORT):
            self._open_or_add(fill)
        elif direction in (OrderDirection.EXIT_LONG, OrderDirection.EXIT_SHORT):
            self._close_or_reduce(fill)

    def _open_or_add(self, fill: Fill) -> None:
        symbol = fill.symbol
        side   = PositionSide.LONG if fill.direction == OrderDirection.LONG else PositionSide.SHORT

        if symbol in self._positions:
            pos = self._positions[symbol]
            total_qty        = pos.quantity + fill.quantity
            pos.avg_entry_price = (
                pos.avg_entry_price * pos.quantity + fill.fill_price * fill.quantity
            ) / total_qty
            pos.quantity         = total_qty
            pos.last_updated     = fill.timestamp
        else:
            self._positions[symbol] = Position(
                symbol          = symbol,
                side            = side,
                quantity        = fill.quantity,
                avg_entry_price = fill.fill_price,
                current_price   = fill.fill_price,
                opened_at       = fill.timestamp,
                last_updated    = fill.timestamp,
            )

        if fill.direction == OrderDirection.LONG:
            self._cash -= fill.quantity * fill.fill_price + fill.commission
        else:
            # Short: receive cash from sale (simplified — no margin model)
            self._cash += fill.quantity * fill.fill_price - fill.commission

    def _close_or_reduce(self, fill: Fill) -> None:
        symbol = fill.symbol
        if symbol not in self._positions:
            return

        pos       = self._positions[symbol]
        close_qty = min(fill.quantity, pos.quantity)

        if pos.side == PositionSide.LONG:
            gross_pnl   = (fill.fill_price - pos.avg_entry_price) * close_qty
            self._cash += fill.fill_price * close_qty - fill.commission
        else:
            gross_pnl   = (pos.avg_entry_price - fill.fill_price) * close_qty
            self._cash -= fill.fill_price * close_qty + fill.commission

        net_pnl    = gross_pnl - fill.commission
        cost_basis = pos.avg_entry_price * close_qty
        return_pct = net_pnl / cost_basis if cost_basis > 0 else 0.0

        trade = Trade(
            symbol       = symbol,
            side         = pos.side,
            entry_price  = pos.avg_entry_price,
            exit_price   = fill.fill_price,
            quantity     = close_qty,
            gross_pnl    = gross_pnl,
            commission   = fill.commission,
            net_pnl      = net_pnl,
            return_pct   = return_pct,
            entry_time   = pos.opened_at,
            exit_time    = fill.timestamp,
            duration_sec = fill.timestamp - pos.opened_at,
        )
        self._trades.append(trade)
        pos.realized_pnl += net_pnl
        pos.quantity     -= close_qty
        if pos.quantity <= 1e-9:
            del self._positions[symbol]

    # ── Price update ──────────────────────────────────────────────────────────

    def update_prices(self, prices: dict[str, float], timestamp: float) -> None:
        for symbol, price in prices.items():
            if symbol in self._positions:
                self._positions[symbol].update_price(price, timestamp)
        self._equity_curve.append((timestamp, self.total_equity()))

    # ── Force-close all ───────────────────────────────────────────────────────

    def close_all_positions(self, prices: dict[str, float], timestamp: float) -> None:
        """Force-close every open position at given prices (end of backtest)."""
        for symbol in list(self._positions.keys()):
            pos   = self._positions[symbol]
            price = prices.get(symbol, pos.current_price)
            direction = (
                OrderDirection.EXIT_LONG
                if pos.side == PositionSide.LONG
                else OrderDirection.EXIT_SHORT
            )
            # Create a synthetic fill with zero commission (already accounted for at entry)
            fill = Fill(
                order_id   = "close_all",
                symbol     = symbol,
                quantity   = pos.quantity,
                fill_price = price,
                commission = 0.0,
                direction  = direction,
                timestamp  = timestamp,
            )
            self._close_or_reduce(fill)
        self._equity_curve.append((timestamp, self.total_equity()))

    # ── Snapshot ──────────────────────────────────────────────────────────────

    def snapshot(self, timestamp: float) -> PortfolioSnapshot:
        equity = self.total_equity()
        return PortfolioSnapshot(
            timestamp      = timestamp,
            cash           = self._cash,
            total_equity   = equity,
            open_positions = len(self._positions),
            total_pnl      = equity - self._initial_capital,
            return_pct     = (equity - self._initial_capital) / self._initial_capital,
            positions      = {s: p.to_dict() for s, p in self._positions.items()},
        )
