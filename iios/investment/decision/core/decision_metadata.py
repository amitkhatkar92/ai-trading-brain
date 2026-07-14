"""iios/investment/decision/core/decision_metadata.py
DecisionMetadata — audit trail and versioning for a decision.
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class AuditEntry:
    """A single immutable entry in the audit trail."""
    entry_id:    str
    actor:       str
    action:      str
    note:        str
    occurred_at: datetime
    extra:       Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id":    self.entry_id,
            "actor":       self.actor,
            "action":      self.action,
            "note":        self.note,
            "occurred_at": self.occurred_at.isoformat(),
            "extra":       self.extra,
        }


def _make_audit_entry(
    actor:  str,
    action: str,
    note:   str  = "",
    extra:  Optional[Dict[str, Any]] = None,
) -> AuditEntry:
    return AuditEntry(
        entry_id=str(uuid.uuid4()),
        actor=actor,
        action=action,
        note=note,
        occurred_at=datetime.now(timezone.utc),
        extra=extra or {},
    )


class DecisionMetadata:
    """
    Mutable, thread-safe metadata container for one decision.
    Tracks version history and audit trail.
    """

    def __init__(
        self,
        decision_id:  str,
        created_by:   str,
        version:      int   = 1,
    ) -> None:
        self._lock         = threading.RLock()
        self.decision_id   = decision_id
        self.created_by    = created_by
        self.created_at    = datetime.now(timezone.utc)
        self.updated_at    = self.created_at
        self.version       = version
        self._audit:       List[AuditEntry] = []

        self._record("system", "decision_created", f"Decision {decision_id} initialised.")

    def record(self, actor: str, action: str, note: str = "", extra: Optional[Dict[str, Any]] = None) -> None:
        with self._lock:
            self._audit.append(_make_audit_entry(actor, action, note, extra))
            self.updated_at = datetime.now(timezone.utc)
            self.version   += 1

    def _record(self, actor: str, action: str, note: str = "") -> None:
        """Internal record that does NOT increment version."""
        self._audit.append(_make_audit_entry(actor, action, note))

    @property
    def audit_trail(self) -> List[AuditEntry]:
        with self._lock:
            return list(self._audit)

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "decision_id":  self.decision_id,
                "created_by":   self.created_by,
                "created_at":   self.created_at.isoformat(),
                "updated_at":   self.updated_at.isoformat(),
                "version":      self.version,
                "audit_entries": len(self._audit),
                "audit_trail":  [e.to_dict() for e in self._audit],
            }
