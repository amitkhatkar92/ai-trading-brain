"""portfolio/position_manager.py — Manages open positions for a paper account."""
from __future__ import annotations

import time
from typing import Any, Optional

from iios.integration.research.paper_trading.paper_trading_constants import (
    OrderSide,
    PaperPositionSide,
)
from iios.integration.research.paper_trading.paper_trading_exceptions import (
    PositionNotFoundError,
    PositionError,
)
from iios.integration.research.paper_trading.core.paper_position import PaperPosition
from iios.integration.research.paper_trading.core.paper_trade import PaperTrade
from iios.integration.research.paper_trading.execution.fill_simulator import FillResult


def _fill_side(fill: FillResult) -> PaperPositionSide:
    return PaperPositionSide.LONG if fill.side == OrderSide.BUY else PaperPositionSide.SHORT


class PositionManager:
    """
    Opens, updates, and closes positions as fills arrive.

    One open position per symbol at a time.
    A fill in the opposite direction reduces (or closes) the existing position.
    Flipping (reversing) a position requires two fills: one close + one open.
    """

    def __init__(self, account_id: str, session_id: str) -> None:
        self._account_id = account_id
        self._session_id = session_id
        self._positions:       dict[str, PaperPosition] = {}
        self._closed_trades:   list[PaperTrade]         = []

    # ── Fill processing ───────────────────────────────────────────────────────

    def apply_fill(self, fill: FillResult) -> Optional[PaperTrade]:
        """
        Apply a fill to the position book.

        Returns a completed PaperTrade if a position is fully or partially closed,
        else None (when opening or adding to a position).
        """
        existing = self._positions.get(fill.symbol)

        if existing is None:
            # Open a new position
            self._open_position(fill)
            return None

        fill_pos_side = _fill_side(fill)
        if fill_pos_side == existing.side:
            # Adding to existing position
            existing.add_to_position(fill.quantity, fill.fill_price, fill.commission)
            return None

        # Opposite direction — reduce or close
        return self._reduce_or_close(existing, fill)

    def _open_position(self, fill: FillResult) -> PaperPosition:
        pos = PaperPosition.open(
            account_id = self._account_id,
            session_id = self._session_id,
            symbol     = fill.symbol,
            side       = _fill_side(fill),
            quantity   = fill.quantity,
            price      = fill.fill_price,
            commission = fill.commission,
        )
        self._positions[fill.symbol] = pos
        return pos

    def _reduce_or_close(
        self, pos: PaperPosition, fill: FillResult
    ) -> PaperTrade:
        close_qty = min(fill.quantity, pos.quantity)
        realized  = pos.reduce_position(close_qty, fill.fill_price, fill.commission)

        trade = PaperTrade.create(
            order_id    = fill.order_id,
            account_id  = self._account_id,
            session_id  = self._session_id,
            symbol      = fill.symbol,
            side        = pos.side,
            quantity    = close_qty,
            entry_price = pos.avg_cost,
            exit_price  = fill.fill_price,
            commission  = fill.commission,
            slippage    = fill.slippage,
            entry_time  = pos.opened_at,
            exit_time   = fill.timestamp,
        )
        self._closed_trades.append(trade)

        if pos.is_closed():
            del self._positions[fill.symbol]
            # If there is residual fill quantity, open a new reversed position
            residual = fill.quantity - close_qty
            if residual > 1e-9:
                self._positions[fill.symbol] = PaperPosition.open(
                    account_id = self._account_id,
                    session_id = self._session_id,
                    symbol     = fill.symbol,
                    side       = _fill_side(fill),
                    quantity   = residual,
                    price      = fill.fill_price,
                )

        return trade

    # ── Price updates ─────────────────────────────────────────────────────────

    def update_prices(self, prices: dict[str, float], timestamp: float) -> None:
        for symbol, price in prices.items():
            if symbol in self._positions:
                self._positions[symbol].update_price(price, timestamp)

    # ── Forced close ─────────────────────────────────────────────────────────

    def close_all(
        self, prices: dict[str, float], timestamp: float
    ) -> list[PaperTrade]:
        """
        Force-close all open positions at the given prices.

        Used at end-of-simulation to produce a clean PnL record.
        """
        trades: list[PaperTrade] = []
        for symbol in list(self._positions.keys()):
            pos = self._positions.get(symbol)
            if pos is None:
                continue
            price = prices.get(symbol, pos.current_price)
            fill = FillResult.create(
                order_id   = "eod_close",
                symbol     = symbol,
                quantity   = pos.quantity,
                fill_price = price,
                commission = 0.0,
                slippage   = 0.0,
                side       = OrderSide.SELL if pos.is_long() else OrderSide.BUY,
                timestamp  = timestamp,
            )
            trade = self._reduce_or_close(pos, fill)
            trades.append(trade)
        return trades

    # ── Queries ───────────────────────────────────────────────────────────────

    def get_position(self, symbol: str) -> Optional[PaperPosition]:
        return self._positions.get(symbol)

    def open_positions(self) -> list[PaperPosition]:
        return list(self._positions.values())

    def all_positions(self) -> list[PaperPosition]:
        return list(self._positions.values())

    def completed_trades(self) -> list[PaperTrade]:
        return list(self._closed_trades)

    def total_market_value(self) -> float:
        return sum(p.market_value for p in self._positions.values())

    def total_unrealized_pnl(self) -> float:
        return sum(p.unrealized_pnl for p in self._positions.values())

    def stats(self) -> dict[str, Any]:
        return {
            "open_positions":  len(self._positions),
            "completed_trades": len(self._closed_trades),
            "total_market_value": self.total_market_value(),
            "total_unrealized_pnl": self.total_unrealized_pnl(),
        }
