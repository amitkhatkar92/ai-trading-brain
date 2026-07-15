"""iios/investment/portfolio/rebalancing/rebalance_history.py

Per-portfolio bounded history of RebalancePlan objects.
"""
from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional


class PortfolioRebalanceHistory:
    """
    Thread-safe bounded per-portfolio history of rebalancing plans.

    Accepts duck-typed plan objects (any object with plan_id, rebalance_score,
    portfolio_id attributes).
    """

    def __init__(self, max_per_portfolio: int = 50) -> None:
        self._max   = max_per_portfolio
        self._lock  = threading.RLock()
        self._store: Dict[str, List[Any]] = {}   # pid → list[plan]

    def add(self, portfolio_id: str, plan: Any) -> None:
        with self._lock:
            if portfolio_id not in self._store:
                self._store[portfolio_id] = []
            self._store[portfolio_id].append(plan)
            if len(self._store[portfolio_id]) > self._max:
                self._store[portfolio_id] = self._store[portfolio_id][-self._max:]

    def latest(self, portfolio_id: str) -> Optional[Any]:
        with self._lock:
            plans = self._store.get(portfolio_id)
            return plans[-1] if plans else None

    def recent(self, portfolio_id: str, n: int = 5) -> List[Any]:
        with self._lock:
            plans = self._store.get(portfolio_id, [])
            return list(plans[-n:])

    def best(self, portfolio_id: str) -> Optional[Any]:
        with self._lock:
            plans = self._store.get(portfolio_id)
            if not plans:
                return None
            return max(plans, key=lambda p: getattr(p, "rebalance_score", 0.0))

    def count(self, portfolio_id: str) -> int:
        with self._lock:
            return len(self._store.get(portfolio_id, []))

    def all_portfolio_ids(self) -> List[str]:
        with self._lock:
            return list(self._store.keys())

    def clear(self, portfolio_id: str) -> None:
        with self._lock:
            self._store.pop(portfolio_id, None)
