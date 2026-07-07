"""
iios/knowledge/models/knowledge_snapshot.py
============================================
Immutable point-in-time snapshot of a KnowledgeRecord.
Used by the versioning subsystem to provide rollback capability.
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from ..knowledge_constants import VersionStatus, VersionBump, SYSTEM_OWNER

__all__ = ["KnowledgeSnapshot", "VersionDiff"]


def _new_id() -> str:
    return str(uuid.uuid4())


@dataclass
class VersionDiff:
    """Records what changed between two versions."""
    snapshot_id_before: str
    snapshot_id_after:  str
    fields_changed:     list[str] = field(default_factory=list)
    summary:            str       = ""
    created_at:         float     = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id_before": self.snapshot_id_before,
            "snapshot_id_after":  self.snapshot_id_after,
            "fields_changed":     self.fields_changed,
            "summary":            self.summary,
            "created_at":         self.created_at,
        }


@dataclass
class KnowledgeSnapshot:
    """Immutable snapshot of a KnowledgeRecord at a point in time.

    Stored by the versioning subsystem.  The ``payload`` is the
    full serialised form of the record at capture time.
    """

    snapshot_id:    str          = field(default_factory=_new_id)
    knowledge_id:   str          = ""
    version:        str          = "1.0.0"
    version_seq:    int          = 1
    bump_type:      VersionBump  = VersionBump.MINOR
    status:         VersionStatus = VersionStatus.CURRENT
    created_by:     str          = SYSTEM_OWNER
    created_at:     float        = field(default_factory=time.time)
    change_summary: str          = ""

    # Full serialised record payload (JSON-serialisable dict)
    payload:        dict[str, Any] = field(default_factory=dict)

    # Pointer to previous snapshot (forms a linked list)
    parent_snapshot_id: Optional[str] = None

    def mark_historical(self) -> None:
        self.status = VersionStatus.HISTORICAL

    def mark_rollback(self) -> None:
        self.status = VersionStatus.ROLLBACK

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id":        self.snapshot_id,
            "knowledge_id":       self.knowledge_id,
            "version":            self.version,
            "version_seq":        self.version_seq,
            "bump_type":          self.bump_type.value,
            "status":             self.status.value,
            "created_by":         self.created_by,
            "created_at":         self.created_at,
            "change_summary":     self.change_summary,
            "payload":            self.payload,
            "parent_snapshot_id": self.parent_snapshot_id,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "KnowledgeSnapshot":
        return cls(
            snapshot_id        = d.get("snapshot_id", _new_id()),
            knowledge_id       = d["knowledge_id"],
            version            = d.get("version", "1.0.0"),
            version_seq        = d.get("version_seq", 1),
            bump_type          = VersionBump(d.get("bump_type", VersionBump.MINOR)),
            status             = VersionStatus(d.get("status", VersionStatus.CURRENT)),
            created_by         = d.get("created_by", SYSTEM_OWNER),
            created_at         = d.get("created_at", time.time()),
            change_summary     = d.get("change_summary", ""),
            payload            = dict(d.get("payload", {})),
            parent_snapshot_id = d.get("parent_snapshot_id"),
        )
