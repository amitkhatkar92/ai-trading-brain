"""
workflow_policy_events.py — iios.workflow.policies
---------------------------------------------------
WorkflowPolicyEvent + WorkflowPolicyEventBus — per-event-type
governance event bus.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 3
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import PolicyEventType

_log = get_logger(__name__)

# Type alias for a listener callable
Listener = Callable[["WorkflowPolicyEvent"], None]


@dataclass(frozen=True)
class WorkflowPolicyEvent:
    """Immutable governance domain event."""
    event_id:   str
    event_type: PolicyEventType
    engine_id:  str
    request_id: str
    workflow_id: str
    payload:    Dict[str, Any]
    emitted_at: str

    @classmethod
    def create(
        cls,
        event_type:  PolicyEventType,
        engine_id:   str,
        *,
        request_id:  str                     = "",
        workflow_id: str                     = "",
        payload:     Optional[Dict[str, Any]] = None,
    ) -> "WorkflowPolicyEvent":
        return cls(
            event_id    = f"wpevt-{uuid.uuid4().hex[:10]}",
            event_type  = event_type,
            engine_id   = engine_id,
            request_id  = request_id,
            workflow_id = workflow_id,
            payload     = dict(payload or {}),
            emitted_at  = datetime.now(tz=timezone.utc).isoformat(),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":   self.event_id,
            "event_type": self.event_type.value,
            "engine_id":  self.engine_id,
            "request_id": self.request_id,
            "workflow_id": self.workflow_id,
            "emitted_at": self.emitted_at,
        }


class WorkflowPolicyEventBus:
    """
    Per-event-type governance event bus.

    Listeners are registered per PolicyEventType.  Emitting an event
    calls all listeners registered for that event type.  Errors in
    individual listeners are caught and logged — they do not propagate.

    Thread-safe.
    """

    def __init__(self) -> None:
        # Dict[PolicyEventType, List[Listener]]
        self._listeners: Dict[PolicyEventType, List[Listener]] = {}
        self._lock = threading.Lock()

    # ----------------------------------------------------------------
    # Listener management
    # ----------------------------------------------------------------

    def add_listener(
        self,
        event_type: PolicyEventType,
        listener:   Listener,
    ) -> None:
        with self._lock:
            self._listeners.setdefault(event_type, [])
            if listener not in self._listeners[event_type]:
                self._listeners[event_type].append(listener)

    def remove_listener(
        self,
        event_type: PolicyEventType,
        listener:   Listener,
    ) -> bool:
        """Remove a listener.  Returns True if removed."""
        with self._lock:
            bucket = self._listeners.get(event_type, [])
            if listener in bucket:
                bucket.remove(listener)
                return True
        return False

    def listener_count(self, event_type: Optional[PolicyEventType] = None) -> int:
        """Return total listener count (all types) or for a specific type."""
        with self._lock:
            if event_type is not None:
                return len(self._listeners.get(event_type, []))
            return sum(len(v) for v in self._listeners.values())

    def clear(self) -> None:
        with self._lock:
            self._listeners.clear()

    # ----------------------------------------------------------------
    # Emission
    # ----------------------------------------------------------------

    def emit(self, event: WorkflowPolicyEvent) -> int:
        """
        Emit an event to all registered listeners for its type.

        Returns the number of listeners notified.
        """
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
