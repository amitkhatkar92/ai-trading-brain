"""iios/investment/portfolio/recommendation/recommendation_tracker.py

Thread-safe tracker for active recommendations per portfolio.
"""
from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional

from iios.investment.portfolio.recommendation.recommendation_expiration import (
    filter_expired, is_expired,
)
from iios.investment.portfolio.recommendation.recommendation_types import (
    LifecycleState, RecommendationAction,
)


class RecommendationTracker:
    """
    Thread-safe store of currently active recommendations per portfolio.
    Active means: PUBLISHED, ACTIVE, or MONITORING lifecycle state.
    """

    def __init__(self, max_per_portfolio: int = 10) -> None:
        self._max  = max_per_portfolio
        self._lock = threading.RLock()
        # portfolio_id → list[PortfolioRecommendation]
        self._active: Dict[str, List[Any]] = {}

    def add(self, portfolio_id: str, rec: Any) -> None:
        with self._lock:
            lst = self._active.setdefault(portfolio_id, [])
            # Remove duplicates for the same action (newer wins)
            action = getattr(rec, "action", None)
            self._active[portfolio_id] = [
                r for r in lst if getattr(r, "action", None) != action
            ]
            self._active[portfolio_id].append(rec)
            # Trim to max
            if len(self._active[portfolio_id]) > self._max:
                self._active[portfolio_id] = self._active[portfolio_id][-self._max:]

    def get_active(self, portfolio_id: str) -> List[Any]:
        """Return non-expired active recommendations for a portfolio."""
        with self._lock:
            lst = self._active.get(portfolio_id, [])
            return filter_expired(lst)

    def remove(self, portfolio_id: str, recommendation_id: str) -> None:
        with self._lock:
            lst = self._active.get(portfolio_id, [])
            self._active[portfolio_id] = [
                r for r in lst
                if getattr(r, "recommendation_id", "") != recommendation_id
            ]

    def expire_all(self, portfolio_id: str) -> None:
        """Remove all entries for a portfolio (e.g. after a major update)."""
        with self._lock:
            self._active[portfolio_id] = []

    def has_active(self, portfolio_id: str, action: RecommendationAction) -> bool:
        """Check if there is a non-expired active recommendation for the given action."""
        with self._lock:
            for rec in filter_expired(self._active.get(portfolio_id, [])):
                if getattr(rec, "action", None) == action:
                    return True
            return False

    def count(self, portfolio_id: str) -> int:
        with self._lock:
            return len(filter_expired(self._active.get(portfolio_id, [])))

    def all_portfolio_ids(self) -> List[str]:
        with self._lock:
            return list(self._active.keys())

    def prune_expired(self) -> int:
        """Remove all expired recommendations across all portfolios; return pruned count."""
        pruned = 0
        with self._lock:
            for pid in list(self._active.keys()):
                before = len(self._active[pid])
                self._active[pid] = filter_expired(self._active[pid])
                pruned += before - len(self._active[pid])
        return pruned
