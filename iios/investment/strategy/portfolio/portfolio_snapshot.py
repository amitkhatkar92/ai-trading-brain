"""iios/investment/strategy/portfolio/portfolio_snapshot.py
PortfolioSnapshot — immutable point-in-time capture of a portfolio.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

from iios.investment.strategy.portfolio.strategy_portfolio import (
    StrategyPortfolio, PortfolioState, PortfolioType
)
from iios.investment.strategy.portfolio.strategy_allocation import StrategyAllocation


@dataclass(frozen=True)
class AllocationSnapshot:
    strategy_id:   str
    strategy_name: str
    weight:        float
    target_weight: float
    status:        str
    evaluation_score: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id":    self.strategy_id,
            "strategy_name":  self.strategy_name,
            "weight":         self.weight,
            "target_weight":  self.target_weight,
            "status":         self.status,
            "evaluation_score": self.evaluation_score,
        }


@dataclass(frozen=True)
class PortfolioSnapshot:
    """Immutable record of portfolio state at a point in time."""
    snapshot_id:    str
    portfolio_id:   str
    portfolio_name: str
    portfolio_type: str
    state:          str
    version:        int
    total_capital:  float
    active_count:   int
    total_weight:   float
    max_drift:      float
    allocations:    Tuple[AllocationSnapshot, ...]
    captured_at:    datetime

    @classmethod
    def from_portfolio(
        cls, portfolio: StrategyPortfolio, snapshot_id: str
    ) -> "PortfolioSnapshot":
        import uuid
        snaps = tuple(
            AllocationSnapshot(
                strategy_id=a.strategy_id,
                strategy_name=a.strategy_name,
                weight=a.weight,
                target_weight=a.target_weight,
                status=a.status.value,
                evaluation_score=a.evaluation_score,
            )
            for a in portfolio.allocations.values()
        )
        return cls(
            snapshot_id=snapshot_id,
            portfolio_id=portfolio.portfolio_id,
            portfolio_name=portfolio.portfolio_name,
            portfolio_type=portfolio.portfolio_type.value,
            state=portfolio.state.value,
            version=portfolio.version,
            total_capital=portfolio.total_capital,
            active_count=portfolio.active_count,
            total_weight=round(portfolio.total_weight, 6),
            max_drift=round(portfolio.max_drift, 6),
            allocations=snaps,
            captured_at=datetime.now(timezone.utc),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id":   self.snapshot_id,
            "portfolio_id":  self.portfolio_id,
            "portfolio_name": self.portfolio_name,
            "portfolio_type": self.portfolio_type,
            "state":         self.state,
            "version":       self.version,
            "total_capital": self.total_capital,
            "active_count":  self.active_count,
            "total_weight":  self.total_weight,
            "max_drift":     self.max_drift,
            "captured_at":   self.captured_at.isoformat(),
            "allocations":   [a.to_dict() for a in self.allocations],
        }
