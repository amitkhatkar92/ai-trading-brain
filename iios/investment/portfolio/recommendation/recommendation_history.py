"""iios/investment/portfolio/recommendation/recommendation_history.py

Per-portfolio bounded history of full PortfolioRecommendation objects.
"""
from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional


class PortfolioRecommendationHistory:
    """
    Thread-safe bounded per-portfolio history of PortfolioRecommendation objects.
    Accepts duck-typed plan objects.
    """

    def __init__(self, max_per_portfolio: int = 50) -> None:
        self._max   = max_per_portfolio
        self._lock  = threading.RLock()
        self._store: Dict[str, List[Any]] = {}   # pid → list[PortfolioRecommendation]

    def add(self, portfolio_id: str, rec: Any) -> None:
        with self._lock:
            if portfolio_id not in self._store:
                self._store[portfolio_id] = []
            self._store[portfolio_id].append(rec)
            if len(self._store[portfolio_id]) > self._max:
                self._store[portfolio_id] = self._store[portfolio_id][-self._max:]

    def latest(self, portfolio_id: str) -> Optional[Any]:
        with self._lock:
            recs = self._store.get(portfolio_id)
            return recs[-1] if recs else None

    def recent(self, portfolio_id: str, n: int = 5) -> List[Any]:
        with self._lock:
            return list(self._store.get(portfolio_id, [])[-n:])

    def best(self, portfolio_id: str) -> Optional[Any]:
        with self._lock:
            recs = self._store.get(portfolio_id)
            if not recs:
                return None
            return max(recs, key=lambda r: getattr(r, "recommendation_score", 0.0))

    def count(self, portfolio_id: str) -> int:
        with self._lock:
            return len(self._store.get(portfolio_id, []))

    def all_portfolio_ids(self) -> List[str]:
        with self._lock:
            return list(self._store.keys())

    def clear(self, portfolio_id: str) -> None:
        with self._lock:
            self._store.pop(portfolio_id, None)

    def latest_by_action(self, portfolio_id: str, action_value: str) -> Optional[Any]:
        """Return most recent recommendation with the given action value."""
        with self._lock:
            recs = self._store.get(portfolio_id, [])
            for rec in reversed(recs):
                act = getattr(rec, "action", None)
                if act is not None and getattr(act, "value", act) == action_value:
                    return rec
            return None
