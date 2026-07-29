"""
governance_event_bus.py -- iios.ai.governance.events
=====================================================
Thread-safe pub/sub event bus for A8 AI Governance Platform.

A8 AI Governance Platform — Phase 3, Module 8
"""
from __future__ import annotations

import threading
from typing import Callable, Dict, List

from .governance_events import GovernanceEvent, GovernanceEventType


class GovernanceEventBus:
    """
    Thread-safe synchronous governance event bus.

    Subscriber exceptions are swallowed to prevent misbehaving handlers
    from blocking governance operations.
    """

    def __init__(self) -> None:
        self._lock:     threading.Lock = threading.Lock()
        self._handlers: Dict[GovernanceEventType, List[Callable]] = {}
        self._history:  List[GovernanceEvent] = []
        self._max_history: int = 2000

    def subscribe(self, event_type: GovernanceEventType, handler: Callable) -> None:
        with self._lock:
            self._handlers.setdefault(event_type, []).append(handler)

    def unsubscribe(self, event_type: GovernanceEventType, handler: Callable) -> None:
        with self._lock:
            handlers = self._handlers.get(event_type, [])
            if handler in handlers:
                handlers.remove(handler)

    def subscribe_all(self, handler: Callable) -> None:
        for et in GovernanceEventType:
            self.subscribe(et, handler)

    def publish(self, event: GovernanceEvent) -> None:
        with self._lock:
            handlers = list(self._handlers.get(event.event_type, []))
            if len(self._history) >= self._max_history:
                self._history = self._history[-(self._max_history - 1):]
            self._history.append(event)
        for handler in handlers:
            try:
                handler(event)
            except Exception:
                pass

    def history(
        self,
        event_type: GovernanceEventType | None = None,
        limit: int = 200,
    ) -> List[GovernanceEvent]:
        with self._lock:
            events = list(self._history)
        if event_type is not None:
            events = [e for e in events if e.event_type == event_type]
        return events[-limit:]

    def subscriber_count(self, event_type: GovernanceEventType) -> int:
        with self._lock:
            return len(self._handlers.get(event_type, []))

    def clear_history(self) -> None:
        with self._lock:
            self._history.clear()
