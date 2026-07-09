"""iios/investment/portfolio/core/portfolio_history.py
Thread-safe per-portfolio ring buffer of PortfolioSnapshot objects.
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Any

from iios.investment.portfolio.portfolio_constants import DEFAULT_SNAPSHOT_HISTORY
from iios.investment.portfolio.core.portfolio_snapshot import PortfolioSnapshot


class PortfolioHistory:
    """Stores a bounded history of snapshots per portfolio."""

    def __init__(self, max_per_portfolio: int = DEFAULT_SNAPSHOT_HISTORY) -> None:
        self._lock              = threading.RLock()
        self._max_per_portfolio = max_per_portfolio
        self._store:            dict[str, deque[PortfolioSnapshot]] = {}

    def add(self, portfolio_id: str, snapshot: PortfolioSnapshot) -> None:
        with self._lock:
            buf = self._store.setdefault(portfolio_id, deque(maxlen=self._max_per_portfolio))
            buf.append(snapshot)

    def get_latest(self, portfolio_id: str) -> PortfolioSnapshot | None:
        with self._lock:
            buf = self._store.get(portfolio_id)
            return buf[-1] if buf else None

    def get_recent(self, portfolio_id: str, n: int = 10) -> list[PortfolioSnapshot]:
        with self._lock:
            buf = self._store.get(portfolio_id)
            if not buf:
                return []
            items = list(buf)
            return items[-n:] if len(items) >= n else items

    def count(self, portfolio_id: str) -> int:
        with self._lock:
            return len(self._store.get(portfolio_id, []))

    def all_portfolios(self) -> list[str]:
        with self._lock:
            return list(self._store.keys())

    def total_snapshots(self) -> int:
        with self._lock:
            return sum(len(b) for b in self._store.values())

    def statistics(self) -> dict[str, Any]:
        with self._lock:
            return {
                "portfolios":           len(self._store),
                "total_snapshots":      self.total_snapshots(),
                "max_per_portfolio":    self._max_per_portfolio,
            }
