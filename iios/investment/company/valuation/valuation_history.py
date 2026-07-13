"""iios/investment/company/valuation/valuation_history.py
Valuation history ring buffer — one snapshot per ticker.
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Dict, List, Optional

from iios.investment.company.valuation.valuation_snapshot import ValuationSnapshot


class ValuationHistory:
    """Thread-safe per-ticker valuation history."""

    def __init__(self, max_snapshots: int = 20) -> None:
        self._lock  = threading.RLock()
        self._store: Dict[str, deque] = {}
        self._max   = max_snapshots

    def push(self, ticker: str, snapshot: ValuationSnapshot) -> None:
        with self._lock:
            q = self._store.setdefault(ticker, deque(maxlen=self._max))
            q.append(snapshot)

    def get_latest(self, ticker: str) -> Optional[ValuationSnapshot]:
        with self._lock:
            q = self._store.get(ticker)
            return q[-1] if q else None

    def get_history(self, ticker: str, n: int = 10) -> List[ValuationSnapshot]:
        with self._lock:
            q = self._store.get(ticker)
            if not q:
                return []
            return list(q)[-n:]

    def depth(self, ticker: str) -> int:
        with self._lock:
            return len(self._store.get(ticker, []))

    def all_tickers(self) -> List[str]:
        with self._lock:
            return list(self._store.keys())
