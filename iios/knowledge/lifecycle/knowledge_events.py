"""
knowledge_events.py — iios.knowledge.lifecycle
------------------------------------------------
Domain events emitted by the Knowledge Lifecycle subsystem.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 1
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from .constants import KnowledgeEventType, KnowledgeLifecycleState


@dataclass(frozen=True)
class KnowledgeEvent:
    """
    Immutable domain event emitted during a knowledge lifecycle transition.

    Fields
    ------
    event_id :      Unique event identifier.
    event_type :    Semantic event type.
    session_id :    Owning knowledge session.
    artifact_id :   Knowledge artifact identifier.
    state :         Knowledge session state at emission time.
    actor :         Identity that triggered the transition.
    occurred_at :   Wall-clock time the event occurred.
    reason :        Optional human-readable context.
    metadata :      Supplementary key-value metadata.
    """
    event_id:    str
    event_type:  KnowledgeEventType
    session_id:  str
    artifact_id: str
    state:       KnowledgeLifecycleState
    actor:       str
    occurred_at: float          = field(default_factory=time.time)
    reason:      str            = ""
    metadata:    Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        event_type:  KnowledgeEventType,
        session_id:  str,
        artifact_id: str,
        state:       KnowledgeLifecycleState,
        actor:       str,
        *,
        event_id:    Optional[str]            = None,
        reason:      str                      = "",
        metadata:    Optional[Dict[str, Any]] = None,
    ) -> "KnowledgeEvent":
        return cls(
            event_id    = event_id or str(uuid.uuid4()),
            event_type  = event_type,
            session_id  = session_id,
            artifact_id = artifact_id,
            state       = state,
            actor       = actor,
            occurred_at = time.time(),
            reason      = reason,
            metadata    = metadata or {},
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":    self.event_id,
            "event_type":  self.event_type.value,
            "session_id":  self.session_id,
            "artifact_id": self.artifact_id,
            "state":       self.state.value,
            "actor":       self.actor,
            "occurred_at": self.occurred_at,
            "reason":      self.reason,
        }


# ---------------------------------------------------------------------------
# Event dispatcher
# ---------------------------------------------------------------------------

KnowledgeEventListener = Callable[[KnowledgeEvent], None]


class KnowledgeEventBus:
    """
    Simple synchronous event bus for knowledge lifecycle events.

    Listeners are called in registration order.  Exceptions from
    individual listeners are caught and logged but do not interrupt
    other listeners.
    """

    def __init__(self) -> None:
        self._listeners: List[KnowledgeEventListener] = []

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def add_listener(self, listener: KnowledgeEventListener) -> None:
        """Register a listener.  Idempotent — duplicate registrations are ignored."""
        if listener not in self._listeners:
            self._listeners.append(listener)

    def remove_listener(self, listener: KnowledgeEventListener) -> bool:
        """Remove a previously registered listener.  Returns ``True`` if removed."""
        try:
            self._listeners.remove(listener)
            return True
        except ValueError:
            return False

    def listener_count(self) -> int:
        return len(self._listeners)

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    def emit(self, event: KnowledgeEvent) -> None:
        """Emit an event to all registered listeners."""
        for listener in list(self._listeners):
            try:
                listener(event)
            except Exception:  # noqa: BLE001 — isolate listener failures
                pass

    def clear(self) -> None:
        """Remove all listeners (used in tests / teardown)."""
        self._listeners.clear()
