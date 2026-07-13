"""iios/investment/strategy/core/execution_history.py
Ring-buffer execution session history for institutional strategies.

Named ExecutionHistory (not StrategyHistory) to avoid collision with the
existing core/strategy_history.py which tracks StrategySnapshot objects
for the strategy intelligence / evaluation subsystem.
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Deque, Dict, List, Optional

from .strategy_session import StrategySession


class ExecutionHistory:
    """
    Thread-safe ring buffer of StrategySession records.
    Maintains per-strategy buckets with aggregate statistics.
    """

    def __init__(self, max_sessions: int = 200) -> None:
        self._max = max_sessions
        self._lock = threading.RLock()
        self._sessions: Dict[str, Deque[StrategySession]] = {}
        self._total_count: Dict[str, int] = {}

    def record(self, session: StrategySession) -> None:
        with self._lock:
            sid = session.strategy_id
            if sid not in self._sessions:
                self._sessions[sid] = deque(maxlen=self._max)
                self._total_count[sid] = 0
            self._sessions[sid].append(session)
            self._total_count[sid] += 1

    def for_strategy(
        self, strategy_id: str, n: int = 50
    ) -> List[StrategySession]:
        with self._lock:
            buf = self._sessions.get(strategy_id, deque())
            return list(buf)[-n:]

    def latest(self, strategy_id: str) -> Optional[StrategySession]:
        with self._lock:
            buf = self._sessions.get(strategy_id, deque())
            return buf[-1] if buf else None

    def total_sessions(self, strategy_id: str) -> int:
        with self._lock:
            return self._total_count.get(strategy_id, 0)

    def success_rate(self, strategy_id: str, n: int = 50) -> float:
        sessions = self.for_strategy(strategy_id, n)
        if not sessions:
            return 0.0
        return sum(1 for s in sessions if s.succeeded) / len(sessions)

    def average_latency_ms(self, strategy_id: str, n: int = 50) -> float:
        sessions = self.for_strategy(strategy_id, n)
        completed = [s for s in sessions if s.is_complete]
        if not completed:
            return 0.0
        return sum(s.duration_ms for s in completed) / len(completed)

    def known_strategies(self) -> List[str]:
        with self._lock:
            return list(self._sessions.keys())
