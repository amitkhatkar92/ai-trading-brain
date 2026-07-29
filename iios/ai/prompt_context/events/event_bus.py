"""
event_bus.py -- iios.ai.prompt_context.events
================================================
:class:`PromptEventBus` -- thread-safe typed event bus for the A3
Prompt & Context Platform.  Mirrors ``iios.ai.foundation.events.event_bus``
but is fully self-contained.

A3 Prompt & Context Platform -- Phase 3, Module 3
"""
from __future__ import annotations

import threading
import uuid
from collections import defaultdict
from typing import Callable, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .event_types   import PromptEventType
from .prompt_events import PromptEvent

_log = get_logger(__name__)

EventHandler = Callable[[PromptEvent], None]


class PromptEventBus:
    """
    Thread-safe typed event bus for the A3 Prompt & Context Platform.

    Handlers are dispatched synchronously on the publisher's thread.
    Handler exceptions are caught and logged.
    """

    def __init__(self) -> None:
        self._lock:            threading.Lock                            = threading.Lock()
        self._handlers:        Dict[str, List[tuple]]                    = defaultdict(list)
        self._sub_map:         Dict[str, str]                            = {}
        self._published_count: int                                      = 0

    def publish(self, event: PromptEvent) -> None:
        """Publish ``event`` to all registered handlers for its type."""
        key = event.event_type.value
        with self._lock:
            handlers = list(self._handlers.get(key, []))
            self._published_count += 1
        for sub_id, handler in handlers:
            try:
                handler(event)
            except Exception as exc:
                _log.warning(
                    f"PromptEventBus: handler error sub_id={sub_id!r} "
                    f"event_type={key!r} error={exc}"
                )

    def subscribe(self, event_type: PromptEventType, handler: EventHandler) -> str:
        """Subscribe ``handler`` to ``event_type``.  Returns subscription id."""
        sub_id = str(uuid.uuid4())
        key    = event_type.value
        with self._lock:
            self._handlers[key].append((sub_id, handler))
            self._sub_map[sub_id] = key
        return sub_id

    def unsubscribe(self, subscription_id: str) -> None:
        with self._lock:
            key = self._sub_map.pop(subscription_id, None)
            if key and key in self._handlers:
                self._handlers[key] = [
                    (sid, h) for sid, h in self._handlers[key] if sid != subscription_id
                ]

    def subscriber_count(self, event_type: Optional[PromptEventType] = None) -> int:
        with self._lock:
            if event_type:
                return len(self._handlers.get(event_type.value, []))
            return sum(len(v) for v in self._handlers.values())

    @property
    def published_count(self) -> int:
        with self._lock:
            return self._published_count

    def clear(self) -> None:
        with self._lock:
            self._handlers.clear()
            self._sub_map.clear()
            self._published_count = 0

    def __repr__(self) -> str:
        return f"<PromptEventBus subscriptions={len(self._sub_map)} published={self.published_count}>"
