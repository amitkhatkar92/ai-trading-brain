"""iios/investment/strategy/debate/debate_history.py
Append-only, thread-safe history of completed debate sessions.
"""
from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Dict, List, Optional

from iios.investment.strategy.debate.debate_session import DebateSession


class DebateHistory:
    """Thread-safe append-only store of DebateSession records."""

    def __init__(self, max_size: int = 10_000) -> None:
        self._lock     = threading.RLock()
        self._store:   Dict[str, DebateSession] = {}
        self._order:   List[str]               = []
        self._max      = max_size

    def record(self, session: DebateSession) -> None:
        with self._lock:
            sid = session.session_id
            if sid not in self._store:
                if len(self._order) >= self._max:
                    evicted = self._order.pop(0)
                    del self._store[evicted]
                self._store[sid] = session
                self._order.append(sid)

    def get(self, session_id: str) -> Optional[DebateSession]:
        with self._lock:
            return self._store.get(session_id)

    def by_strategy(self, strategy_id: str) -> List[DebateSession]:
        with self._lock:
            result = []
            for s in self._store.values():
                if s.context.strategy and s.context.strategy.strategy_id == strategy_id:
                    result.append(s)
            return result

    def by_opportunity(self, opportunity_id: str) -> List[DebateSession]:
        with self._lock:
            result = []
            for s in self._store.values():
                if s.context.opportunity and s.context.opportunity.opportunity_id == opportunity_id:
                    result.append(s)
            return result

    def by_symbol(self, symbol: str) -> List[DebateSession]:
        with self._lock:
            return [s for s in self._store.values() if s.context.symbol == symbol]

    def recent(self, n: int = 20) -> List[DebateSession]:
        with self._lock:
            return [self._store[sid] for sid in self._order[-n:]]

    def all(self) -> List[DebateSession]:
        with self._lock:
            return list(self._store.values())

    def count(self) -> int:
        with self._lock:
            return len(self._store)
