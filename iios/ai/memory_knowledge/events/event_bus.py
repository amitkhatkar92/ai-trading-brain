"""
event_bus.py -- iios.ai.memory_knowledge.events
================================================
:class:`MemoryEventBus` — thread-safe publish/subscribe bus for A4 events.
Independent of A1's AIEventBus.
"""
from __future__ import annotations

import threading
from typing import Callable, Dict, List

from .event_types  import MemoryEventType
from .memory_events import MemoryEvent

Handler = Callable[[MemoryEvent], None]


class MemoryEventBus:
    """Thread-safe pub/sub event bus for A4 memory & knowledge events."""

    def __init__(self) -> None:
        self._lock:      threading.Lock                       = threading.Lock()
        self._handlers:  Dict[MemoryEventType, List[Handler]] = {}
        self._published: int                                  = 0

    # ── Subscription ──────────────────────────────────────────────────────────

    def subscribe(self, event_type: MemoryEventType, handler: Handler) -> None:
        with self._lock:
            self._handlers.setdefault(event_type, []).append(handler)

    def unsubscribe(self, event_type: MemoryEventType, handler: Handler) -> None:
        with self._lock:
            handlers = self._handlers.get(event_type, [])
            if handler in handlers:
                handlers.remove(handler)

    # ── Publishing ────────────────────────────────────────────────────────────

    def publish(self, event: MemoryEvent) -> None:
        with self._lock:
            handlers = list(self._handlers.get(event.event_type, []))
            self._published += 1
        for handler in handlers:
            try:
                handler(event)
            except Exception:  # noqa: BLE001
                pass  # handlers must not crash the bus

    # ── Introspection ─────────────────────────────────────────────────────────

    def subscriber_count(self, event_type: MemoryEventType) -> int:
        with self._lock:
            return len(self._handlers.get(event_type, []))

    def clear(self) -> None:
        with self._lock:
            self._handlers.clear()

    @property
    def published_count(self) -> int:
        with self._lock:
            return self._published
