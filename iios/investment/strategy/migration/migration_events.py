"""iios/investment/strategy/migration/migration_events.py
Event bus for the Strategy Migration Framework.
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class MigrationEventType(str, Enum):
    DISCOVERY_STARTED          = "discovery_started"
    STRATEGY_DISCOVERED        = "strategy_discovered"
    DISCOVERY_COMPLETED        = "discovery_completed"

    VALIDATION_STARTED         = "validation_started"
    VALIDATION_PASSED          = "validation_passed"
    VALIDATION_FAILED          = "validation_failed"

    PREPARATION_STARTED        = "preparation_started"
    ADAPTER_CREATED            = "adapter_created"

    MIGRATION_STARTED          = "migration_started"
    MIGRATION_COMPLETED        = "migration_completed"
    MIGRATION_FAILED           = "migration_failed"

    VERIFICATION_STARTED       = "verification_started"
    BEHAVIOR_EQUIVALENCE_PASSED  = "behavior_equivalence_passed"
    BEHAVIOR_EQUIVALENCE_FAILED  = "behavior_equivalence_failed"
    VERIFICATION_COMPLETED     = "verification_completed"

    APPROVAL_REQUESTED         = "approval_requested"
    MIGRATION_APPROVED         = "migration_approved"
    MIGRATION_REJECTED         = "migration_rejected"

    ROLLBACK_REQUESTED         = "rollback_requested"
    ROLLBACK_COMPLETED         = "rollback_completed"
    ROLLBACK_FAILED            = "rollback_failed"

    ARCHIVED                   = "archived"
    CHECKPOINT_SAVED           = "checkpoint_saved"


@dataclass
class MigrationEvent:
    """Immutable event record emitted during migration lifecycle."""
    event_id:      str
    event_type:    MigrationEventType
    strategy_id:   str
    strategy_name: str
    payload:       Dict[str, Any]
    occurred_at:   datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    session_id:    str = ""
    source:        str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":     self.event_id,
            "event_type":   self.event_type.value,
            "strategy_id":  self.strategy_id,
            "strategy_name": self.strategy_name,
            "payload":      self.payload,
            "occurred_at":  self.occurred_at.isoformat(),
            "session_id":   self.session_id,
        }


MigrationEventHandler = Callable[[MigrationEvent], None]


class MigrationEventBus:
    """Thread-safe in-process event bus for migration lifecycle events."""

    def __init__(self) -> None:
        self._handlers: Dict[MigrationEventType, List[MigrationEventHandler]] = {}
        self._global:   List[MigrationEventHandler] = []
        self._history:  List[MigrationEvent] = []
        self._lock      = threading.RLock()
        self._max_history = 10_000

    def subscribe(
        self,
        handler:    MigrationEventHandler,
        event_type: Optional[MigrationEventType] = None,
    ) -> None:
        with self._lock:
            if event_type is None:
                if handler not in self._global:
                    self._global.append(handler)
            else:
                self._handlers.setdefault(event_type, [])
                if handler not in self._handlers[event_type]:
                    self._handlers[event_type].append(handler)

    def unsubscribe(
        self,
        handler:    MigrationEventHandler,
        event_type: Optional[MigrationEventType] = None,
    ) -> None:
        with self._lock:
            if event_type is None:
                self._global = [h for h in self._global if h != handler]
            elif event_type in self._handlers:
                self._handlers[event_type] = [
                    h for h in self._handlers[event_type] if h != handler
                ]

    def emit(self, event: MigrationEvent) -> None:
        with self._lock:
            handlers = list(self._global) + list(
                self._handlers.get(event.event_type, [])
            )
            if len(self._history) < self._max_history:
                self._history.append(event)
        for h in handlers:
            try:
                h(event)
            except Exception:
                pass

    def emit_simple(
        self,
        event_type:    MigrationEventType,
        strategy_id:   str,
        strategy_name: str,
        payload:       Optional[Dict[str, Any]] = None,
        session_id:    str = "",
    ) -> None:
        self.emit(MigrationEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            strategy_id=strategy_id,
            strategy_name=strategy_name,
            payload=payload or {},
            session_id=session_id,
        ))

    def history(
        self,
        strategy_id: Optional[str] = None,
        event_type:  Optional[MigrationEventType] = None,
        n:           int = 100,
    ) -> List[MigrationEvent]:
        with self._lock:
            events = list(self._history)
        if strategy_id:
            events = [e for e in events if e.strategy_id == strategy_id]
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        return events[-n:]
