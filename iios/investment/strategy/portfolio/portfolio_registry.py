"""iios/investment/strategy/portfolio/portfolio_registry.py
PortfolioRegistry — thread-safe store of all portfolios.
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from iios.investment.strategy.portfolio.strategy_portfolio import (
    StrategyPortfolio, PortfolioState
)


class PortfolioRegistry:
    """
    Central registry for all StrategyPortfolio objects.
    Thread-safe; all mutations go through this registry.
    """

    def __init__(self) -> None:
        self._portfolios: Dict[str, StrategyPortfolio] = {}
        self._lock = threading.RLock()

    def register(self, portfolio: StrategyPortfolio) -> None:
        with self._lock:
            self._portfolios[portfolio.portfolio_id] = portfolio

    def get(self, portfolio_id: str) -> Optional[StrategyPortfolio]:
        with self._lock:
            return self._portfolios.get(portfolio_id)

    def all(self) -> List[StrategyPortfolio]:
        with self._lock:
            return list(self._portfolios.values())

    def active(self) -> List[StrategyPortfolio]:
        with self._lock:
            return [
                p for p in self._portfolios.values()
                if p.state in (PortfolioState.ACTIVE, PortfolioState.REBALANCED)
            ]

    def by_state(self, state: PortfolioState) -> List[StrategyPortfolio]:
        with self._lock:
            return [p for p in self._portfolios.values() if p.state == state]

    def remove(self, portfolio_id: str) -> bool:
        with self._lock:
            if portfolio_id in self._portfolios:
                del self._portfolios[portfolio_id]
                return True
            return False

    def ids(self) -> List[str]:
        with self._lock:
            return list(self._portfolios.keys())

    def count(self) -> int:
        with self._lock:
            return len(self._portfolios)
