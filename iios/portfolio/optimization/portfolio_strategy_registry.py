"""
portfolio_strategy_registry.py — iios.portfolio.optimization
=============================================================
Thread-safe, bounded registry for optimization strategies.

C10 Portfolio Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from .constants import DEFAULT_MAX_STRATEGIES, DEFAULT_STRATEGY_NAME, StrategyStatus
from .exceptions import (
    PortfolioOptimizationCapacityError,
    PortfolioOptimizationNotFoundError,
)
from .portfolio_optimization_strategy import PortfolioOptimizationStrategy


class PortfolioStrategyRegistry:
    """
    Thread-safe, bounded store for optimization strategies.

    The registry allows lookup by ``strategy_id`` or ``name``.
    Exactly one strategy may carry ``is_default=True``; registering a
    new default automatically demotes the previous default.

    Parameters
    ----------
    max_strategies : Hard upper bound on stored strategies.
    """

    def __init__(self, max_strategies: int = DEFAULT_MAX_STRATEGIES) -> None:
        self._max  = max_strategies
        self._by_id:   Dict[str, PortfolioOptimizationStrategy] = {}
        self._by_name: Dict[str, PortfolioOptimizationStrategy] = {}
        self._lock = threading.Lock()
        self._default_id: Optional[str] = None

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def register(self, strategy: PortfolioOptimizationStrategy) -> None:
        """Register a strategy.  Raises PortfolioOptimizationCapacityError if full."""
        with self._lock:
            if (
                len(self._by_id) >= self._max
                and strategy.strategy_id not in self._by_id
            ):
                raise PortfolioOptimizationCapacityError(
                    self._max, resource="strategy registry"
                )
            self._by_id[strategy.strategy_id] = strategy
            self._by_name[strategy.name]       = strategy
            if strategy.is_default:
                self._default_id = strategy.strategy_id

    def remove(self, strategy_id: str) -> None:
        with self._lock:
            if strategy_id not in self._by_id:
                raise PortfolioOptimizationNotFoundError(
                    strategy_id, item_type="strategy"
                )
            strat = self._by_id.pop(strategy_id)
            self._by_name.pop(strat.name, None)
            if self._default_id == strategy_id:
                self._default_id = None

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get(self, strategy_id: str) -> Optional[PortfolioOptimizationStrategy]:
        with self._lock:
            return self._by_id.get(strategy_id)

    def get_by_name(self, name: str) -> Optional[PortfolioOptimizationStrategy]:
        with self._lock:
            return self._by_name.get(name)

    def default_strategy(self) -> Optional[PortfolioOptimizationStrategy]:
        with self._lock:
            if self._default_id:
                return self._by_id.get(self._default_id)
            # Fallback: return the first active strategy named "default"
            return self._by_name.get(DEFAULT_STRATEGY_NAME)

    def resolve(self, name: str) -> Optional[PortfolioOptimizationStrategy]:
        """Return strategy by name, falling back to the default strategy."""
        strat = self.get_by_name(name)
        return strat if strat is not None else self.default_strategy()

    def all_active(self) -> List[PortfolioOptimizationStrategy]:
        with self._lock:
            return [
                s for s in self._by_id.values()
                if s.status == StrategyStatus.ACTIVE
            ]

    def all(self) -> List[PortfolioOptimizationStrategy]:
        with self._lock:
            return list(self._by_id.values())

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._by_id)

    @property
    def active_count(self) -> int:
        return len(self.all_active())

    def __contains__(self, strategy_id: str) -> bool:
        with self._lock:
            return strategy_id in self._by_id
