"""iios/investment/portfolio/performance/performance_history.py

Per-portfolio bounded history of full PerformanceProfiles.
"""
from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional


class PortfolioPerformanceHistory:
    """
    Thread-safe registry of per-portfolio bounded profile histories.

    Stores arbitrary profile objects (typed PerformanceProfile at runtime).
    Typed as Any to avoid circular imports.
    """

    def __init__(self, max_profiles_per_portfolio: int = 200) -> None:
        self._max  = max_profiles_per_portfolio
        self._lock = threading.RLock()
        self._data: Dict[str, List[Any]] = {}

    def add(self, portfolio_id: str, profile: Any) -> None:
        with self._lock:
            if portfolio_id not in self._data:
                self._data[portfolio_id] = []
            self._data[portfolio_id].append(profile)
            if len(self._data[portfolio_id]) > self._max:
                self._data[portfolio_id] = self._data[portfolio_id][-self._max:]

    def latest(self, portfolio_id: str) -> Optional[Any]:
        with self._lock:
            bucket = self._data.get(portfolio_id, [])
            return bucket[-1] if bucket else None

    def recent(self, portfolio_id: str, n: int) -> List[Any]:
        with self._lock:
            bucket = self._data.get(portfolio_id, [])
            return list(bucket[-n:])

    def best(self, portfolio_id: str) -> Optional[Any]:
        """Return profile with highest overall_performance_score (attr duck-typed)."""
        with self._lock:
            bucket = self._data.get(portfolio_id, [])
            if not bucket:
                return None
            def _key(p: Any) -> float:
                return getattr(p, "overall_performance_score", 0.0)
            return max(bucket, key=_key)

    def count(self, portfolio_id: str) -> int:
        with self._lock:
            return len(self._data.get(portfolio_id, []))

    def all_portfolio_ids(self) -> List[str]:
        with self._lock:
            return list(self._data.keys())

    def clear(self, portfolio_id: str) -> None:
        with self._lock:
            self._data.pop(portfolio_id, None)
