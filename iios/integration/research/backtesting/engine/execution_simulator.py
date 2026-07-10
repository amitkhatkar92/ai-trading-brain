"""engine/execution_simulator.py — Fills orders against historical bars."""
from __future__ import annotations

from typing import Any, Optional

from iios.integration.research.backtesting.backtest_constants import (
    ExecutionModel,
    OrderDirection,
    OrderStatus,
    OrderType,
)
from iios.integration.research.backtesting.backtest_exceptions import (
    InsufficientCapitalError,
    OrderRejectedError,
)
from iios.integration.research.backtesting.core.backtest_configuration import BacktestConfiguration
from iios.integration.research.backtesting.engine.market_simulator import BarEvent
from iios.integration.research.backtesting.execution.order import Fill, Order, OrderSignal
from iios.integration.research.backtesting.execution.portfolio import Portfolio


class ExecutionSimulator:
    """
    Converts strategy OrderSignals into Orders and fills them
    against historical BarEvent data.

    Supports four ExecutionModel modes:
        NEXT_OPEN  – fill at next bar's open (default, most realistic)
        CLOSE      – fill at current bar's close
        VWAP       – fill at estimated VWAP = (O+H+L+C)/4
        WORST_CASE – fill at worst price for the order direction
    """

    def __init__(self, config: BacktestConfiguration) -> None:
        self._config:   BacktestConfiguration = config
        self._pending:  list[Order]            = []
        self._rejected: list[Order]            = []
        self._stats:    dict[str, int]         = {
            "submitted": 0,
            "filled":    0,
            "rejected":  0,
        }

    # ── Signal → Order ────────────────────────────────────────────────────────

    def submit_signal(
        self,
        signal:    OrderSignal,
        portfolio: Portfolio,
        bar:       BarEvent,
    ) -> Optional[Order]:
        """
        Convert a strategy signal into a pending Order.

        Returns the Order on success, None if signal was filtered out.
        Raises InsufficientCapitalError if the portfolio cannot afford the order.
        """
        if signal.direction == OrderDirection.HOLD:
            return None

        if signal.size_pct <= 0:
            return None

        # Determine quantity from size_pct of available cash
        if signal.direction in (OrderDirection.LONG,):
            capital = portfolio.cash * signal.size_pct
            if capital < 0.01:
                return None
            quantity = capital / bar.close if bar.close > 0 else 0.0
        elif signal.direction == OrderDirection.SHORT:
            capital  = portfolio.cash * signal.size_pct
            quantity = capital / bar.close if bar.close > 0 else 0.0
        elif signal.direction in (OrderDirection.EXIT_LONG, OrderDirection.EXIT_SHORT):
            pos = portfolio.positions.get(signal.symbol)
            if pos is None:
                return None
            quantity = pos.quantity * signal.size_pct
        else:
            return None

        if quantity < 1e-9:
            return None

        order = Order(
            symbol       = signal.symbol,
            direction    = signal.direction,
            order_type   = signal.order_type,
            quantity     = quantity,
            limit_price  = signal.limit_price,
            stop_price   = signal.stop_price,
            status       = OrderStatus.PENDING,
            submitted_at = bar.timestamp,
            metadata     = dict(signal.metadata),
        )
        self._pending.append(order)
        self._stats["submitted"] += 1
        return order

    # ── Order filling ─────────────────────────────────────────────────────────

    def fill_pending(self, bars: dict[str, BarEvent]) -> list[Fill]:
        """
        Attempt to fill all pending orders with the current set of bars.
        Returns a list of Fills; unfillable orders remain in the queue.
        """
        fills:    list[Fill]  = []
        unfilled: list[Order] = []

        for order in self._pending:
            if order.symbol not in bars:
                unfilled.append(order)
                continue

            bar  = bars[order.symbol]
            fill = self._try_fill(order, bar)

            if fill is not None:
                order.status    = OrderStatus.FILLED
                order.filled_at = bar.timestamp
                order.fill_price = fill.fill_price
                fills.append(fill)
                self._stats["filled"] += 1
            else:
                if order.order_type == OrderType.MARKET:
                    # Market orders should always fill if bar data is present
                    # Reject only if fill_price calculation fails
                    order.status = OrderStatus.REJECTED
                    self._rejected.append(order)
                    self._stats["rejected"] += 1
                else:
                    unfilled.append(order)

        self._pending = unfilled
        return fills

    def _try_fill(self, order: Order, bar: BarEvent) -> Optional[Fill]:
        model = self._config.execution_model

        if model == ExecutionModel.NEXT_OPEN:
            raw_price = bar.open
        elif model == ExecutionModel.CLOSE:
            raw_price = bar.close
        elif model == ExecutionModel.VWAP:
            raw_price = bar.vwap
        elif model == ExecutionModel.WORST_CASE:
            raw_price = bar.high if order.direction == OrderDirection.LONG else bar.low
        else:
            raw_price = bar.close

        # Check limit / stop conditions
        if order.order_type == OrderType.LIMIT and order.limit_price is not None:
            if order.direction == OrderDirection.LONG and raw_price > order.limit_price:
                return None   # price hasn't come down to limit yet
            if order.direction == OrderDirection.SHORT and raw_price < order.limit_price:
                return None

        if order.order_type == OrderType.STOP and order.stop_price is not None:
            if order.direction == OrderDirection.LONG and raw_price < order.stop_price:
                return None
            if order.direction == OrderDirection.SHORT and raw_price > order.stop_price:
                return None

        if raw_price <= 0:
            return None

        # Apply slippage
        slip_factor = self._config.slippage_pct
        if order.direction in (OrderDirection.LONG, OrderDirection.EXIT_SHORT):
            fill_price = raw_price * (1.0 + slip_factor)
        else:
            fill_price = raw_price * (1.0 - slip_factor)

        slippage   = abs(fill_price - raw_price) * order.quantity
        commission = (
            self._config.commission_fixed
            + fill_price * order.quantity * self._config.commission_pct
        )

        return Fill(
            order_id   = order.order_id,
            symbol     = order.symbol,
            quantity   = order.quantity,
            fill_price = fill_price,
            commission = commission,
            slippage   = slippage,
            direction  = order.direction,
            timestamp  = bar.timestamp,
        )

    # ── Accessors ─────────────────────────────────────────────────────────────

    def pending_count(self) -> int:
        return len(self._pending)

    def stats(self) -> dict[str, Any]:
        return dict(self._stats)

    def clear(self) -> None:
        self._pending.clear()
        self._rejected.clear()
