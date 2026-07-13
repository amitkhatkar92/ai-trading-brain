"""iios/investment/company/ownership/ownership_history.py
Ring-buffer ownership history store — thread-safe.
"""
from __future__ import annotations

import threading
from collections import deque
from typing import List, Optional


_MAX_HISTORY = 20   # maximum snapshots kept per ticker


class OwnershipHistory:
    """
    Thread-safe ring-buffer of OwnershipSnapshot objects keyed by ticker.
    One entry per ingest() call; oldest entries are evicted automatically.
    """

    def __init__(self, max_per_ticker: int = _MAX_HISTORY) -> None:
        self._max = max_per_ticker
        self._lock = threading.RLock()
        self._data: dict[str, deque] = {}

    def push(self, ticker: str, snapshot: object) -> None:
        with self._lock:
            if ticker not in self._data:
                self._data[ticker] = deque(maxlen=self._max)
            self._data[ticker].appendleft(snapshot)

    def get_latest(self, ticker: str) -> Optional[object]:
        with self._lock:
            buf = self._data.get(ticker)
            if buf:
                return buf[0]
            return None

    def get_history(self, ticker: str, n: int = _MAX_HISTORY) -> List[object]:
        with self._lock:
            buf = self._data.get(ticker)
            if not buf:
                return []
            return list(buf)[:n]

    def all_tickers(self) -> List[str]:
        with self._lock:
            return list(self._data.keys())

    def ticker_count(self) -> int:
        with self._lock:
            return len(self._data)

    def snapshot_count(self, ticker: str) -> int:
        with self._lock:
            buf = self._data.get(ticker)
            return len(buf) if buf else 0
