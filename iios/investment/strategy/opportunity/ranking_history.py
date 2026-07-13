"""iios/investment/strategy/opportunity/ranking_history.py
Thread-safe ring buffer of RankingScore history per strategy.
"""
from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Deque, Dict, List, Optional

from iios.investment.strategy.opportunity.ranking_score import RankingScore


@dataclass
class RankRecord:
    score:       RankingScore
    recorded_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class RankingHistory:
    """Stores the N most recent RankingScore objects per strategy."""

    def __init__(self, max_per_strategy: int = 200) -> None:
        self._max   = max_per_strategy
        self._store: Dict[str, Deque[RankRecord]] = {}
        self._lock  = threading.RLock()

    def record(self, score: RankingScore) -> None:
        with self._lock:
            sid = score.strategy_id
            if sid not in self._store:
                self._store[sid] = deque(maxlen=self._max)
            self._store[sid].append(RankRecord(score=score))

    def latest(self, strategy_id: str) -> Optional[RankingScore]:
        with self._lock:
            buf = self._store.get(strategy_id)
            return buf[-1].score if buf else None

    def history(self, strategy_id: str, n: int = 20) -> List[RankingScore]:
        with self._lock:
            buf = list(self._store.get(strategy_id, []))
            return [r.score for r in buf[-n:]]

    def avg_score(self, strategy_id: str) -> float:
        with self._lock:
            buf = list(self._store.get(strategy_id, []))
            return sum(r.score.overall_score for r in buf) / len(buf) if buf else 0.0

    def best_rank(self, strategy_id: str) -> int:
        with self._lock:
            buf = list(self._store.get(strategy_id, []))
            ranks = [r.score.rank for r in buf if r.score.rank > 0]
            return min(ranks) if ranks else 0

    def known_strategies(self) -> List[str]:
        with self._lock:
            return list(self._store.keys())

    def purge(self, strategy_id: str) -> None:
        with self._lock:
            self._store.pop(strategy_id, None)
