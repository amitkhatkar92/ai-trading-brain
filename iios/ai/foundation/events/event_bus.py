"""
event_bus.py -- iios.ai.foundation.events
==========================================
Typed AI event bus for the provider runtime.

Builds on LocalAIEventBus from adapters/ but adds typed handler support
and synchronous dispatch with structured logging.

A1 AI Foundation -- Phase 3, Provider Runtime
"""
from __future__ import annotations

import threading
import uuid
from collections import defaultdict
from typing import Callable, Dict, List, Optional, Type, TypeVar

from iios.common.logging.logging_manager import get_logger

from .ai_events import AIEvent
from .event_types import AIEventType

_log = get_logger(__name__)

E = TypeVar("E", bound=AIEvent)
EventHandler = Callable[[AIEvent], None]


class AIEventBus:
    """
    Thread-safe typed event bus for the AI Foundation runtime.

    Handlers are dispatched synchronously on the publisher's thread.
    Handler exceptions are caught and logged -- a faulty handler never
    breaks delivery to other subscribers.

    Usage::

        bus = AIEventBus()
        sub = bus.subscribe(AIEventType.EXECUTION_COMPLETED, my_handler)
        bus.publish(ExecutionCompletedEvent.create(...))
        bus.unsubscribe(sub)
    """

    def __init__(self) -> None:
        self._lock:     threading.Lock                          = threading.Lock()
        self._handlers: Dict[str, List[tuple[str, EventHandler]]] = defaultdict(list)
        self._sub_map:  Dict[str, str]                         = {}   # sub_id -> event_type

    def publish(self, event: AIEvent) -> None:
        """Publish ``event`` to all registered handlers for its type."""
        key = event.event_type.value
        with self._lock:
            handlers = list(self._handlers.get(key, []))
        for sub_id, handler in handlers:
            try:
                handler(event)
            except Exception as exc:
                _log.warning(
                    f"AIEventBus: handler error sub_id={sub_id!r} "
                    f"event_type={key!r} error={exc}"
                )

    def subscribe(self, event_type: AIEventType, handler: EventHandler) -> str:
        """
        Subscribe ``handler`` to ``event_type``.

        Returns the subscription ID (pass to :meth:`unsubscribe` to remove).
        """
        sub_id = str(uuid.uuid4())
        key    = event_type.value
        with self._lock:
            self._handlers[key].append((sub_id, handler))
            self._sub_map[sub_id] = key
        return sub_id

    def unsubscribe(self, subscription_id: str) -> None:
        """Remove the subscription identified by ``subscription_id``."""
        with self._lock:
            key = self._sub_map.pop(subscription_id, None)
            if key and key in self._handlers:
                self._handlers[key] = [
                    (sid, h) for sid, h in self._handlers[key]
                    if sid != subscription_id
                ]

    def subscriber_count(self, event_type: Optional[AIEventType] = None) -> int:
        """Return count of subscribers for ``event_type``, or total if None."""
        with self._lock:
            if event_type:
                return len(self._handlers.get(event_type.value, []))
            return sum(len(v) for v in self._handlers.values())

    def clear(self) -> None:
        """Remove all subscriptions."""
        with self._lock:
            self._handlers.clear()
            self._sub_map.clear()

    def __repr__(self) -> str:
        return f"<AIEventBus subscriptions={len(self._sub_map)}>"
