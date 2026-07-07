"""
iios/knowledge/versioning/models/version_branch.py
===================================================
VersionBranch, ConflictInfo, and MergeResult — data models for the
branching and merging subsystem of the versioning engine.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from ..version_constants import (
    BranchStatus,
    MergeStrategy,
    DEFAULT_BRANCH,
    SYSTEM_VERSIONING_ACTOR,
    VERSIONING_SCHEMA_VERSION,
)

__all__ = ["VersionBranch", "ConflictInfo", "MergeResult"]


def _new_id() -> str:
    return str(uuid.uuid4())


@dataclass
class VersionBranch:
    """Metadata record for a knowledge branch.

    Branches track the divergence point from the parent branch
    (``source_version_id``) and the ordered sequence of version IDs
    committed onto the branch.
    """

    branch_id:         str          = field(default_factory=_new_id)
    knowledge_id:      str          = ""
    name:              str          = DEFAULT_BRANCH
    source_branch:     str          = DEFAULT_BRANCH
    source_version_id: Optional[str] = None   # version at which this branch forked

    status:            BranchStatus  = BranchStatus.OPEN
    created_by:        str           = SYSTEM_VERSIONING_ACTOR
    description:       str           = ""

    # Ordered list of version_ids committed on this branch (oldest first)
    version_ids:       list[str]     = field(default_factory=list)

    # Set when merged
    merged_into:       Optional[str] = None
    merged_at:         Optional[float] = None
    merged_by:         Optional[str]   = None

    created_at:        float         = field(default_factory=time.time)
    schema_version:    str           = VERSIONING_SCHEMA_VERSION

    # ── Helpers ───────────────────────────────────────────────────────────────

    @property
    def is_main(self) -> bool:
        return self.name == DEFAULT_BRANCH

    @property
    def head_version_id(self) -> Optional[str]:
        """Latest version on this branch."""
        return self.version_ids[-1] if self.version_ids else None

    @property
    def commit_count(self) -> int:
        return len(self.version_ids)

    def add_version(self, version_id: str) -> None:
        self.version_ids.append(version_id)

    def mark_merged(self, into: str, by: str) -> None:
        self.status = BranchStatus.MERGED
        self.merged_into = into
        self.merged_at = time.time()
        self.merged_by = by

    def mark_closed(self) -> None:
        self.status = BranchStatus.CLOSED

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "branch_id":          self.branch_id,
            "knowledge_id":       self.knowledge_id,
            "name":               self.name,
            "source_branch":      self.source_branch,
            "source_version_id":  self.source_version_id,
            "status":             self.status.value,
            "created_by":         self.created_by,
            "description":        self.description,
            "version_ids":        list(self.version_ids),
            "merged_into":        self.merged_into,
            "merged_at":          self.merged_at,
            "merged_by":          self.merged_by,
            "created_at":         self.created_at,
            "schema_version":     self.schema_version,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "VersionBranch":
        return cls(
            branch_id         = d.get("branch_id",         _new_id()),
            knowledge_id      = d.get("knowledge_id",      ""),
            name              = d.get("name",              DEFAULT_BRANCH),
            source_branch     = d.get("source_branch",     DEFAULT_BRANCH),
            source_version_id = d.get("source_version_id"),
            status            = BranchStatus(d.get("status", BranchStatus.OPEN.value)),
            created_by        = d.get("created_by",        SYSTEM_VERSIONING_ACTOR),
            description       = d.get("description",       ""),
            version_ids       = list(d.get("version_ids",  [])),
            merged_into       = d.get("merged_into"),
            merged_at         = d.get("merged_at"),
            merged_by         = d.get("merged_by"),
            created_at        = d.get("created_at",        time.time()),
            schema_version    = d.get("schema_version",    VERSIONING_SCHEMA_VERSION),
        )


@dataclass
class ConflictInfo:
    """Describes a single field-level conflict detected during a merge."""

    field_name:    str
    source_value:  Any
    target_value:  Any
    base_value:    Any = None  # common ancestor value; None if unknown

    def to_dict(self) -> dict[str, Any]:
        return {
            "field_name":   self.field_name,
            "source_value": self.source_value,
            "target_value": self.target_value,
            "base_value":   self.base_value,
        }


@dataclass
class MergeResult:
    """Result of a branch merge operation."""

    success:          bool
    knowledge_id:     str
    source_branch:    str
    target_branch:    str
    strategy:         MergeStrategy
    new_version_id:   Optional[str]       = None  # created on target if successful
    conflicts:        list[ConflictInfo]  = field(default_factory=list)
    merged_by:        str                 = SYSTEM_VERSIONING_ACTOR
    error_message:    str                 = ""
    created_at:       float               = field(default_factory=time.time)

    @property
    def has_conflicts(self) -> bool:
        return bool(self.conflicts)

    @property
    def conflict_fields(self) -> list[str]:
        return [c.field_name for c in self.conflicts]

    def to_dict(self) -> dict[str, Any]:
        return {
            "success":        self.success,
            "knowledge_id":   self.knowledge_id,
            "source_branch":  self.source_branch,
            "target_branch":  self.target_branch,
            "strategy":       self.strategy.value,
            "new_version_id": self.new_version_id,
            "conflicts":      [c.to_dict() for c in self.conflicts],
            "merged_by":      self.merged_by,
            "error_message":  self.error_message,
            "created_at":     self.created_at,
        }
