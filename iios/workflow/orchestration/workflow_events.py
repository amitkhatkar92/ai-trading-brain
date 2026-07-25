"""
workflow_events.py — iios.workflow.orchestration
-------------------------------------------------
OrchestrationEvent + WorkflowOrchestrationEventBus — per-event-type
event bus for orchestration domain events.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 4
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import OrchestrationEventType, PREFIX_EVENT

_log = get_logger(__name__)

Listener = Callable[["OrchestrationEvent"], None]


@dataclass(frozen=True)
class OrchestrationEvent:
    """Immutable orchestration domain event."""
    event_id:    str
    event_type:  OrchestrationEventType
    engine_id:   str
    workflow_id: str
    runtime_id:  str
    payload:     Dict[str, Any]
    emitted_at:  str

    @classmethod
    def create(
        cls,
        event_type:  OrchestrationEventType,
        engine_id:   str,
        workflow_id: str                      = "",
        runtime_id:  str                      = "",
        payload:     Optional[Dict[str, Any]] = None,
    ) -> "OrchestrationEvent":
        return cls(
            event_id    = f"{PREFIX_EVENT}{uuid.uuid4().hex[:10]}",
            event_type  = event_type,
            engine_id   = engine_id,
            workflow_id = workflow_id,
            runtime_id  = runtime_id,
            payload     = dict(payload or {}),
            emitted_at  = datetime.now(tz=timezone.utc).isoformat(),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":   self.event_id,
            "event_type": self.event_type.value,
            "engine_id":  self.engine_id,
            "workflow_id": self.workflow_id,
            "runtime_id":  self.runtime_id,
            "emitted_at":  self.emitted_at,
        }


class WorkflowOrchestrationEventBus:
    """
    Per-event-type orchestration event bus.

    Thread-safe.  Listener errors are caught and logged — they do not
    propagate to the caller.
    """

    def __init__(self) -> None:
        self._listeners: Dict[OrchestrationEventType, List[Listener]] = {}
        self._lock = threading.Lock()

    def add_listener(self, event_type: OrchestrationEventType, listener: Listener) -> None:
        with self._lock:
            self._listeners.setdefault(event_type, [])
            if listener not in self._listeners[event_type]:
                self._listeners[event_type].append(listener)

    def remove_listener(self, event_type: OrchestrationEventType, listener: Listener) -> bool:
        with self._lock:
            bucket = self._listeners.get(event_type, [])
            if listener in bucket:
                bucket.remove(listener)
                return True
        return False

    def listener_count(self, event_type: Optional[OrchestrationEventType] = None) -> int:
        with self._lock:
            if event_type is not None:
                return len(self._listeners.get(event_type, []))
            return sum(len(v) for v in self._listeners.values())

    def emit(self, event: OrchestrationEvent) -> int:
        with self._lock:
            listeners = list(self._listeners.get(event.event_type, []))
        notified = 0
        for listener in listeners:
            try:
                listener(event)
                notified += 1
            except Exception as exc:
                _log.warning(
                    f"EventBus: listener error on {event.event_type.value!r}: {exc!r}"
                )
        return notified

    def clear(self) -> None:
        with self._lock:
            self._listeners.clear()
