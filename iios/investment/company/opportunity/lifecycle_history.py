"""iios/investment/company/opportunity/lifecycle_history.py
Per-ticker ring-buffer of full lifecycle change records.
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Dict, List, Optional

from iios.investment.company.opportunity.opportunity_lifecycle import LifecycleChange
from iios.investment.company.opportunity.opportunity_profile import OpportunityLifecycle


_DEFAULT_CAPACITY = 100


class LifecycleHistory:
    """
    Thread-safe global store for all lifecycle transitions, searchable by ticker.
    Useful for audit trails and historical replay.
    """

    def __init__(self, capacity: int = _DEFAULT_CAPACITY) -> None:
        self._capacity = max(1, capacity)
        self._lock     = threading.RLock()
        self._records:  Dict[str, deque] = {}   # ticker → deque[LifecycleChange]
        self._global:   deque = deque(maxlen=capacity * 10)  # global audit log

    def record(self, ticker: str, change: LifecycleChange) -> None:
        with self._lock:
            if ticker not in self._records:
                self._records[ticker] = deque(maxlen=self._capacity)
            self._records[ticker].append(change)
            self._global.append((ticker, change))

    def get_ticker_history(self, ticker: str, n: int = 20) -> List[LifecycleChange]:
        with self._lock:
            buf = self._records.get(ticker, deque())
            items = list(buf)
            return items[-n:][::-1]   # most-recent first

    def get_transitions_to(
        self, target: OpportunityLifecycle, n: int = 50
    ) -> List[LifecycleChange]:
        with self._lock:
            return [
                change
                for _, change in list(self._global)[-n * 5 :]
                if change.to_state == target
            ][-n:]

    def count_transitions(self, ticker: str) -> int:
        with self._lock:
            return len(self._records.get(ticker, []))

    def latest(self, ticker: str) -> Optional[LifecycleChange]:
        with self._lock:
            buf = self._records.get(ticker)
            return buf[-1] if buf else None

    def known_tickers(self) -> List[str]:
        with self._lock:
            return list(self._records.keys())
