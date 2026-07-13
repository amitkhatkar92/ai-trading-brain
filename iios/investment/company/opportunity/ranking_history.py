"""iios/investment/company/opportunity/ranking_history.py
Per-ticker ring-buffer of past ranking positions.
"""
from __future__ import annotations

import threading
from collections import deque
from datetime import datetime, timezone
from typing import Dict, List, Optional

from iios.investment.company.opportunity.ranking_score import RankingChange, RankingResult


_DEFAULT_CAPACITY = 50


class RankingHistory:
    """
    Thread-safe ring-buffer of RankingResult objects per ticker.
    Supports up to *capacity* records per ticker.
    """

    def __init__(self, capacity: int = _DEFAULT_CAPACITY) -> None:
        self._capacity = max(1, capacity)
        self._lock     = threading.RLock()
        self._records:  Dict[str, deque] = {}   # ticker → deque[RankingResult]
        self._changes:  Dict[str, deque] = {}   # ticker → deque[RankingChange]

    def record(self, result: RankingResult, previous_rank: Optional[int] = None) -> None:
        with self._lock:
            t = result.ticker
            if t not in self._records:
                self._records[t] = deque(maxlen=self._capacity)
                self._changes[t] = deque(maxlen=self._capacity)
            prev_result = self._records[t][-1] if self._records[t] else None
            self._records[t].append(result)
            if prev_result is not None or previous_rank is not None:
                old_rank = previous_rank if previous_rank is not None else (
                    prev_result.global_rank if prev_result else None
                )
                change = RankingChange(
                    ticker=t,
                    from_rank=old_rank,
                    to_rank=result.global_rank,
                    score_change=result.score - (prev_result.score if prev_result else result.score),
                    changed_at=datetime.now(timezone.utc),
                )
                self._changes[t].append(change)

    def get_history(self, ticker: str, n: int = 10) -> List[RankingResult]:
        with self._lock:
            buf = self._records.get(ticker)
            if not buf:
                return []
            items = list(buf)
            return items[-n:][::-1]   # most-recent first

    def get_changes(self, ticker: str, n: int = 10) -> List[RankingChange]:
        with self._lock:
            buf = self._changes.get(ticker)
            if not buf:
                return []
            items = list(buf)
            return items[-n:][::-1]

    def latest(self, ticker: str) -> Optional[RankingResult]:
        with self._lock:
            buf = self._records.get(ticker)
            return buf[-1] if buf else None

    def known_tickers(self) -> List[str]:
        with self._lock:
            return list(self._records.keys())
