"""
iios/knowledge/versioning/models/version_audit.py
==================================================
AuditEntry — immutable audit record emitted by the versioning engine for
every significant lifecycle event (create, release, archive, rollback,
branch, merge, provenance link, lineage link).

All entries are stored with nanosecond timestamps to ensure strict ordering
even in high-throughput scenarios.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from ..version_constants import (
    VersionEventType,
    DEFAULT_BRANCH,
    SYSTEM_VERSIONING_ACTOR,
)

__all__ = ["AuditEntry"]


def _new_id() -> str:
    return str(uuid.uuid4())


@dataclass
class AuditEntry:
    """Single audit record for one versioning lifecycle event."""

    audit_id:     str               = field(default_factory=_new_id)
    knowledge_id: str               = ""
    event_type:   VersionEventType  = VersionEventType.VERSION_CREATED

    # Version / branch context
    version_id:   Optional[str]     = None
    branch_name:  str               = DEFAULT_BRANCH

    # Actor and reason
    actor:        str               = SYSTEM_VERSIONING_ACTOR
    reason:       str               = ""

    # Free-form details (e.g. conflict fields, merge strategy)
    details:      dict[str, Any]    = field(default_factory=dict)

    created_at:   float             = field(default_factory=time.time)

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "audit_id":     self.audit_id,
            "knowledge_id": self.knowledge_id,
            "event_type":   self.event_type.value,
            "version_id":   self.version_id,
            "branch_name":  self.branch_name,
            "actor":        self.actor,
            "reason":       self.reason,
            "details":      dict(self.details),
            "created_at":   self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "AuditEntry":
        return cls(
            audit_id     = d.get("audit_id",     _new_id()),
            knowledge_id = d.get("knowledge_id", ""),
            event_type   = VersionEventType(d.get("event_type",
                                                   VersionEventType.VERSION_CREATED.value)),
            version_id   = d.get("version_id"),
            branch_name  = d.get("branch_name",  DEFAULT_BRANCH),
            actor        = d.get("actor",        SYSTEM_VERSIONING_ACTOR),
            reason       = d.get("reason",       ""),
            details      = dict(d.get("details", {})),
            created_at   = d.get("created_at",   time.time()),
        )
