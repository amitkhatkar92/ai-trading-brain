"""iios/investment/strategy/integration/quality_history.py
Append-only store of historical QualityReports.
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from iios.investment.strategy.integration.strategy_quality import QualityReport


class QualityHistory:
    """Thread-safe append-only store of QualityReports."""

    def __init__(self, max_size: int = 50_000) -> None:
        self._lock:  threading.RLock  = threading.RLock()
        self._store: List[QualityReport] = []
        self._max    = max_size

    def record(self, report: QualityReport) -> None:
        with self._lock:
            if len(self._store) >= self._max:
                self._store.pop(0)
            self._store.append(report)

    def for_strategy(self, strategy_id: str) -> List[QualityReport]:
        with self._lock:
            return [r for r in self._store if r.strategy_id == strategy_id]

    def recent(self, n: int = 50) -> List[QualityReport]:
        with self._lock:
            return self._store[-n:]

    def trend(self, strategy_id: str, n: int = 10) -> List[float]:
        """Returns the last n overall_scores for a strategy (oldest first)."""
        rpts = self.for_strategy(strategy_id)
        return [r.overall_score for r in rpts[-n:]]

    def count(self) -> int:
        with self._lock:
            return len(self._store)
