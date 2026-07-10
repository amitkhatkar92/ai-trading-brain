"""execution/fill_simulator.py — Simulates order fills against price bars."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from iios.integration.research.paper_trading.paper_trading_constants import (
    FillModel,
    OrderSide,
    PaperOrderType,
    DEFAULT_FILL_MODEL,
)
from iios.integration.research.paper_trading.paper_trading_exceptions import FillError
from iios.integration.research.paper_trading.core.paper_order import PaperOrder
from iios.integration.research.paper_trading.market.market_simulator import PriceBar
from iios.integration.research.paper_trading.execution.slippage_model import SlippageModel
from iios.integration.research.paper_trading.execution.commission_model import CommissionModel
from iios.integration.research.paper_trading.execution.latency_model import LatencyModel


@dataclass
class FillResult:
    """Represents a successful order fill."""
    fill_id:    str
    order_id:   str
    symbol:     str
    quantity:   float
    fill_price: float
    commission: float
    slippage:   float
    side:       OrderSide
    timestamp:  float
    is_partial: bool = False
    metadata:   dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        order_id:   str,
        symbol:     str,
        quantity:   float,
        fill_price: float,
        commission: float,
        slippage:   float,
        side:       OrderSide,
        timestamp:  float,
        is_partial: bool = False,
    ) -> "FillResult":
        return cls(
            fill_id    = f"fill_{uuid.uuid4().hex[:10]}",
            order_id   = order_id,
            symbol     = symbol,
            quantity   = quantity,
            fill_price = fill_price,
            commission = commission,
            slippage   = slippage,
            side       = side,
            timestamp  = timestamp,
            is_partial = is_partial,
        )

    def net_cost(self) -> float:
        """Signed notional cost including commission and slippage.
        Positive = cash outflow (buy); negative = cash inflow (sell).
        """
        base = self.fill_price * self.quantity
        cost = self.commission + self.slippage
        if self.side == OrderSide.BUY:
            return base + cost
        return -(base - cost)


class FillSimulator:
    """
    Attempts to fill pending orders against the current bar's prices.

    Supports MARKET, LIMIT, STOP, and STOP_LIMIT order types.
    The fill model (NEXT_OPEN, CLOSE, VWAP, WORST_CASE) determines the base
    price before slippage is applied.
    """

    def __init__(
        self,
        slippage_model:  SlippageModel,
        commission_model: CommissionModel,
        latency_model:   LatencyModel,
        fill_model:      FillModel = DEFAULT_FILL_MODEL,
    ) -> None:
        self._slippage    = slippage_model
        self._commission  = commission_model
        self._latency     = latency_model
        self._fill_model  = fill_model

        # Pending next-bar fills: list of (order, intended_bar_after)
        self._pending_next_open: list[PaperOrder] = []

    def try_fill(
        self,
        order: PaperOrder,
        bar:   PriceBar,
    ) -> Optional[FillResult]:
        """
        Attempt to fill *order* against *bar*.

        Returns a FillResult on success, None if the order cannot be filled yet.
        """
        otype = order.order_type

        if otype == PaperOrderType.MARKET:
            return self._fill_at(order, self._base_price(bar), bar, is_partial=False)

        if otype == PaperOrderType.LIMIT:
            if not self._limit_triggered(order, bar):
                return None
            price = self._clamp_limit(order, bar)
            return self._fill_at(order, price, bar, is_partial=False)

        if otype == PaperOrderType.STOP:
            if not self._stop_triggered(order, bar):
                return None
            return self._fill_at(order, self._base_price(bar), bar, is_partial=False)

        if otype == PaperOrderType.STOP_LIMIT:
            if not self._stop_triggered(order, bar):
                return None
            if not self._limit_triggered(order, bar):
                return None
            price = self._clamp_limit(order, bar)
            return self._fill_at(order, price, bar, is_partial=False)

        # TRAILING_STOP — treated as market order for simplicity
        return self._fill_at(order, self._base_price(bar), bar, is_partial=False)

    # ── Fill construction ─────────────────────────────────────────────────────

    def _fill_at(
        self,
        order:       PaperOrder,
        base_price:  float,
        bar:         PriceBar,
        is_partial:  bool,
    ) -> FillResult:
        qty        = order.remaining_quantity()
        slip_amt   = self._slippage.compute(base_price, qty, order.side, bar)
        slip_unit  = slip_amt / qty if qty > 0 else 0.0
        # Slippage adjusts fill price
        fill_price = base_price + slip_unit if order.is_buy() else base_price - slip_unit
        commission = self._commission.compute(fill_price, qty)

        return FillResult.create(
            order_id   = order.order_id,
            symbol     = order.symbol,
            quantity   = qty,
            fill_price = fill_price,
            commission = commission,
            slippage   = slip_amt,
            side       = order.side,
            timestamp  = bar.timestamp,
            is_partial = is_partial,
        )

    # ── Price model ───────────────────────────────────────────────────────────

    def _base_price(self, bar: PriceBar) -> float:
        if self._fill_model == FillModel.CLOSE:
            return bar.close
        if self._fill_model == FillModel.VWAP:
            return bar.vwap
        if self._fill_model == FillModel.WORST_CASE:
            return bar.high   # worst for buyers (sellers get bar.low — handled as negative)
        # NEXT_OPEN — caller must pass the next bar; here we use bar.open
        return bar.open

    # ── Trigger logic ─────────────────────────────────────────────────────────

    def _limit_triggered(self, order: PaperOrder, bar: PriceBar) -> bool:
        if order.limit_price is None:
            return True
        if order.is_buy():
            return bar.low <= order.limit_price
        return bar.high >= order.limit_price

    def _stop_triggered(self, order: PaperOrder, bar: PriceBar) -> bool:
        if order.stop_price is None:
            return True
        if order.is_buy():
            return bar.high >= order.stop_price
        return bar.low <= order.stop_price

    def _clamp_limit(self, order: PaperOrder, bar: PriceBar) -> float:
        base = self._base_price(bar)
        if order.limit_price is None:
            return base
        if order.is_buy():
            return min(base, order.limit_price)
        return max(base, order.limit_price)
