"""iios/investment/portfolio/integration/quality_history.py

Bounded per-portfolio quality assessment history.
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Dict, List, Optional

from iios.investment.portfolio.integration.quality_statistics import QualityRunMetric


class QualityHistory:
    """Thread-safe bounded history of quality assessments per portfolio."""

    def __init__(self, max_per_portfolio: int = 100) -> None:
        self._max  = max_per_portfolio
        self._lock = threading.RLock()
        self._store: Dict[str, deque] = {}

    def add(self, portfolio_id: str, metric: QualityRunMetric) -> None:
        with self._lock:
            if portfolio_id not in self._store:
                self._store[portfolio_id] = deque(maxlen=self._max)
            self._store[portfolio_id].appendleft(metric)

    def recent(self, portfolio_id: str, n: int = 10) -> List[QualityRunMetric]:
        with self._lock:
            return list(self._store.get(portfolio_id, deque()))[:n]

    def latest(self, portfolio_id: str) -> Optional[QualityRunMetric]:
        results = self.recent(portfolio_id, 1)
        return results[0] if results else None

    def trend(self, portfolio_id: str, n: int = 10) -> List[float]:
        """Return quality scores oldest-first for trend analysis."""
        return [r.overall_score for r in reversed(self.recent(portfolio_id, n))]

    def all_portfolio_ids(self) -> List[str]:
        with self._lock:
            return list(self._store.keys())
