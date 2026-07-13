"""iios/investment/strategy/portfolio/strategy_portfolio.py
StrategyPortfolio — the mutable core portfolio object with state machine.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from iios.investment.strategy.portfolio.strategy_allocation import (
    StrategyAllocation, AllocationStatus
)


class PortfolioType(str, Enum):
    EQUAL_WEIGHT       = "equal_weight"
    RISK_PARITY        = "risk_parity"
    PERFORMANCE_WEIGHT = "performance_weight"
    CONFIDENCE_WEIGHT  = "confidence_weight"
    VOLATILITY_WEIGHT  = "volatility_weight"
    COMPOSITE_WEIGHT   = "composite_weight"
    HIERARCHICAL       = "hierarchical"
    CUSTOM             = "custom"


class PortfolioState(str, Enum):
    CREATED    = "created"
    OPTIMIZED  = "optimized"
    APPROVED   = "approved"
    ACTIVE     = "active"
    REBALANCED = "rebalanced"
    PAUSED     = "paused"
    ARCHIVED   = "archived"


_VALID_TRANSITIONS: Dict[PortfolioState, frozenset] = {
    PortfolioState.CREATED:    frozenset({PortfolioState.OPTIMIZED, PortfolioState.ARCHIVED}),
    PortfolioState.OPTIMIZED:  frozenset({PortfolioState.APPROVED,  PortfolioState.CREATED, PortfolioState.ARCHIVED}),
    PortfolioState.APPROVED:   frozenset({PortfolioState.ACTIVE,    PortfolioState.ARCHIVED}),
    PortfolioState.ACTIVE:     frozenset({PortfolioState.REBALANCED, PortfolioState.PAUSED, PortfolioState.ARCHIVED}),
    PortfolioState.REBALANCED: frozenset({PortfolioState.ACTIVE,    PortfolioState.PAUSED,  PortfolioState.ARCHIVED}),
    PortfolioState.PAUSED:     frozenset({PortfolioState.ACTIVE,    PortfolioState.ARCHIVED}),
    PortfolioState.ARCHIVED:   frozenset(),
}


@dataclass
class StrategyPortfolio:
    """
    Core portfolio object.  Contains StrategyAllocation slots.
    State transitions are managed by PortfolioLifecycle.
    """
    portfolio_id:   str
    portfolio_name: str
    portfolio_type: PortfolioType
    state:          PortfolioState = PortfolioState.CREATED
    total_capital:  float = 0.0    # base capital (informational)
    version:        int   = 1

    allocations:    Dict[str, StrategyAllocation] = field(default_factory=dict)

    created_at:     datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at:     datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_optimized: Optional[datetime] = None
    last_rebalanced: Optional[datetime] = None

    metadata:       Dict[str, Any] = field(default_factory=dict)

    # ── allocation accessors ─────────────────────────────────────────────────

    def add_strategy(self, alloc: StrategyAllocation) -> None:
        self.allocations[alloc.strategy_id] = alloc
        self._touch()

    def remove_strategy(self, strategy_id: str) -> None:
        if strategy_id in self.allocations:
            self.allocations[strategy_id].status = AllocationStatus.REMOVED
        self._touch()

    def active_allocations(self) -> List[StrategyAllocation]:
        return [a for a in self.allocations.values() if a.is_active]

    @property
    def active_count(self) -> int:
        return sum(1 for a in self.allocations.values() if a.is_active)

    @property
    def total_weight(self) -> float:
        return sum(a.weight for a in self.allocations.values() if a.is_active)

    @property
    def max_drift(self) -> float:
        active = self.active_allocations()
        return max((a.weight_drift for a in active), default=0.0)

    # ── state machine ────────────────────────────────────────────────────────

    def can_transition_to(self, new_state: PortfolioState) -> bool:
        return new_state in _VALID_TRANSITIONS.get(self.state, frozenset())

    def apply_transition(self, new_state: PortfolioState, reason: str = "") -> None:
        if not self.can_transition_to(new_state):
            raise ValueError(f"Invalid transition: {self.state.value} → {new_state.value}")
        self.state = new_state
        self.version += 1
        self._touch()

    def _touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "portfolio_id":    self.portfolio_id,
            "portfolio_name":  self.portfolio_name,
            "portfolio_type":  self.portfolio_type.value,
            "state":           self.state.value,
            "total_capital":   self.total_capital,
            "version":         self.version,
            "active_count":    self.active_count,
            "total_weight":    round(self.total_weight, 6),
            "max_drift":       round(self.max_drift, 6),
            "created_at":      self.created_at.isoformat(),
            "updated_at":      self.updated_at.isoformat(),
            "allocations":     {sid: a.to_dict() for sid, a in self.allocations.items()},
        }
