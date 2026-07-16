"""iios/execution/positions/integration/position_integration_history.py
==================================================
IntegrationHistory — bounded, thread-safe event history for the
Position Integration subsystem.

C6 Execution Intelligence — Phase 3, Module 6
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Callable, List, Optional

from .constants import DEFAULT_MAX_HISTORY, IntegrationEventType
from .position_integration_events import IntegrationEvent


class IntegrationHistory:
    """
    Bounded, thread-safe deque of :class:`IntegrationEvent` objects.

    When the history reaches ``max_events`` capacity, the oldest entry
    is evicted automatically (deque FIFO semantics with ``maxlen``).
    """

    def __init__(self, max_events: int = DEFAULT_MAX_HISTORY) -> None:
        if max_events < 1:
            raise ValueError(f"max_events must be ≥ 1, got {max_events}")
        self._q:    deque[IntegrationEvent] = deque(maxlen=max_events)
        self._lock: threading.Lock          = threading.Lock()

    # ── Write ─────────────────────────────────────────────────────────────────

    def append(self, event: IntegrationEvent) -> None:
        with self._lock:
            self._q.append(event)

    def extend(self, events: List[IntegrationEvent]) -> None:
        with self._lock:
            for e in events:
                self._q.append(e)

    def clear(self) -> None:
        with self._lock:
            self._q.clear()

    # ── Read ──────────────────────────────────────────────────────────────────

    def all(self) -> List[IntegrationEvent]:
        with self._lock:
            return list(self._q)

    def latest(self, n: int = 10) -> List[IntegrationEvent]:
        """Return up to *n* most recent events."""
        with self._lock:
            events = list(self._q)
        return events[-n:] if n < len(events) else events

    def for_type(self, event_type: IntegrationEventType) -> List[IntegrationEvent]:
        with self._lock:
            return [e for e in self._q if e.event_type == event_type]

    def for_component(self, component: str) -> List[IntegrationEvent]:
        with self._lock:
            return [e for e in self._q if e.component == component]

    def filter(self, predicate: Callable[[IntegrationEvent], bool]) -> List[IntegrationEvent]:
        with self._lock:
            return [e for e in self._q if predicate(e)]

    def count(self) -> int:
        with self._lock:
            return len(self._q)

    def is_empty(self) -> bool:
        with self._lock:
            return len(self._q) == 0

    def __len__(self) -> int:
        with self._lock:
            return len(self._q)
