"""
capability_event_bus.py -- iios.ai.capability.events
======================================================
:class:`CapabilityEventBus` — thread-safe pub/sub event bus.

A9 Enterprise Capability Platform — Phase 3, Module 9
"""
from __future__ import annotations

import threading
from collections import defaultdict
from typing import Callable, Dict, List, Optional

from .capability_events import CapabilityEvent, CapabilityEventType

SubscriberFn = Callable[[CapabilityEvent], None]

_WILDCARD = "__ALL__"


class CapabilityEventBus:
    """
    Thread-safe publish/subscribe event bus for capability events.

    Subscriber exceptions are swallowed (isolation guarantee).
    """

    MAX_HISTORY = 2000

    def __init__(self) -> None:
        self._lock:        threading.Lock                            = threading.Lock()
        self._subscribers: Dict[str, List[SubscriberFn]]            = defaultdict(list)
        self._history:     List[CapabilityEvent]                     = []

    # ── subscription ─────────────────────────────────────────────────────────

    def subscribe(
        self,
        event_type: CapabilityEventType,
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
        event_type: CapabilityEventType,
        handler:    SubscriberFn,
    ) -> None:
        with self._lock:
            subs = self._subscribers.get(event_type.value, [])
            try:
                subs.remove(handler)
            except ValueError:
                pass

    # ── publishing ────────────────────────────────────────────────────────────

    def publish(self, event: CapabilityEvent) -> None:
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
        event_type: Optional[CapabilityEventType] = None,
    ) -> List[CapabilityEvent]:
        with self._lock:
            events = list(self._history)
        if event_type is not None:
            events = [e for e in events if e.event_type == event_type]
        return events

    def clear_history(self) -> None:
        with self._lock:
            self._history.clear()
