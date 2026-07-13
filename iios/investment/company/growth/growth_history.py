"""iios/investment/company/growth/growth_history.py
Ring buffer for GrowthSnapshot history per ticker.
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Dict, List, Optional

from iios.investment.company.growth.growth_snapshot import GrowthSnapshot


class GrowthHistory:
    """Thread-safe per-ticker growth history."""

    def __init__(self, max_snapshots: int = 20) -> None:
        self._lock  = threading.RLock()
        self._store: Dict[str, deque] = {}
        self._max   = max_snapshots

    def push(self, ticker: str, snapshot: GrowthSnapshot) -> None:
        with self._lock:
            q = self._store.setdefault(ticker, deque(maxlen=self._max))
            q.append(snapshot)

    def get_latest(self, ticker: str) -> Optional[GrowthSnapshot]:
        with self._lock:
            q = self._store.get(ticker)
            return q[-1] if q else None

    def get_history(self, ticker: str, n: int = 10) -> List[GrowthSnapshot]:
        with self._lock:
            q = self._store.get(ticker)
            return list(q)[-n:] if q else []

    def depth(self, ticker: str) -> int:
        with self._lock:
            return len(self._store.get(ticker, []))

    def all_tickers(self) -> List[str]:
        with self._lock:
            return list(self._store.keys())
