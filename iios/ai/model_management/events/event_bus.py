"""
event_bus.py -- iios.ai.model_management.events
=================================================
:class:`ModelEventBus` — thread-safe publish/subscribe bus for A2 domain
events.  Independent of A1's AIEventBus so A2 can be used standalone.

A2 Model Management — Phase 3, Module 2
"""
from __future__ import annotations

import threading
import uuid
from typing import Callable, Dict, List, Optional

from .event_types  import ModelEventType
from .model_events import ModelEvent


class ModelEventBus:
    """Thread-safe, synchronous publish/subscribe event bus for A2 events."""

    def __init__(self) -> None:
        self._subscribers: Dict[ModelEventType, Dict[str, Callable[[ModelEvent], None]]] = {}
        self._lock: threading.RLock = threading.RLock()
        self._published_count: int = 0

    def subscribe(
        self,
        event_type: ModelEventType,
        handler: Callable[[ModelEvent], None],
    ) -> str:
        """Register *handler* for *event_type*; returns a subscription id."""
        sub_id = str(uuid.uuid4())
        with self._lock:
            self._subscribers.setdefault(event_type, {})[sub_id] = handler
        return sub_id

    def unsubscribe(self, sub_id: str) -> None:
        """Remove subscription by id.  Silent no-op if already removed."""
        with self._lock:
            for handlers in self._subscribers.values():
                handlers.pop(sub_id, None)

    def publish(self, event: ModelEvent) -> None:
        """Publish *event* synchronously to all registered handlers."""
        with self._lock:
            handlers = list(self._subscribers.get(event.event_type, {}).values())
            self._published_count += 1
        for handler in handlers:
            handler(event)

    def subscriber_count(self, event_type: ModelEventType) -> int:
        with self._lock:
            return len(self._subscribers.get(event_type, {}))

    def clear(self) -> None:
        with self._lock:
            self._subscribers.clear()

    @property
    def published_count(self) -> int:
        with self._lock:
            return self._published_count
