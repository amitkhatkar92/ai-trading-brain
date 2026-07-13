"""iios/investment/company/integration/aggregation_history.py
Thread-safe ring buffer of CompanyIntelligenceSnapshot per ticker.
"""
from __future__ import annotations

import threading
from collections import deque
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_DEFAULT_MAXLEN = 50   # snapshots per ticker


class AggregationHistory:
    """
    Global store of historical CompanyIntelligenceSnapshot objects, keyed by ticker.
    Each ticker has an independent fixed-size ring buffer.
    """

    def __init__(self, maxlen: int = _DEFAULT_MAXLEN) -> None:
        self._lock   = threading.RLock()
        self._maxlen = maxlen
        self._store: Dict[str, deque] = {}   # ticker → deque[snapshot]

    # ── Mutation ──────────────────────────────────────────────────────────────

    def record(self, snapshot: Any) -> None:
        """Append *snapshot* to the ticker's ring buffer."""
        ticker = getattr(snapshot, "ticker", None)
        if not ticker:
            return
        with self._lock:
            if ticker not in self._store:
                self._store[ticker] = deque(maxlen=self._maxlen)
            self._store[ticker].append(snapshot)

    # ── Read access ───────────────────────────────────────────────────────────

    def get_history(
        self,
        ticker: str,
        n: int = 10,
    ) -> List[Any]:
        """Return up to *n* most-recent snapshots (newest first)."""
        with self._lock:
            buf = self._store.get(ticker, deque())
            snaps = list(buf)
            return snaps[-n:][::-1]

    def latest(self, ticker: str) -> Optional[Any]:
        with self._lock:
            buf = self._store.get(ticker, deque())
            return buf[-1] if buf else None

    def count(self, ticker: str) -> int:
        with self._lock:
            return len(self._store.get(ticker, deque()))

    def known_tickers(self) -> List[str]:
        with self._lock:
            return list(self._store.keys())

    def clear_ticker(self, ticker: str) -> None:
        with self._lock:
            self._store.pop(ticker, None)

    # ── Score trend helpers ───────────────────────────────────────────────────

    def score_series(self, ticker: str, n: int = 10) -> List[float]:
        """
        Return the last *n* overall scores (oldest first) for trend analysis.
        """
        with self._lock:
            buf = self._store.get(ticker, deque())
            snaps = list(buf)[-n:]
            return [getattr(s, "overall_score", 0.0) for s in snaps]

    def score_trend(self, ticker: str) -> float:
        """
        Simple trend: latest minus oldest from the last 5 snapshots.
        Positive = improving, negative = deteriorating.
        """
        series = self.score_series(ticker, n=5)
        if len(series) < 2:
            return 0.0
        return series[-1] - series[0]
