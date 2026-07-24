"""
integration_events.py — iios.integration.lifecycle
----------------------------------------------------
Event data objects and synchronous event bus for lifecycle events.

11 event types matching IntegrationEventType enum.

C15 Enterprise Integration & Connectivity — Phase 1, Module 1
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import IntegrationEventType, IntegrationLifecycleState

_log     = get_logger(__name__)
Listener = Callable[["IntegrationLifecycleEvent"], None]


@dataclass(frozen=True)
class IntegrationLifecycleEvent:
    """An immutable event emitted by the Integration Lifecycle system."""
    event_id:   str
    event_type: IntegrationEventType
    session_id: str
    state:      IntegrationLifecycleState
    payload:    Dict[str, Any]
    emitted_at: str

    @classmethod
    def create(
        cls,
        event_type: IntegrationEventType,
        session_id: str,
        state:      IntegrationLifecycleState,
        payload:    Optional[Dict[str, Any]] = None,
    ) -> "IntegrationLifecycleEvent":
        return cls(
            event_id   = f"levt-{uuid.uuid4().hex[:10]}",
            event_type = event_type,
            session_id = session_id,
            state      = state,
            payload    = dict(payload or {}),
            emitted_at = datetime.now(tz=timezone.utc).isoformat(),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":   self.event_id,
            "event_type": self.event_type.value,
            "session_id": self.session_id,
            "state":      self.state.value,
            "payload":    self.payload,
            "emitted_at": self.emitted_at,
        }


class IntegrationLifecycleEventBus:
    """
    Thread-safe synchronous event bus for lifecycle events.

    Listener exceptions are logged and suppressed.
    """

    def __init__(self) -> None:
        self._listeners: List[Listener] = []
        self._lock       = threading.Lock()

    def add_listener(self, listener: Listener) -> None:
        with self._lock:
            if listener not in self._listeners:
                self._listeners.append(listener)

    def remove_listener(self, listener: Listener) -> None:
        with self._lock:
            if listener in self._listeners:
                self._listeners.remove(listener)

    def emit(
        self,
        event_type: IntegrationEventType,
        session_id: str,
        state:      IntegrationLifecycleState,
        payload:    Optional[Dict[str, Any]] = None,
    ) -> IntegrationLifecycleEvent:
        event = IntegrationLifecycleEvent.create(
            event_type, session_id, state, payload
        )
        with self._lock:
            listeners = list(self._listeners)
        for fn in listeners:
            try:
                fn(event)
            except Exception as exc:
                _log.warning(
                    f"Lifecycle listener error on {event_type.value!r}: {exc!r}"
                )
        return event

    def listener_count(self) -> int:
        with self._lock:
            return len(self._listeners)

    def clear(self) -> None:
        with self._lock:
            self._listeners.clear()
