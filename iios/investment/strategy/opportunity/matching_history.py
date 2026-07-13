"""iios/investment/strategy/opportunity/matching_history.py
Thread-safe ring buffer of past MatchResult objects per strategy.
"""
from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Deque, Dict, List, Optional

from iios.investment.strategy.opportunity.strategy_matcher import MatchResult


@dataclass
class MatchRecord:
    result:       MatchResult
    recorded_at:  datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class MatchingHistory:
    """
    Stores the N most recent MatchResult objects per strategy.
    Thread-safe via RLock.
    """

    def __init__(self, max_per_strategy: int = 200) -> None:
        self._max = max_per_strategy
        self._store: Dict[str, Deque[MatchRecord]] = {}
        self._lock = threading.RLock()

    def record(self, result: MatchResult) -> None:
        with self._lock:
            sid = result.strategy_id
            if sid not in self._store:
                self._store[sid] = deque(maxlen=self._max)
            self._store[sid].append(MatchRecord(result=result))

    def latest(self, strategy_id: str) -> Optional[MatchResult]:
        with self._lock:
            buf = self._store.get(strategy_id)
            return buf[-1].result if buf else None

    def history(self, strategy_id: str, n: int = 20) -> List[MatchResult]:
        with self._lock:
            buf = list(self._store.get(strategy_id, []))
            records = buf[-n:]
            return [r.result for r in records]

    def avg_score(self, strategy_id: str) -> float:
        with self._lock:
            buf = list(self._store.get(strategy_id, []))
            if not buf:
                return 0.0
            return sum(r.result.score for r in buf) / len(buf)

    def pass_rate(self, strategy_id: str) -> float:
        with self._lock:
            buf = list(self._store.get(strategy_id, []))
            if not buf:
                return 0.0
            return sum(1 for r in buf if r.result.passed) / len(buf)

    def known_strategies(self) -> List[str]:
        with self._lock:
            return list(self._store.keys())

    def purge(self, strategy_id: str) -> None:
        with self._lock:
            self._store.pop(strategy_id, None)
