"""
integration_snapshot_events.py — iios.integration.snapshot
------------------------------------------------------------
IntegrationSnapshotEventBus — thread-safe in-process pub/sub bus for
snapshot lifecycle events.

Handlers that raise exceptions are suppressed (logged but not re-raised).
Event history is bounded to prevent unbounded memory growth.

C15 Enterprise Integration & Connectivity — Phase 1, Module 5
"""
from __future__ import annotations

import uuid
import threading
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Deque, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import EVENT_ID_PREFIX, SnapshotEventType

_log = get_logger(__name__)

Handler = Callable[["SnapshotEvent"], None]


@dataclass(frozen=True)
class SnapshotEvent:
    """Immutable snapshot lifecycle event."""
    event_id:    str
    event_type:  SnapshotEventType
    snapshot_id: str
    source:      str
    payload:     Dict[str, Any]
    occurred_at: str


class IntegrationSnapshotEventBus:
    """
    Thread-safe in-process pub/sub bus for snapshot lifecycle events.

    Handlers are invoked synchronously in the calling thread.
    Exceptions raised by handlers are caught and logged (not re-raised).
    History is bounded by max_history.
    """

    def __init__(self, max_history: int = 500) -> None:
        self._handlers:    Dict[SnapshotEventType, List[Handler]] = {}
        self._history:     Deque[SnapshotEvent]                   = deque(maxlen=max_history)
        self._published:   int                                     = 0
        self._failed_handlers: int                                 = 0
        self._lock:        threading.Lock                          = threading.Lock()

    # ── Subscription ──────────────────────────────────────────────────

    def subscribe(
        self,
        event_type: SnapshotEventType,
        handler:    Handler,
    ) -> bool:
        """
        Subscribe a handler to an event type.

        Returns True.  Duplicate registrations are allowed (handler will
        be called multiple times per event).
        """
        with self._lock:
            self._handlers.setdefault(event_type, []).append(handler)
        return True

    def unsubscribe(
        self,
        event_type: SnapshotEventType,
        handler:    Handler,
    ) -> bool:
        """
        Remove a specific handler for an event type.

        Returns True if found and removed, False otherwise.
        """
        with self._lock:
            handlers = self._handlers.get(event_type, [])
            try:
                handlers.remove(handler)
                return True
            except ValueError:
                return False

    # ── Publication ───────────────────────────────────────────────────

    def publish(self, event: SnapshotEvent) -> int:
        """
        Publish an event to all registered handlers.

        Returns the number of handlers successfully invoked.
        Handler exceptions are suppressed and logged.
        """
        with self._lock:
            handlers = list(self._handlers.get(event.event_type, []))
            self._history.append(event)
            self._published += 1

        invoked = 0
        for handler in handlers:
            try:
                handler(event)
                invoked += 1
            except Exception as exc:
                with self._lock:
                    self._failed_handlers += 1
                _log.warning(
                    f"Snapshot event handler raised: "
                    f"{type(exc).__name__}: {exc} "
                    f"(event={event.event_type.value!r})"
                )
        return invoked

    def emit(
        self,
        event_type:  SnapshotEventType,
        snapshot_id: str,
        source:      str,
        payload:     Optional[Dict[str, Any]] = None,
    ) -> int:
        """Convenience method: build and publish a SnapshotEvent."""
        event = SnapshotEvent(
            event_id    = f"{EVENT_ID_PREFIX}{uuid.uuid4().hex[:12]}",
            event_type  = event_type,
            snapshot_id = snapshot_id,
            source      = source,
            payload     = dict(payload or {}),
            occurred_at = datetime.now(tz=timezone.utc).isoformat(),
        )
        return self.publish(event)

    # ── History ───────────────────────────────────────────────────────

    def history(self, n: Optional[int] = None) -> List[SnapshotEvent]:
        """Return recent events (all if n is None, else last n)."""
        with self._lock:
            events = list(self._history)
        return events if n is None else events[-n:]

    def history_by_type(
        self, event_type: SnapshotEventType
    ) -> List[SnapshotEvent]:
        """Return all history entries for a specific event type."""
        with self._lock:
            return [e for e in self._history if e.event_type == event_type]

    # ── Stats ─────────────────────────────────────────────────────────

    @property
    def stats(self) -> Dict[str, int]:
        with self._lock:
            return {
                "published":        self._published,
                "failed_handlers":  self._failed_handlers,
                "history_size":     len(self._history),
            }
