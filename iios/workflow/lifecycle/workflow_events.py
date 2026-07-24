"""
workflow_events.py — iios.workflow.lifecycle
---------------------------------------------
Event data objects and synchronous event bus for workflow lifecycle events.

11 event types matching WorkflowEventType enum.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 1
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import WorkflowEventType, WorkflowLifecycleState

_log     = get_logger(__name__)
Listener = Callable[["WorkflowLifecycleEvent"], None]


@dataclass(frozen=True)
class WorkflowLifecycleEvent:
    """An immutable event emitted by the Workflow Lifecycle system."""
    event_id:   str
    event_type: WorkflowEventType
    session_id: str
    state:      WorkflowLifecycleState
    payload:    Dict[str, Any]
    emitted_at: str

    @classmethod
    def create(
        cls,
        event_type: WorkflowEventType,
        session_id: str,
        state:      WorkflowLifecycleState,
        payload:    Optional[Dict[str, Any]] = None,
    ) -> "WorkflowLifecycleEvent":
        return cls(
            event_id   = f"wevt-{uuid.uuid4().hex[:10]}",
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


class WorkflowLifecycleEventBus:
    """
    Thread-safe synchronous event bus for workflow lifecycle events.

    Listener exceptions are logged and suppressed.
    """

    def __init__(self) -> None:
        self._listeners: List[Listener] = []
        self._lock = threading.Lock()

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
        event_type: WorkflowEventType,
        session_id: str,
        state:      WorkflowLifecycleState,
        payload:    Optional[Dict[str, Any]] = None,
    ) -> WorkflowLifecycleEvent:
        event = WorkflowLifecycleEvent.create(event_type, session_id, state, payload)
        with self._lock:
            listeners = list(self._listeners)
        for fn in listeners:
            try:
                fn(event)
            except Exception as exc:
                _log.warning(
                    f"Workflow lifecycle listener error on {event_type.value!r}: {exc!r}"
                )
        return event

    def listener_count(self) -> int:
        with self._lock:
            return len(self._listeners)

    def clear(self) -> None:
        with self._lock:
            self._listeners.clear()
