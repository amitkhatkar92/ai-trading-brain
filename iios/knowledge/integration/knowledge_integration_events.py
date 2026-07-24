"""
knowledge_integration_events.py — iios.knowledge.integration
-------------------------------------------------------------
Event data objects and synchronous event bus for the integration system.

8 event types matching IntegrationEventType enum.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List

from iios.common.logging.logging_manager import get_logger

from .constants import IntegrationEventType

_log     = get_logger(__name__)
Listener = Callable[["IntegrationEvent"], None]


@dataclass(frozen=True)
class IntegrationEvent:
    """An immutable event emitted by the Knowledge Integration system."""
    event_id:       str
    event_type:     IntegrationEventType
    integration_id: str
    session_id:     str
    payload:        Dict[str, Any]
    emitted_at:     str

    @classmethod
    def create(
        cls,
        event_type:     IntegrationEventType,
        integration_id: str = "",
        session_id:     str = "",
        payload:        Optional[Dict[str, Any]] = None,
    ) -> "IntegrationEvent":
        return cls(
            event_id       = f"ievt-{uuid.uuid4().hex[:10]}",
            event_type     = event_type,
            integration_id = integration_id,
            session_id     = session_id,
            payload        = dict(payload or {}),
            emitted_at     = datetime.now(tz=timezone.utc).isoformat(),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":       self.event_id,
            "event_type":     self.event_type.value,
            "integration_id": self.integration_id,
            "session_id":     self.session_id,
            "payload":        self.payload,
            "emitted_at":     self.emitted_at,
        }


# Fix missing Optional import
from typing import Optional   # noqa: E402


class IntegrationEventBus:
    """
    Thread-safe synchronous event bus for integration events.

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
        event_type:     IntegrationEventType,
        integration_id: str = "",
        session_id:     str = "",
        payload:        Optional[Dict[str, Any]] = None,
    ) -> IntegrationEvent:
        event = IntegrationEvent.create(
            event_type, integration_id, session_id, payload
        )
        with self._lock:
            listeners = list(self._listeners)
        for fn in listeners:
            try:
                fn(event)
            except Exception as exc:
                _log.warning(
                    f"Integration listener error on {event_type.value!r}: {exc!r}"
                )
        return event

    def listener_count(self) -> int:
        with self._lock:
            return len(self._listeners)

    def clear(self) -> None:
        with self._lock:
            self._listeners.clear()
