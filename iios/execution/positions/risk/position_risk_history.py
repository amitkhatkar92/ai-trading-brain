"""iios/execution/positions/risk/position_risk_history.py
==================================================
RiskHistory — bounded list of RiskEvent objects for a single position
or the entire risk subsystem.

C6 Execution Intelligence — Phase 3, Module 4
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Callable, List, Optional, Sequence

from .position_risk_events import RiskEvent


_DEFAULT_MAX_EVENTS = 1_000


class RiskHistory:
    """
    Thread-safe, bounded circular history of ``RiskEvent`` objects.

    ``max_events`` caps memory usage. When full, oldest entries are dropped.
    """

    def __init__(self, max_events: int = _DEFAULT_MAX_EVENTS) -> None:
        if max_events < 1:
            raise ValueError(f"max_events must be >= 1, got {max_events}")
        self._max_events = max_events
        self._events: deque[RiskEvent] = deque(maxlen=max_events)
        self._lock = threading.Lock()

    # ── Mutation ──────────────────────────────────────────────────────────────

    def append(self, event: RiskEvent) -> None:
        with self._lock:
            self._events.append(event)

    def extend(self, events: Sequence[RiskEvent]) -> None:
        with self._lock:
            for e in events:
                self._events.append(e)

    def clear(self) -> None:
        with self._lock:
            self._events.clear()

    # ── Queries ───────────────────────────────────────────────────────────────

    def all(self) -> List[RiskEvent]:
        with self._lock:
            return list(self._events)

    def latest(self, n: int = 10) -> List[RiskEvent]:
        with self._lock:
            events = list(self._events)
        return events[-n:]

    def for_position(self, position_id: str) -> List[RiskEvent]:
        with self._lock:
            return [e for e in self._events if e.position_id == position_id]

    def filter(self, predicate: Callable[[RiskEvent], bool]) -> List[RiskEvent]:
        with self._lock:
            return [e for e in self._events if predicate(e)]

    def count(self) -> int:
        with self._lock:
            return len(self._events)

    @property
    def max_events(self) -> int:
        return self._max_events

    def is_empty(self) -> bool:
        with self._lock:
            return len(self._events) == 0

    def __len__(self) -> int:
        with self._lock:
            return len(self._events)
