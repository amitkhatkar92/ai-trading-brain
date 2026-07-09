"""iios/investment/portfolio/core/portfolio.py"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.investment.portfolio.portfolio_constants import (
    PortfolioObjective,
    PortfolioStatus,
    PortfolioType,
    RiskLevel,
)
from iios.investment.portfolio.core.position import Position
from iios.investment.portfolio.core.asset_allocation import AssetAllocation


@dataclass
class Portfolio:
    """
    Core portfolio entity.

    Holds all open positions and tracks NAV.  Positions are stored
    in a dict keyed by ``position_id`` for O(1) access.
    """

    portfolio_id:      str                    = field(default_factory=lambda: str(uuid.uuid4()))
    name:              str                    = ""
    portfolio_type:    PortfolioType          = PortfolioType.UNKNOWN
    status:            PortfolioStatus        = PortfolioStatus.DRAFT
    objective:         PortfolioObjective     = PortfolioObjective.UNKNOWN
    base_currency:     str                    = "INR"
    benchmark:         str                    = ""
    inception_date:    str                    = ""
    cash:              float                  = 0.0
    risk_level:        RiskLevel              = RiskLevel.UNKNOWN
    max_positions:     int                    = 50
    max_single_weight: float                  = 0.25
    strategy_ids:      list[str]              = field(default_factory=list)
    account_id:        str                    = ""
    positions:         dict[str, Position]    = field(default_factory=dict)
    allocations:       dict[str, AssetAllocation] = field(default_factory=dict)
    metadata:          dict[str, Any]         = field(default_factory=dict)
    created_at:        float                  = field(default_factory=time.time)
    updated_at:        float                  = field(default_factory=time.time)

    # ── derived metrics ───────────────────────────────────────────────────────

    @property
    def invested_value(self) -> float:
        return sum(p.market_value for p in self.positions.values())

    @property
    def total_nav(self) -> float:
        return self.cash + self.invested_value

    @property
    def position_count(self) -> int:
        return len(self.positions)

    @property
    def unrealized_pnl(self) -> float:
        return sum(p.unrealized_pnl for p in self.positions.values())

    @property
    def unrealized_pnl_pct(self) -> float:
        cost = sum(p.cost_basis for p in self.positions.values())
        return self.unrealized_pnl / cost if cost > 0 else 0.0

    # ── mutation helpers ──────────────────────────────────────────────────────

    def add_position(self, position: Position) -> None:
        position.portfolio_id = self.portfolio_id
        self.positions[position.position_id] = position
        self.recompute_weights()
        self.updated_at = time.time()

    def remove_position(self, position_id: str) -> None:
        self.positions.pop(position_id, None)
        self.recompute_weights()
        self.updated_at = time.time()

    def get_position(self, position_id: str) -> Position | None:
        return self.positions.get(position_id)

    def update_cash(self, amount: float) -> None:
        self.cash      = amount
        self.recompute_weights()
        self.updated_at = time.time()

    def recompute_weights(self) -> None:
        nav = self.total_nav
        for pos in self.positions.values():
            pos.weight = pos.market_value / nav if nav > 0 else 0.0

    # ── grouping helpers ──────────────────────────────────────────────────────

    def by_sector(self) -> dict[str, list[Position]]:
        result: dict[str, list[Position]] = {}
        for p in self.positions.values():
            key = p.sector or "unknown"
            result.setdefault(key, []).append(p)
        return result

    def by_country(self) -> dict[str, list[Position]]:
        result: dict[str, list[Position]] = {}
        for p in self.positions.values():
            key = p.country or "unknown"
            result.setdefault(key, []).append(p)
        return result

    def by_asset_class(self) -> dict[str, list[Position]]:
        result: dict[str, list[Position]] = {}
        for p in self.positions.values():
            key = p.asset_class.value
            result.setdefault(key, []).append(p)
        return result

    def to_dict(self) -> dict[str, Any]:
        return {
            "portfolio_id":     self.portfolio_id,
            "name":             self.name,
            "portfolio_type":   self.portfolio_type.value,
            "status":           self.status.value,
            "objective":        self.objective.value,
            "base_currency":    self.base_currency,
            "benchmark":        self.benchmark,
            "cash":             self.cash,
            "total_nav":        self.total_nav,
            "invested_value":   self.invested_value,
            "position_count":   self.position_count,
            "unrealized_pnl":   self.unrealized_pnl,
            "risk_level":       self.risk_level.value,
            "strategy_ids":     self.strategy_ids,
            "account_id":       self.account_id,
            "metadata":         self.metadata,
            "created_at":       self.created_at,
            "updated_at":       self.updated_at,
        }
