"""iios/execution/monitoring/audit/audit_history.py"""
from __future__ import annotations

import threading
from typing import Any

from iios.execution.monitoring.monitoring_constants import (
    AuditEventType,
    DEFAULT_MAX_AUDIT_EVENTS,
)
from iios.execution.monitoring.monitoring_exceptions import (
    AuditStorageOverflowError,
    AuditTamperingDetectedError,
)
from iios.execution.monitoring.audit.audit_event import AuditEvent


class AuditHistory:
    """
    Append-only, in-memory audit event store.

    Supports:
    - Chronological retrieval
    - Entity-scoped queries
    - Event-type filtering
    - Integrity verification
    Thread-safe.
    """

    def __init__(self, max_events: int = DEFAULT_MAX_AUDIT_EVENTS) -> None:
        self._events:         list[AuditEvent]             = []
        self._by_entity:      dict[str, list[AuditEvent]]  = {}
        self._by_event_type:  dict[AuditEventType, list[AuditEvent]] = {}
        self._index:          dict[str, AuditEvent]        = {}
        self._max_events      = max_events
        self._lock            = threading.RLock()

    # ── Append ────────────────────────────────────────────────────────────────

    def append(self, event: AuditEvent) -> None:
        with self._lock:
            if len(self._events) >= self._max_events:
                raise AuditStorageOverflowError(
                    f"Audit history capacity reached ({self._max_events})",
                    "EM-032",
                )
            self._events.append(event)
            self._index[event.event_id] = event
            if event.entity_id:
                self._by_entity.setdefault(event.entity_id, []).append(event)
            self._by_event_type.setdefault(event.event_type, []).append(event)

    # ── Queries ───────────────────────────────────────────────────────────────

    def get(self, event_id: str) -> AuditEvent | None:
        with self._lock:
            return self._index.get(event_id)

    def for_entity(self, entity_id: str) -> list[AuditEvent]:
        with self._lock:
            return list(self._by_entity.get(entity_id, []))

    def for_event_type(self, event_type: AuditEventType) -> list[AuditEvent]:
        with self._lock:
            return list(self._by_event_type.get(event_type, []))

    def all_events(self) -> list[AuditEvent]:
        with self._lock:
            return list(self._events)

    def recent(self, n: int = 100) -> list[AuditEvent]:
        with self._lock:
            return list(self._events[-n:])

    def count(self) -> int:
        with self._lock:
            return len(self._events)

    # ── Integrity ─────────────────────────────────────────────────────────────

    def verify_all(self) -> list[str]:
        """Return event_ids of any events that fail integrity check."""
        with self._lock:
            events = list(self._events)
        tampered = [e.event_id for e in events if not e.verify_integrity()]
        return tampered

    def assert_integrity(self) -> None:
        """Raise AuditTamperingDetectedError if any record fails integrity."""
        tampered = self.verify_all()
        if tampered:
            raise AuditTamperingDetectedError(
                f"{len(tampered)} tampered audit event(s) detected: {tampered[:3]}",
                "EM-033",
            )

    def statistics(self) -> dict[str, Any]:
        with self._lock:
            return {
                "total_events":  len(self._events),
                "max_events":    self._max_events,
                "entity_count":  len(self._by_entity),
                "event_types":   list(self._by_event_type.keys()),
            }
