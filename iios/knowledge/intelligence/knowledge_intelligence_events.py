"""
knowledge_intelligence_events.py — iios.knowledge.intelligence
---------------------------------------------------------------
Event data objects and a lightweight synchronous event bus for the
Knowledge Intelligence Framework.

10 event types (IntelligenceEventType).

C14 Enterprise Knowledge Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List

from iios.common.logging.logging_manager import get_logger

from .constants import IntelligenceEventType

_log = get_logger(__name__)

Listener = Callable[["IntelligenceEvent"], None]


@dataclass(frozen=True)
class IntelligenceEvent:
    """An event emitted by the Knowledge Intelligence Framework."""
    event_id:   str
    event_type: IntelligenceEventType
    payload:    Dict[str, Any]
    emitted_at: str

    @classmethod
    def create(
        cls,
        event_type: IntelligenceEventType,
        payload:    Dict[str, Any] = None,
    ) -> "IntelligenceEvent":
        return cls(
            event_id   = f"evt-{uuid.uuid4().hex[:10]}",
            event_type = event_type,
            payload    = dict(payload or {}),
            emitted_at = datetime.now(tz=timezone.utc).isoformat(),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":   self.event_id,
            "event_type": self.event_type.value,
            "payload":    self.payload,
            "emitted_at": self.emitted_at,
        }


class IntelligenceEventBus:
    """
    Thread-safe synchronous event bus for intelligence events.

    Each call to emit() invokes all registered listeners on the calling
    thread in registration order.  Listener exceptions are logged and
    suppressed to protect the intelligence pipeline.
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
        event_type: IntelligenceEventType,
        payload:    Dict[str, Any] = None,
    ) -> IntelligenceEvent:
        event = IntelligenceEvent.create(event_type, payload)
        with self._lock:
            listeners = list(self._listeners)
        for fn in listeners:
            try:
                fn(event)
            except Exception as exc:
                _log.warning(
                    f"Listener error on {event_type.value!r}: {exc!r}"
                )
        return event

    def listener_count(self) -> int:
        with self._lock:
            return len(self._listeners)

    def clear(self) -> None:
        with self._lock:
            self._listeners.clear()
