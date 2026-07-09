"""iios/investment/portfolio/portfolio_factory.py
Convenience factory for constructing portfolio domain objects.
"""
from __future__ import annotations

from typing import Any

from iios.investment.portfolio.portfolio_constants import (
    AssetClass,
    PortfolioObjective,
    PortfolioStatus,
    PortfolioType,
    PositionStatus,
    PositionType,
    RiskLevel,
)
from iios.investment.portfolio.core.portfolio import Portfolio
from iios.investment.portfolio.core.portfolio_profile import PortfolioProfile
from iios.investment.portfolio.core.position import Position
from iios.investment.portfolio.core.portfolio_snapshot import PortfolioSnapshot


class PortfolioFactory:
    """Stateless factory — all methods are static."""

    @staticmethod
    def make_portfolio(
        name:           str              = "",
        portfolio_type: PortfolioType    = PortfolioType.EQUITY,
        objective:      PortfolioObjective = PortfolioObjective.GROWTH,
        base_currency:  str              = "INR",
        cash:           float            = 0.0,
        **kwargs: Any,
    ) -> Portfolio:
        return Portfolio(
            name           = name,
            portfolio_type = portfolio_type,
            status         = PortfolioStatus.ACTIVE,
            objective      = objective,
            base_currency  = base_currency,
            cash           = cash,
            risk_level     = kwargs.get("risk_level", RiskLevel.UNKNOWN),
            account_id     = str(kwargs.get("account_id", "")),
            benchmark      = str(kwargs.get("benchmark", "")),
        )

    @staticmethod
    def make_profile(portfolio: Portfolio, **kwargs: Any) -> PortfolioProfile:
        return PortfolioProfile(
            portfolio_id = portfolio.portfolio_id,
            portfolio    = portfolio,
            account_id   = str(kwargs.get("account_id", "")),
            manager_id   = str(kwargs.get("manager_id", "")),
        )

    @staticmethod
    def make_position(
        portfolio_id:  str         = "",
        ticker:        str         = "",
        quantity:      float       = 0.0,
        avg_cost:      float       = 0.0,
        current_price: float       = 0.0,
        asset_class:   AssetClass  = AssetClass.EQUITY,
        **kwargs: Any,
    ) -> Position:
        pos = Position(
            portfolio_id  = portfolio_id,
            ticker        = ticker,
            quantity      = quantity,
            avg_cost      = avg_cost,
            current_price = current_price or avg_cost,
            asset_class   = asset_class,
            position_type = kwargs.get("position_type", PositionType.LONG),
            status        = PositionStatus.OPEN,
            name          = str(kwargs.get("name", ticker)),
            sector        = str(kwargs.get("sector", "")),
            industry      = str(kwargs.get("industry", "")),
            country       = str(kwargs.get("country", "IN")),
            currency      = str(kwargs.get("currency", "INR")),
            strategy_id   = str(kwargs.get("strategy_id", "")),
        )
        # Ensure derived values are computed
        if pos.cost_basis == 0.0 and quantity and avg_cost:
            pos.cost_basis  = abs(quantity) * avg_cost
        if pos.market_value == 0.0 and quantity and (current_price or avg_cost):
            pos.market_value = abs(quantity) * (current_price or avg_cost)
            pos._refresh_pnl()
        return pos

    @staticmethod
    def make_snapshot(
        portfolio_id: str   = "",
        total_nav:    float = 0.0,
        **kwargs: Any,
    ) -> PortfolioSnapshot:
        return PortfolioSnapshot(
            portfolio_id   = portfolio_id,
            total_nav      = total_nav,
            cash           = float(kwargs.get("cash", 0.0)),
            position_count = int(kwargs.get("position_count", 0)),
        )
