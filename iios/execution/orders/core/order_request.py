"""iios/execution/orders/core/order_request.py"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from ..order_constants import (
    OrderAssetClass,
    OrderMode,
    OrderPriority,
    OrderSide,
    OrderType,
    TimeInForce,
)


@dataclass
class OrderRequest:
    """Immutable input to the OMS — describes what the caller *wants* to order."""

    request_id:    str             = field(default_factory=lambda: str(uuid.uuid4()))

    # Asset
    ticker:        str             = ""
    asset_id:      str             = ""
    exchange:      str             = ""
    asset_class:   OrderAssetClass = OrderAssetClass.UNKNOWN

    # Order spec
    order_type:    OrderType       = OrderType.MARKET
    side:          OrderSide       = OrderSide.BUY
    quantity:      float           = 0.0
    price:         float | None    = None
    stop_price:    float | None    = None
    limit_price:   float | None    = None
    trail_amount:  float | None    = None
    time_in_force: TimeInForce     = TimeInForce.DAY

    # Routing / control
    priority:      OrderPriority   = OrderPriority.NORMAL
    mode:          OrderMode       = OrderMode.PAPER

    # Linkage IDs
    execution_id:  str = ""
    decision_id:   str = ""
    portfolio_id:  str = ""
    strategy_id:   str = ""
    account_id:    str = ""

    # Risk
    max_slippage_pct:      float = 0.01
    max_market_impact_pct: float = 0.005

    # Good-Till-Date expiry (epoch float, optional)
    expires_at:    float | None = None

    tags:          list[str]       = field(default_factory=list)
    metadata:      dict[str, Any]  = field(default_factory=dict)

    created_at:    float           = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id":              self.request_id,
            "ticker":                  self.ticker,
            "asset_id":                self.asset_id,
            "exchange":                self.exchange,
            "asset_class":             self.asset_class.value,
            "order_type":              self.order_type.value,
            "side":                    self.side.value,
            "quantity":                self.quantity,
            "price":                   self.price,
            "stop_price":              self.stop_price,
            "limit_price":             self.limit_price,
            "trail_amount":            self.trail_amount,
            "time_in_force":           self.time_in_force.value,
            "priority":                self.priority.value,
            "mode":                    self.mode.value,
            "execution_id":            self.execution_id,
            "decision_id":             self.decision_id,
            "portfolio_id":            self.portfolio_id,
            "strategy_id":             self.strategy_id,
            "account_id":              self.account_id,
            "max_slippage_pct":        self.max_slippage_pct,
            "max_market_impact_pct":   self.max_market_impact_pct,
            "expires_at":              self.expires_at,
            "tags":                    list(self.tags),
            "metadata":                dict(self.metadata),
            "created_at":              self.created_at,
        }
