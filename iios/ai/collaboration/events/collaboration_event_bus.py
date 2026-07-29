"""
collaboration_event_bus.py -- iios.ai.collaboration.events
===========================================================
:class:`CollaborationEventBus` — thread-safe pub/sub bus for A6 events.

Mirrors the pattern from A5's ``AgentEventBus``.

A6 Multi-Agent Collaboration Framework — Phase 3, Module 6
"""
from __future__ import annotations

import threading
from collections import defaultdict
from typing import Callable, Dict, Set

from .collaboration_events import CollaborationEvent, CollaborationEventType


Handler = Callable[[CollaborationEvent], None]


class CollaborationEventBus:
    """
    Thread-safe publish/subscribe bus for :class:`CollaborationEvent` objects.

    Handler exceptions are swallowed so one broken handler cannot disrupt others.
    """

    def __init__(self) -> None:
        self._lock:            threading.Lock                                    = threading.Lock()
        self._handlers:        Dict[CollaborationEventType, Set[Handler]]        = defaultdict(set)
        self._published_count: int                                               = 0

    def subscribe(self, event_type: CollaborationEventType, handler: Handler) -> None:
        with self._lock:
            self._handlers[event_type].add(handler)

    def unsubscribe(self, event_type: CollaborationEventType, handler: Handler) -> None:
        with self._lock:
            self._handlers[event_type].discard(handler)

    def publish(self, event: CollaborationEvent) -> None:
        with self._lock:
            handlers = list(self._handlers.get(event.event_type, []))
            self._published_count += 1
        for handler in handlers:
            try:
                handler(event)
            except Exception:  # noqa: BLE001
                pass

    def subscriber_count(self, event_type: CollaborationEventType) -> int:
        with self._lock:
            return len(self._handlers.get(event_type, set()))

    def clear(self) -> None:
        with self._lock:
            self._handlers.clear()

    @property
    def published_count(self) -> int:
        return self._published_count
