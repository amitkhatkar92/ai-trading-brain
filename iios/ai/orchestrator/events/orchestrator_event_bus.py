"""
orchestrator_event_bus.py -- iios.ai.orchestrator.events
==========================================================
:class:`OrchestratorEventBus` — thread-safe pub/sub event bus.

A10 Enterprise AI Orchestrator — Phase 3, Module 10
"""
from __future__ import annotations

import threading
from collections import defaultdict
from typing import Callable, Dict, List, Optional

from .orchestrator_events import OrchestratorEvent, OrchestratorEventType

SubscriberFn = Callable[[OrchestratorEvent], None]

_WILDCARD = "__ALL__"


class OrchestratorEventBus:
    """
    Thread-safe publish/subscribe event bus for orchestrator events.
    Subscriber exceptions are swallowed to provide isolation.
    """

    MAX_HISTORY = 2000

    def __init__(self) -> None:
        self._lock:        threading.Lock                       = threading.Lock()
        self._subscribers: Dict[str, List[SubscriberFn]]       = defaultdict(list)
        self._history:     List[OrchestratorEvent]              = []

    # ── subscription ─────────────────────────────────────────────────────────

    def subscribe(
        self,
        event_type: OrchestratorEventType,
        handler:    SubscriberFn,
    ) -> None:
        with self._lock:
            self._subscribers[event_type.value].append(handler)

    def subscribe_all(self, handler: SubscriberFn) -> None:
        """Subscribe to every event type."""
        with self._lock:
            self._subscribers[_WILDCARD].append(handler)

    def unsubscribe(
        self,
        event_type: OrchestratorEventType,
        handler:    SubscriberFn,
    ) -> None:
        with self._lock:
            subs = self._subscribers.get(event_type.value, [])
            try:
                subs.remove(handler)
            except ValueError:
                pass

    # ── publishing ────────────────────────────────────────────────────────────

    def publish(self, event: OrchestratorEvent) -> None:
        """Dispatch *event* to all matching subscribers.  Never raises."""
        with self._lock:
            specific = list(self._subscribers.get(event.event_type.value, []))
            wildcard = list(self._subscribers.get(_WILDCARD, []))
            self._history.append(event)
            if len(self._history) > self.MAX_HISTORY:
                self._history.pop(0)

        for handler in specific + wildcard:
            try:
                handler(event)
            except Exception:
                pass

    # ── history ───────────────────────────────────────────────────────────────

    def history(
        self,
        event_type: Optional[OrchestratorEventType] = None,
        limit:      int = 100,
    ) -> List[OrchestratorEvent]:
        with self._lock:
            events = list(self._history)
        if event_type is not None:
            events = [e for e in events if e.event_type == event_type]
        return events[-limit:]

    def clear_history(self) -> None:
        with self._lock:
            self._history.clear()

    def total_count(self) -> int:
        with self._lock:
            return len(self._history)
