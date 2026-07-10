"""execution/order.py — Order, OrderSignal, and Fill data models."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from iios.integration.research.backtesting.backtest_constants import (
    OrderDirection,
    OrderStatus,
    OrderType,
)


@dataclass
class OrderSignal:
    """
    A trading instruction emitted by a BacktestStrategy.

    The execution simulator converts this into a concrete Order
    and fills it according to the configured ExecutionModel.
    """
    symbol:       str            = ""
    direction:    OrderDirection = OrderDirection.LONG
    order_type:   OrderType      = OrderType.MARKET
    size_pct:     float          = 1.0       # fraction of available capital
    limit_price:  Optional[float] = None
    stop_price:   Optional[float] = None
    metadata:     dict[str, Any] = field(default_factory=dict)


@dataclass
class Order:
    """Internal representation of a pending or filled order."""
    symbol:        str             = ""
    direction:     OrderDirection  = OrderDirection.LONG
    order_type:    OrderType       = OrderType.MARKET
    quantity:      float           = 0.0
    limit_price:   Optional[float] = None
    stop_price:    Optional[float] = None

    order_id:      str             = field(default_factory=lambda: str(uuid.uuid4()))
    backtest_id:   str             = ""
    status:        OrderStatus     = OrderStatus.PENDING

    submitted_at:  float           = field(default_factory=time.time)
    filled_at:     Optional[float] = None
    fill_price:    Optional[float] = None
    commission:    float           = 0.0
    slippage:      float           = 0.0
    metadata:      dict[str, Any]  = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "order_id":     self.order_id,
            "backtest_id":  self.backtest_id,
            "symbol":       self.symbol,
            "direction":    self.direction.value,
            "order_type":   self.order_type.value,
            "quantity":     self.quantity,
            "limit_price":  self.limit_price,
            "stop_price":   self.stop_price,
            "status":       self.status.value,
            "submitted_at": self.submitted_at,
            "filled_at":    self.filled_at,
            "fill_price":   self.fill_price,
            "commission":   self.commission,
            "slippage":     self.slippage,
        }


@dataclass
class Fill:
    """Record of a successful order execution."""
    order_id:   str            = ""
    symbol:     str            = ""
    quantity:   float          = 0.0
    fill_price: float          = 0.0
    commission: float          = 0.0
    slippage:   float          = 0.0
    direction:  OrderDirection = OrderDirection.LONG
    timestamp:  float          = field(default_factory=time.time)
    fill_id:    str            = field(default_factory=lambda: str(uuid.uuid4()))

    def net_cost(self) -> float:
        """Positive = cash out; negative = cash in."""
        if self.direction in (OrderDirection.LONG,):
            return self.fill_price * self.quantity + self.commission
        return -(self.fill_price * self.quantity - self.commission)

    def to_dict(self) -> dict[str, Any]:
        return {
            "fill_id":    self.fill_id,
            "order_id":   self.order_id,
            "symbol":     self.symbol,
            "quantity":   self.quantity,
            "fill_price": self.fill_price,
            "commission": self.commission,
            "slippage":   self.slippage,
            "direction":  self.direction.value,
            "timestamp":  self.timestamp,
        }
