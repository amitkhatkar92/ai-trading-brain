"""iios/investment/company/opportunity/opportunity_history.py
Per-ticker ring-buffer of past OpportunitySnapshot objects.
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Dict, List, Optional

from iios.investment.company.opportunity.opportunity_snapshot import OpportunitySnapshot


_DEFAULT_CAPACITY = 30


class OpportunityHistory:
    """
    Thread-safe, bounded ring-buffer storing historical OpportunitySnapshots
    per ticker. Enables trend analysis, lookback queries, and audit trails.
    """

    def __init__(self, capacity: int = _DEFAULT_CAPACITY) -> None:
        self._capacity = max(1, capacity)
        self._lock     = threading.RLock()
        self._records:  Dict[str, deque] = {}    # ticker → deque[OpportunitySnapshot]

    def record(self, snapshot: OpportunitySnapshot) -> None:
        with self._lock:
            t = snapshot.ticker
            if t not in self._records:
                self._records[t] = deque(maxlen=self._capacity)
            self._records[t].append(snapshot)

    def get_history(self, ticker: str, n: int = 10) -> List[OpportunitySnapshot]:
        """Return the *n* most recent snapshots, newest first."""
        with self._lock:
            buf = self._records.get(ticker)
            if not buf:
                return []
            items = list(buf)
            return items[-n:][::-1]

    def latest(self, ticker: str) -> Optional[OpportunitySnapshot]:
        with self._lock:
            buf = self._records.get(ticker)
            return buf[-1] if buf else None

    def score_series(self, ticker: str, n: int = 10) -> List[float]:
        """Return the last *n* overall scores in chronological order (oldest first)."""
        with self._lock:
            buf = self._records.get(ticker)
            if not buf:
                return []
            items = list(buf)[-n:]
            return [s.overall_score for s in items]

    def count(self, ticker: str) -> int:
        with self._lock:
            buf = self._records.get(ticker)
            return len(buf) if buf else 0

    def known_tickers(self) -> List[str]:
        with self._lock:
            return list(self._records.keys())

    def clear(self, ticker: str) -> None:
        with self._lock:
            self._records.pop(ticker, None)
