"""audit/audit_history.py — Immutable append-only audit log."""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from iios.integration.research.governance.governance_constants import (
    AuditEventType,
    DEFAULT_MAX_AUDIT_ENTRIES,
)
from iios.integration.research.governance.governance_exceptions import AuditError


@dataclass(frozen=True)
class AuditRecord:
    """
    An immutable audit log entry.

    frozen=True ensures no field can be mutated after creation,
    preserving the integrity of the audit trail.
    """
    record_id:    str
    event_type:   AuditEventType
    entity_type:  str
    entity_id:    str
    actor:        Optional[str]
    before_state: Optional[dict]
    after_state:  Optional[dict]
    ip_address:   Optional[str]
    occurred_at:  float
    metadata:     dict

    @classmethod
    def create(
        cls,
        event_type:   AuditEventType,
        entity_type:  str,
        entity_id:    str,
        *,
        record_id:    Optional[str]  = None,
        actor:        Optional[str]  = None,
        before_state: Optional[dict] = None,
        after_state:  Optional[dict] = None,
        ip_address:   Optional[str]  = None,
        metadata:     Optional[dict] = None,
    ) -> "AuditRecord":
        return cls(
            record_id    = record_id or f"audit_{uuid.uuid4().hex[:10]}",
            event_type   = event_type,
            entity_type  = entity_type,
            entity_id    = entity_id,
            actor        = actor,
            before_state = before_state,
            after_state  = after_state,
            ip_address   = ip_address,
            occurred_at  = time.time(),
            metadata     = metadata or {},
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id":    self.record_id,
            "event_type":   self.event_type.value,
            "entity_type":  self.entity_type,
            "entity_id":    self.entity_id,
            "actor":        self.actor,
            "before_state": self.before_state,
            "after_state":  self.after_state,
            "ip_address":   self.ip_address,
            "occurred_at":  self.occurred_at,
        }


class AuditHistory:
    """
    Append-only audit log.

    Enforces capacity limits and provides filtering queries.
    Records are immutable (frozen dataclass) and stored in insertion order.
    """

    def __init__(self, max_entries: int = DEFAULT_MAX_AUDIT_ENTRIES) -> None:
        self._records: list[AuditRecord] = []
        self._max     = max_entries
        self._lock    = threading.RLock()

    def append(self, record: AuditRecord) -> None:
        with self._lock:
            if len(self._records) >= self._max:
                # Evict oldest 10 % to avoid blocking
                evict = max(1, self._max // 10)
                self._records = self._records[evict:]
            self._records.append(record)

    def query(
        self,
        *,
        entity_id:   Optional[str]        = None,
        event_type:  Optional[AuditEventType] = None,
        actor:       Optional[str]        = None,
        limit:       int                  = 100,
    ) -> list[AuditRecord]:
        with self._lock:
            result = list(self._records)
        if entity_id is not None:
            result = [r for r in result if r.entity_id == entity_id]
        if event_type is not None:
            result = [r for r in result if r.event_type == event_type]
        if actor is not None:
            result = [r for r in result if r.actor == actor]
        return result[-limit:]

    def count(self) -> int:
        with self._lock:
            return len(self._records)

    def export(self) -> list[dict[str, Any]]:
        with self._lock:
            return [r.to_dict() for r in self._records]
