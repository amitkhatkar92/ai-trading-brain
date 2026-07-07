"""
iios/knowledge/versioning/models/knowledge_version.py
======================================================
KnowledgeVersion — rich version record that extends the base
KnowledgeSnapshot with branching, author, reason, lifecycle, and
delta-payload support.

Each KnowledgeVersion captures the full serialised state of a knowledge
record at the moment it was versioned (``payload``), the bump type
(MAJOR / MINOR / PATCH / SNAPSHOT), the branch it belongs to, and
optional structured metadata.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from ...knowledge_constants import VersionBump, SYSTEM_OWNER
from ..version_constants import DEFAULT_BRANCH, VERSIONING_SCHEMA_VERSION

__all__ = ["KnowledgeVersion", "VersionStatus"]


def _new_id() -> str:
    return str(uuid.uuid4())


class VersionStatus(str, Enum):
    """Lifecycle status of a KnowledgeVersion."""

    DRAFT    = "draft"     # in progress; not yet released
    CURRENT  = "current"   # the live, active version
    RELEASED = "released"  # published / frozen
    ARCHIVED = "archived"  # superseded but retained for history
    ROLLBACK = "rollback"  # result of a rollback operation
    DELETED  = "deleted"   # soft-deleted (payload retained)


@dataclass
class KnowledgeVersion:
    """Immutable (by convention) version record for a knowledge item.

    Instances should not be mutated after creation.  Use
    ``dataclasses.replace()`` to derive modified copies.
    """

    # Identifiers
    version_id:        str            = field(default_factory=_new_id)
    knowledge_id:      str            = ""

    # Semantic version ("major.minor.patch")
    version_string:    str            = "1.0.0"
    version_seq:       int            = 1

    # Classification
    bump_type:         VersionBump    = VersionBump.SNAPSHOT
    status:            VersionStatus  = VersionStatus.CURRENT
    branch_name:       str            = DEFAULT_BRANCH

    # Authorship
    author:            str            = SYSTEM_OWNER
    change_summary:    str            = ""
    change_reason:     str            = ""

    # Full serialised payload at this version
    payload:           dict[str, Any] = field(default_factory=dict)

    # Linkage
    parent_version_id: Optional[str]  = None
    merged_from_ids:   list[str]      = field(default_factory=list)

    # Extras
    tags:              list[str]      = field(default_factory=list)
    attributes:        dict[str, Any] = field(default_factory=dict)

    # Timestamps
    created_at:        float          = field(default_factory=time.time)

    # Schema
    schema_version:    str            = VERSIONING_SCHEMA_VERSION

    # ── Derived helpers ───────────────────────────────────────────────────────

    @property
    def is_draft(self) -> bool:
        return self.status == VersionStatus.DRAFT

    @property
    def is_released(self) -> bool:
        return self.status == VersionStatus.RELEASED

    @property
    def is_archived(self) -> bool:
        return self.status == VersionStatus.ARCHIVED

    @property
    def is_current(self) -> bool:
        return self.status == VersionStatus.CURRENT

    @property
    def major(self) -> int:
        return int(self.version_string.split(".")[0])

    @property
    def minor(self) -> int:
        return int(self.version_string.split(".")[1])

    @property
    def patch(self) -> int:
        return int(self.version_string.split(".")[2])

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "version_id":        self.version_id,
            "knowledge_id":      self.knowledge_id,
            "version_string":    self.version_string,
            "version_seq":       self.version_seq,
            "bump_type":         self.bump_type.value,
            "status":            self.status.value,
            "branch_name":       self.branch_name,
            "author":            self.author,
            "change_summary":    self.change_summary,
            "change_reason":     self.change_reason,
            "payload":           self.payload,
            "parent_version_id": self.parent_version_id,
            "merged_from_ids":   list(self.merged_from_ids),
            "tags":              list(self.tags),
            "attributes":        dict(self.attributes),
            "created_at":        self.created_at,
            "schema_version":    self.schema_version,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "KnowledgeVersion":
        return cls(
            version_id        = d.get("version_id",        _new_id()),
            knowledge_id      = d.get("knowledge_id",      ""),
            version_string    = d.get("version_string",    "1.0.0"),
            version_seq       = d.get("version_seq",       1),
            bump_type         = VersionBump(d.get("bump_type", VersionBump.SNAPSHOT.value)),
            status            = VersionStatus(d.get("status", VersionStatus.CURRENT.value)),
            branch_name       = d.get("branch_name",       DEFAULT_BRANCH),
            author            = d.get("author",            SYSTEM_OWNER),
            change_summary    = d.get("change_summary",    ""),
            change_reason     = d.get("change_reason",     ""),
            payload           = d.get("payload",           {}),
            parent_version_id = d.get("parent_version_id"),
            merged_from_ids   = list(d.get("merged_from_ids", [])),
            tags              = list(d.get("tags",             [])),
            attributes        = dict(d.get("attributes",       {})),
            created_at        = d.get("created_at",        time.time()),
            schema_version    = d.get("schema_version",    VERSIONING_SCHEMA_VERSION),
        )
