"""iios/investment/strategy/migration/migration_audit.py
Append-only, thread-safe migration audit log.
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterator, List, Optional


@dataclass(frozen=True)
class AuditEntry:
    """
    A single immutable audit record for one migration event.
    """
    audit_id:      str
    strategy_id:   str
    strategy_name: str
    event_type:    str
    actor:         str      # "system" or user identifier
    before_state:  Dict[str, Any]
    after_state:   Dict[str, Any]
    reason:        str
    timestamp:     datetime
    session_id:    str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "audit_id":      self.audit_id,
            "strategy_id":   self.strategy_id,
            "strategy_name": self.strategy_name,
            "event_type":    self.event_type,
            "actor":         self.actor,
            "before_state":  self.before_state,
            "after_state":   self.after_state,
            "reason":        self.reason,
            "timestamp":     self.timestamp.isoformat(),
            "session_id":    self.session_id,
        }


def make_entry(
    strategy_id:   str,
    strategy_name: str,
    event_type:    str,
    before_state:  Dict[str, Any],
    after_state:   Dict[str, Any],
    reason:        str = "",
    actor:         str = "system",
    session_id:    str = "",
) -> AuditEntry:
    """Convenience constructor that fills in audit_id and timestamp."""
    return AuditEntry(
        audit_id=str(uuid.uuid4()),
        strategy_id=strategy_id,
        strategy_name=strategy_name,
        event_type=event_type,
        actor=actor,
        before_state=before_state,
        after_state=after_state,
        reason=reason,
        timestamp=datetime.now(timezone.utc),
        session_id=session_id,
    )


class MigrationAudit:
    """
    Append-only migration audit store.
    All entries are immutable once written.
    Supports per-strategy retrieval, full export, and chronological iteration.
    """

    def __init__(self) -> None:
        self._lock:    threading.RLock      = threading.RLock()
        self._entries: List[AuditEntry]     = []
        self._by_id:   Dict[str, List[AuditEntry]] = {}  # strategy_id → entries

    def record(self, entry: AuditEntry) -> None:
        with self._lock:
            self._entries.append(entry)
            bucket = self._by_id.setdefault(entry.strategy_id, [])
            bucket.append(entry)

    def record_event(
        self,
        strategy_id:   str,
        strategy_name: str,
        event_type:    str,
        before_state:  Optional[Dict] = None,
        after_state:   Optional[Dict] = None,
        reason:        str            = "",
        actor:         str            = "system",
        session_id:    str            = "",
    ) -> AuditEntry:
        entry = make_entry(
            strategy_id=strategy_id,
            strategy_name=strategy_name,
            event_type=event_type,
            before_state=before_state or {},
            after_state=after_state or {},
            reason=reason,
            actor=actor,
            session_id=session_id,
        )
        self.record(entry)
        return entry

    def get(self, strategy_id: str) -> List[AuditEntry]:
        """All audit entries for one strategy in chronological order."""
        with self._lock:
            return list(self._by_id.get(strategy_id, []))

    def all(self) -> List[AuditEntry]:
        """All entries in insertion order."""
        with self._lock:
            return list(self._entries)

    def export(self) -> List[Dict[str, Any]]:
        """Serialize all entries for external audit systems."""
        with self._lock:
            return [e.to_dict() for e in self._entries]

    def count(self) -> int:
        with self._lock:
            return len(self._entries)

    def strategies_audited(self) -> List[str]:
        with self._lock:
            return list(self._by_id.keys())

    def __iter__(self) -> Iterator[AuditEntry]:
        with self._lock:
            return iter(list(self._entries))
