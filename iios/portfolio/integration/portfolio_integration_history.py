"""
portfolio_integration_history.py — iios.portfolio.integration
==============================================================
Thread-safe bounded integration history per portfolio and per request.

C10 Portfolio Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Dict, List, Optional, TYPE_CHECKING

from .constants import DEFAULT_MAX_HISTORY

if TYPE_CHECKING:
    from .portfolio_integration_response import PortfolioIntegrationResponse


class PortfolioIntegrationHistory:
    """
    Thread-safe, bounded history of integration responses.

    Maintains two indexes:
      - per-portfolio deque (capped at max_per_portfolio)
      - global deque (capped at max_total)
    """

    def __init__(
        self,
        max_per_portfolio: int = 100,
        max_total:         int = DEFAULT_MAX_HISTORY,
    ) -> None:
        if max_per_portfolio < 1:
            max_per_portfolio = 1
        if max_total < 1:
            max_total = 1
        self._max_per_portfolio = max_per_portfolio
        self._max_total         = max_total
        self._lock              = threading.Lock()
        # portfolio_id → deque[PortfolioIntegrationResponse]
        self._per_portfolio: Dict[str, deque] = {}
        # global ring buffer
        self._global: deque = deque(maxlen=max_total)

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def record(self, response: "PortfolioIntegrationResponse") -> None:
        pid = response.portfolio_id
        with self._lock:
            if pid not in self._per_portfolio:
                self._per_portfolio[pid] = deque(maxlen=self._max_per_portfolio)
            self._per_portfolio[pid].append(response)
            self._global.append(response)

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get_for_portfolio(
        self, portfolio_id: str, limit: int = 0
    ) -> "List[PortfolioIntegrationResponse]":
        with self._lock:
            dq = self._per_portfolio.get(portfolio_id)
            if not dq:
                return []
            items = list(dq)
        if limit > 0:
            return items[-limit:]
        return items

    def get_latest(
        self, portfolio_id: str
    ) -> "Optional[PortfolioIntegrationResponse]":
        with self._lock:
            dq = self._per_portfolio.get(portfolio_id)
            if not dq:
                return None
            return dq[-1]

    def get_global(self, limit: int = 0) -> "List[PortfolioIntegrationResponse]":
        with self._lock:
            items = list(self._global)
        if limit > 0:
            return items[-limit:]
        return items

    # ------------------------------------------------------------------
    # Inspection
    # ------------------------------------------------------------------

    def count_for_portfolio(self, portfolio_id: str) -> int:
        with self._lock:
            dq = self._per_portfolio.get(portfolio_id)
            return len(dq) if dq else 0

    def portfolio_count(self) -> int:
        with self._lock:
            return len(self._per_portfolio)

    def total_count(self) -> int:
        with self._lock:
            return len(self._global)

    def has_portfolio(self, portfolio_id: str) -> bool:
        with self._lock:
            return portfolio_id in self._per_portfolio

    def clear(self) -> None:
        with self._lock:
            self._per_portfolio.clear()
            self._global.clear()
