"""
workflow_snapshot_events.py — iios.workflow.snapshot
-----------------------------------------------------
WorkflowSnapshotEvent + WorkflowSnapshotEventBus —
per-event-type domain event bus for snapshot publication.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 5
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import PREFIX_EVENT, SnapshotEventType

_log = get_logger(__name__)

Listener = Callable[["WorkflowSnapshotEvent"], None]


@dataclass(frozen=True)
class WorkflowSnapshotEvent:
    """Immutable snapshot domain event."""
    event_id:    str
    event_type:  SnapshotEventType
    snapshot_id: str
    workflow_id: str
    payload:     Dict[str, Any]
    emitted_at:  str

    @classmethod
    def create(
        cls,
        event_type:  SnapshotEventType,
        snapshot_id: str         = "",
        workflow_id: str         = "",
        payload:     Optional[Dict[str, Any]] = None,
    ) -> "WorkflowSnapshotEvent":
        return cls(
            event_id    = f"{PREFIX_EVENT}{uuid.uuid4().hex[:10]}",
            event_type  = event_type,
            snapshot_id = snapshot_id,
            workflow_id = workflow_id,
            payload     = dict(payload or {}),
            emitted_at  = datetime.now(tz=timezone.utc).isoformat(),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":    self.event_id,
            "event_type":  self.event_type.value,
            "snapshot_id": self.snapshot_id,
            "workflow_id": self.workflow_id,
            "emitted_at":  self.emitted_at,
        }


class WorkflowSnapshotEventBus:
    """
    Per-event-type snapshot domain event bus.

    Thread-safe.  Listener errors are caught and logged.
    """

    def __init__(self) -> None:
        self._listeners: Dict[SnapshotEventType, List[Listener]] = {}
        self._lock = threading.Lock()

    def add_listener(self, event_type: SnapshotEventType, listener: Listener) -> None:
        with self._lock:
            self._listeners.setdefault(event_type, [])
            if listener not in self._listeners[event_type]:
                self._listeners[event_type].append(listener)

    def remove_listener(self, event_type: SnapshotEventType, listener: Listener) -> bool:
        with self._lock:
            bucket = self._listeners.get(event_type, [])
            if listener in bucket:
                bucket.remove(listener)
                return True
        return False

    def listener_count(self, event_type: Optional[SnapshotEventType] = None) -> int:
        with self._lock:
            if event_type is not None:
                return len(self._listeners.get(event_type, []))
            return sum(len(v) for v in self._listeners.values())

    def emit(self, event: WorkflowSnapshotEvent) -> int:
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
