"""iios/investment/strategy/core/event_history.py
Thread-safe ring-buffer history of institutional strategy events.
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Callable, Deque, Dict, List, Optional

from .strategy_events import StrategyEvent, StrategyEventType


class EventHistory:
    """
    Thread-safe ring buffer of StrategyEvent records.
    Maintains per-strategy buckets and a global ring buffer.
    """

    def __init__(
        self,
        max_per_strategy: int = 500,
        max_global: int = 5_000,
    ) -> None:
        self._max_per = max_per_strategy
        self._max_global = max_global
        self._lock = threading.RLock()
        self._by_strategy: Dict[str, Deque[StrategyEvent]] = {}
        self._global: Deque[StrategyEvent] = deque(maxlen=max_global)

    def record(self, event: StrategyEvent) -> None:
        with self._lock:
            if event.strategy_id not in self._by_strategy:
                self._by_strategy[event.strategy_id] = deque(maxlen=self._max_per)
            self._by_strategy[event.strategy_id].append(event)
            self._global.append(event)

    def for_strategy(
        self,
        strategy_id: str,
        n: int = 50,
        event_type: Optional[StrategyEventType] = None,
    ) -> List[StrategyEvent]:
        with self._lock:
            buf = list(self._by_strategy.get(strategy_id, deque()))
        if event_type is not None:
            buf = [e for e in buf if e.event_type == event_type]
        return buf[-n:]

    def recent(self, n: int = 100) -> List[StrategyEvent]:
        with self._lock:
            return list(self._global)[-n:]

    def filter(
        self,
        predicate: Callable[[StrategyEvent], bool],
        n: int = 200,
    ) -> List[StrategyEvent]:
        with self._lock:
            events = list(self._global)
        return [e for e in events if predicate(e)][-n:]

    def clear(self, strategy_id: Optional[str] = None) -> None:
        with self._lock:
            if strategy_id:
                self._by_strategy.pop(strategy_id, None)
            else:
                self._by_strategy.clear()
                self._global.clear()

    def total_count(self) -> int:
        with self._lock:
            return len(self._global)

    def strategy_count(self, strategy_id: str) -> int:
        with self._lock:
            return len(self._by_strategy.get(strategy_id, []))
