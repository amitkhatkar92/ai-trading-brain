"""iios/investment/portfolio/risk/portfolio_risk_history.py

Portfolio risk history: manages per-portfolio bounded history of full
PortfolioRiskProfile objects (more detailed than the lightweight RiskRecord
in portfolio_risk_snapshot.py).
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from iios.investment.portfolio.risk.portfolio_risk_profile import PortfolioRiskProfile


class PortfolioRiskHistory:
    """
    Thread-safe, bounded history of full PortfolioRiskProfile objects.

    Maintains separate history per portfolio_id.
    """

    def __init__(self, max_per_portfolio: int = 100) -> None:
        self._max   = max_per_portfolio
        self._lock  = threading.RLock()
        self._store: Dict[str, List[PortfolioRiskProfile]] = {}

    def record(self, profile: PortfolioRiskProfile) -> None:
        pid = profile.portfolio_id
        with self._lock:
            if pid not in self._store:
                self._store[pid] = []
            self._store[pid].append(profile)
            if len(self._store[pid]) > self._max:
                self._store[pid] = self._store[pid][-self._max:]

    def latest(self, portfolio_id: str) -> Optional[PortfolioRiskProfile]:
        with self._lock:
            records = self._store.get(portfolio_id, [])
            return records[-1] if records else None

    def all(self, portfolio_id: str, n: Optional[int] = None) -> List[PortfolioRiskProfile]:
        with self._lock:
            records = self._store.get(portfolio_id, [])
            if n is None:
                return list(records)
            return list(records[-n:])

    def best(self, portfolio_id: str) -> Optional[PortfolioRiskProfile]:
        with self._lock:
            records = self._store.get(portfolio_id, [])
            return min(records, key=lambda p: p.overall_risk_score) if records else None

    def portfolio_ids(self) -> List[str]:
        with self._lock:
            return list(self._store.keys())

    def clear(self, portfolio_id: str) -> None:
        with self._lock:
            self._store.pop(portfolio_id, None)
