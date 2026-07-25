"""
workflow_events.py — iios.workflow.engine
------------------------------------------
9 workflow engine events and synchronous event bus.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 2
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import WorkflowEngineEventType

_log     = get_logger(__name__)
Listener = Callable[["WorkflowEngineEvent"], None]


@dataclass(frozen=True)
class WorkflowEngineEvent:
    """Immutable event emitted by the Workflow Engine."""
    event_id:   str
    event_type: WorkflowEngineEventType
    engine_id:  str
    request_id: str
    session_id: str
    payload:    Dict[str, Any]
    emitted_at: str

    @classmethod
    def create(
        cls,
        event_type: WorkflowEngineEventType,
        engine_id:  str,
        request_id: str,
        session_id: str,
        payload:    Optional[Dict[str, Any]] = None,
    ) -> "WorkflowEngineEvent":
        return cls(
            event_id   = f"wevt-{uuid.uuid4().hex[:10]}",
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


class WorkflowEngineEventBus:
    """
    Thread-safe synchronous event bus for workflow engine events.

    Supports per-event-type listener registration.  Listener exceptions
    are logged and suppressed so a bad listener cannot crash the engine.
    """

    def __init__(self) -> None:
        self._listeners: Dict[WorkflowEngineEventType, List[Listener]] = {}
        self._lock = threading.Lock()

    def add_listener(
        self,
        event_type: WorkflowEngineEventType,
        listener:   Listener,
    ) -> None:
        with self._lock:
            bucket = self._listeners.setdefault(event_type, [])
            if listener not in bucket:
                bucket.append(listener)

    def remove_listener(
        self,
        event_type: WorkflowEngineEventType,
        listener:   Listener,
    ) -> None:
        with self._lock:
            if event_type in self._listeners:
                self._listeners[event_type] = [
                    l for l in self._listeners[event_type] if l is not listener
                ]

    def emit(
        self,
        event_type: WorkflowEngineEventType,
        engine_id:  str,
        request_id: str,
        session_id: str,
        payload:    Optional[Dict[str, Any]] = None,
    ) -> WorkflowEngineEvent:
        event = WorkflowEngineEvent.create(
            event_type, engine_id, request_id, session_id, payload
        )
        with self._lock:
            listeners = list(self._listeners.get(event_type, []))
        for lst in listeners:
            try:
                lst(event)
            except Exception as exc:
                _log.warning(
                    f"EventBus listener error type={event_type.value!r}: {exc!r}"
                )
        return event

    def listener_count(self, event_type: WorkflowEngineEventType) -> int:
        with self._lock:
            return len(self._listeners.get(event_type, []))

    def clear(self) -> None:
        with self._lock:
            self._listeners.clear()
