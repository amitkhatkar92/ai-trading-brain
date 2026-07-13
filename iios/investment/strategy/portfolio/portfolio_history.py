"""iios/investment/strategy/portfolio/portfolio_history.py
PortfolioHistory — thread-safe ring buffer of PortfolioSnapshot objects.
"""
from __future__ import annotations

import threading
import uuid
from collections import deque
from typing import Deque, Dict, List, Optional

from iios.investment.strategy.portfolio.strategy_portfolio import StrategyPortfolio
from iios.investment.strategy.portfolio.portfolio_snapshot import PortfolioSnapshot


class PortfolioHistory:
    """Append-only ring buffer of portfolio snapshots, one deque per portfolio_id."""

    def __init__(self, max_per_portfolio: int = 1_000) -> None:
        self._max   = max_per_portfolio
        self._store: Dict[str, Deque[PortfolioSnapshot]] = {}
        self._lock  = threading.RLock()

    def capture(self, portfolio: StrategyPortfolio) -> PortfolioSnapshot:
        """Take a snapshot of the current portfolio state and store it."""
        snap = PortfolioSnapshot.from_portfolio(portfolio, str(uuid.uuid4()))
        with self._lock:
            pid = portfolio.portfolio_id
            if pid not in self._store:
                self._store[pid] = deque(maxlen=self._max)
            self._store[pid].append(snap)
        return snap

    def latest(self, portfolio_id: str) -> Optional[PortfolioSnapshot]:
        with self._lock:
            buf = self._store.get(portfolio_id)
            return buf[-1] if buf else None

    def history(self, portfolio_id: str, n: int = 20) -> List[PortfolioSnapshot]:
        with self._lock:
            buf = list(self._store.get(portfolio_id, []))
            return buf[-n:]

    def version_count(self, portfolio_id: str) -> int:
        with self._lock:
            return len(self._store.get(portfolio_id, []))

    def purge(self, portfolio_id: str) -> None:
        with self._lock:
            self._store.pop(portfolio_id, None)

    def all_portfolio_ids(self) -> List[str]:
        with self._lock:
            return list(self._store.keys())
