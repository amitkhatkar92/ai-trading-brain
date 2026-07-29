"""
agent_event_bus.py -- iios.ai.agent_framework.events
=====================================================
:class:`AgentEventBus` — thread-safe publish/subscribe bus for A5 events.

Mirrors the pattern used in A4's ``MemoryEventBus``.

A5 AI Agent Framework — Phase 3, Module 5
"""
from __future__ import annotations

import threading
from collections import defaultdict
from typing import Callable, Dict, List, Set

from .agent_events import AgentEvent, AgentEventType


Handler = Callable[[AgentEvent], None]


class AgentEventBus:
    """
    Thread-safe publish/subscribe bus for :class:`AgentEvent` objects.

    Handlers are invoked synchronously in the publishing thread.  Any
    exception raised by a handler is swallowed and logged so that one
    broken handler cannot disrupt others.
    """

    def __init__(self) -> None:
        self._lock:             threading.Lock                              = threading.Lock()
        self._handlers:         Dict[AgentEventType, Set[Handler]]         = defaultdict(set)
        self._published_count:  int                                         = 0

    # ── Subscribe / unsubscribe ───────────────────────────────────────────────

    def subscribe(self, event_type: AgentEventType, handler: Handler) -> None:
        """Register *handler* to receive events of *event_type*."""
        with self._lock:
            self._handlers[event_type].add(handler)

    def unsubscribe(self, event_type: AgentEventType, handler: Handler) -> None:
        """Remove *handler* from *event_type*.  No-op if not registered."""
        with self._lock:
            self._handlers[event_type].discard(handler)

    # ── Publish ───────────────────────────────────────────────────────────────

    def publish(self, event: AgentEvent) -> None:
        """
        Dispatch *event* to all registered handlers.

        Thread-safe.  Handlers are called outside the lock to prevent
        deadlocks if a handler publishes further events.
        """
        with self._lock:
            handlers = list(self._handlers.get(event.event_type, []))
            self._published_count += 1

        for handler in handlers:
            try:
                handler(event)
            except Exception:  # noqa: BLE001
                pass  # isolated — do not let one handler break others

    # ── Introspection ─────────────────────────────────────────────────────────

    def subscriber_count(self, event_type: AgentEventType) -> int:
        """Return the number of handlers for *event_type*."""
        with self._lock:
            return len(self._handlers.get(event_type, set()))

    def clear(self) -> None:
        """Remove all handlers.  Useful in tests."""
        with self._lock:
            self._handlers.clear()

    @property
    def published_count(self) -> int:
        """Total events published since this bus was created or cleared."""
        return self._published_count
