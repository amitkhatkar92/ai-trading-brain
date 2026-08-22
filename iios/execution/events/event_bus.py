"""iios/execution/events/event_bus.py"""
from __future__ import annotations

import logging
import threading
from collections import defaultdict
from typing import Callable

from iios.execution.execution_constants import ExecutionEventType
from iios.execution.events.execution_event import ExecutionEvent

logger = logging.getLogger(__name__)


class ExecutionEventBus:
    """
    Thread-safe, in-process publish/subscribe bus for execution events.

    Handlers are called synchronously in the publisher's thread.
    Handlers that raise are logged and silenced so a bad handler cannot
    crash the workflow.
    """

    def __init__(self) -> None:
        self._lock: threading.RLock = threading.RLock()
        # event_type → list[handler]
        self._handlers: dict[ExecutionEventType, list[Callable[[ExecutionEvent], None]]] = (
            defaultdict(list)
        )
        # Per-execution event store (last N per execution_id)
        self._events:   dict[str, list[ExecutionEvent]] = defaultdict(list)
        self._max_events_per_execution = 500

    # ── Subscription ──────────────────────────────────────────────────────────

    def subscribe(
        self,
        event_type: ExecutionEventType,
        handler: Callable[[ExecutionEvent], None],
    ) -> None:
        with self._lock:
            if handler not in self._handlers[event_type]:
                self._handlers[event_type].append(handler)

    def unsubscribe(
        self,
        event_type: ExecutionEventType,
        handler: Callable[[ExecutionEvent], None],
    ) -> None:
        with self._lock:
            handlers = self._handlers[event_type]
            if handler in handlers:
                handlers.remove(handler)

    def subscribe_all(self, handler: Callable[[ExecutionEvent], None]) -> None:
        """Subscribe to every event type."""
        with self._lock:
            for et in ExecutionEventType:
                self.subscribe(et, handler)

    # ── Publishing ────────────────────────────────────────────────────────────

    def publish(self, event: ExecutionEvent) -> None:
        with self._lock:
            # Store in per-execution ring buffer.
            buf = self._events[event.execution_id]
            if len(buf) >= self._max_events_per_execution:
                buf.pop(0)
            buf.append(event)
            handlers = list(self._handlers.get(event.event_type, []))

        # Dispatch outside lock to avoid deadlock in re-entrant handlers.
        for handler in handlers:
            try:
                handler(event)
            except Exception:
                logger.exception(
                    "ExecutionEventBus: handler %s raised for event %s",
                    handler,
                    event.event_type.value,
                )

    # ── Query ─────────────────────────────────────────────────────────────────

    def get_events(self, execution_id: str) -> list[ExecutionEvent]:
        with self._lock:
            return list(self._events.get(execution_id, []))

    def clear_events(self, execution_id: str) -> None:
        with self._lock:
            self._events.pop(execution_id, None)

    def clear_all(self) -> None:
        with self._lock:
            self._events.clear()

    def handler_count(self, event_type: ExecutionEventType) -> int:
        with self._lock:
            return len(self._handlers.get(event_type, []))
