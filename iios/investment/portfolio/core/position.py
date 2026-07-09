"""iios/investment/portfolio/core/position.py"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.investment.portfolio.portfolio_constants import (
    AssetClass,
    PositionStatus,
    PositionType,
)


@dataclass
class Position:
    """Represents a single portfolio holding."""

    position_id:       str            = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:      str            = ""
    company_id:        str            = ""
    ticker:            str            = ""
    name:              str            = ""
    asset_class:       AssetClass     = AssetClass.UNKNOWN
    position_type:     PositionType   = PositionType.LONG
    status:            PositionStatus = PositionStatus.OPEN

    # Size & price
    quantity:          float          = 0.0
    avg_cost:          float          = 0.0
    current_price:     float          = 0.0

    # Derived values (updated via update_price)
    market_value:      float          = 0.0   # quantity × current_price
    cost_basis:        float          = 0.0   # quantity × avg_cost
    unrealized_pnl:    float          = 0.0   # market_value − cost_basis
    unrealized_pnl_pct: float         = 0.0   # unrealized_pnl / cost_basis
    weight:            float          = 0.0   # market_value / portfolio_nav

    # Classification
    sector:            str            = ""
    industry:          str            = ""
    country:           str            = ""
    currency:          str            = "INR"
    strategy_id:       str            = ""

    metadata:          dict[str, Any] = field(default_factory=dict)
    opened_at:         float          = field(default_factory=time.time)
    updated_at:        float          = field(default_factory=time.time)

    def __post_init__(self) -> None:
        # Derive cost_basis and initial market_value on construction
        if self.cost_basis == 0.0 and self.quantity != 0 and self.avg_cost != 0:
            self.cost_basis = abs(self.quantity) * self.avg_cost
        if self.market_value == 0.0 and self.quantity != 0 and self.current_price != 0:
            self.market_value = abs(self.quantity) * self.current_price
            self._refresh_pnl()

    def update_price(self, price: float) -> None:
        self.current_price = price
        self.market_value  = abs(self.quantity) * price
        self._refresh_pnl()
        self.updated_at    = time.time()

    def _refresh_pnl(self) -> None:
        sign = 1.0 if self.position_type == PositionType.LONG else -1.0
        self.unrealized_pnl     = sign * (self.market_value - self.cost_basis)
        self.unrealized_pnl_pct = (
            self.unrealized_pnl / self.cost_basis
            if self.cost_basis > 0 else 0.0
        )

    @property
    def is_open(self) -> bool:
        return self.status == PositionStatus.OPEN

    @property
    def is_long(self) -> bool:
        return self.position_type == PositionType.LONG

    def to_dict(self) -> dict[str, Any]:
        return {
            "position_id":       self.position_id,
            "portfolio_id":      self.portfolio_id,
            "company_id":        self.company_id,
            "ticker":            self.ticker,
            "name":              self.name,
            "asset_class":       self.asset_class.value,
            "position_type":     self.position_type.value,
            "status":            self.status.value,
            "quantity":          self.quantity,
            "avg_cost":          self.avg_cost,
            "current_price":     self.current_price,
            "market_value":      self.market_value,
            "cost_basis":        self.cost_basis,
            "unrealized_pnl":    self.unrealized_pnl,
            "unrealized_pnl_pct": self.unrealized_pnl_pct,
            "weight":            self.weight,
            "sector":            self.sector,
            "industry":          self.industry,
            "country":           self.country,
            "currency":          self.currency,
            "strategy_id":       self.strategy_id,
            "metadata":          self.metadata,
            "opened_at":         self.opened_at,
            "updated_at":        self.updated_at,
        }
