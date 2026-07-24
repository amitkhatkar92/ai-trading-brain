"""
integration_events.py — iios.integration.engine
-------------------------------------------------
9 integration engine events and synchronous event bus.

C15 Enterprise Integration & Connectivity — Phase 1, Module 2
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import IntegrationEngineEventType

_log     = get_logger(__name__)
Listener = Callable[["IntegrationEngineEvent"], None]


@dataclass(frozen=True)
class IntegrationEngineEvent:
    """Immutable event emitted by the Integration Engine."""
    event_id:   str
    event_type: IntegrationEngineEventType
    engine_id:  str
    request_id: str
    session_id: str
    payload:    Dict[str, Any]
    emitted_at: str

    @classmethod
    def create(
        cls,
        event_type: IntegrationEngineEventType,
        engine_id:  str,
        request_id: str,
        session_id: str,
        payload:    Optional[Dict[str, Any]] = None,
    ) -> "IntegrationEngineEvent":
        return cls(
            event_id   = f"evnt-{uuid.uuid4().hex[:10]}",
            event_type = event_type,
            engine_id  = engine_id,
            request_id = request_id,
            session_id = session_id,
            payload    = dict(payload or {}),
            emitted_at = datetime.now(tz=timezone.utc).isoformat(),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":   self.event_id,
            "event_type": self.event_type.value,
            "engine_id":  self.engine_id,
            "request_id": self.request_id,
            "session_id": self.session_id,
            "payload":    self.payload,
            "emitted_at": self.emitted_at,
        }


class IntegrationEngineEventBus:
    """
    Thread-safe synchronous event bus.

    Listener exceptions are logged and suppressed so a bad listener
    cannot crash the engine.
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
        event_type: IntegrationEngineEventType,
        engine_id:  str,
        request_id: str,
        session_id: str,
        payload:    Optional[Dict[str, Any]] = None,
    ) -> IntegrationEngineEvent:
        event = IntegrationEngineEvent.create(
            event_type, engine_id, request_id, session_id, payload
        )
        with self._lock:
            listeners = list(self._listeners)
        for fn in listeners:
            try:
                fn(event)
            except Exception as exc:
                _log.warning(
                    f"Engine event listener error on {event_type.value!r}: {exc!r}"
                )
        return event

    def listener_count(self) -> int:
        with self._lock:
            return len(self._listeners)

    def clear(self) -> None:
        with self._lock:
            self._listeners.clear()
