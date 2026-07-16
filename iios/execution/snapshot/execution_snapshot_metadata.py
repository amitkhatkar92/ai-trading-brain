"""iios/execution/snapshot/execution_snapshot_metadata.py
==================================================
SnapshotAuditMetadata — immutable audit and provenance record
attached to every ExecutionSnapshot.

C6 Execution Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.execution.snapshot.constants import (
    SnapshotFormat,
    SnapshotTrigger,
    VERSION,
)

SNAPSHOT_SYSTEM_ID_DEFAULT = "iios:execution:snapshot"


@dataclass(frozen=True)
class SnapshotAuditMetadata:
    """
    Immutable audit and provenance record for a single snapshot.

    Tracks who created the snapshot, when, what triggered it,
    and versioning / format information.
    """

    audit_id:       str            = field(default_factory=lambda: str(uuid.uuid4()))
    schema_version: str            = VERSION

    # Provenance
    created_by:     str            = "iios:system"
    created_at:     float          = field(default_factory=time.time)
    source_system:  str            = SNAPSHOT_SYSTEM_ID_DEFAULT
    trigger:        SnapshotTrigger = SnapshotTrigger.STATE_TRANSITION
    format:         SnapshotFormat  = SnapshotFormat.JSON

    # Lineage
    parent_snapshot_id: str = ""    # ID of prior snapshot in sequence
    sequence_number:    int = 0     # monotonically increasing per execution

    # Tags
    tags:     frozenset[str]    = field(default_factory=frozenset)
    notes:    str               = ""
    metadata: dict[str, Any]   = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "audit_id":           self.audit_id,
            "schema_version":     self.schema_version,
            "created_by":         self.created_by,
            "created_at":         self.created_at,
            "source_system":      self.source_system,
            "trigger":            self.trigger.value,
            "format":             self.format.value,
            "parent_snapshot_id": self.parent_snapshot_id,
            "sequence_number":    self.sequence_number,
            "tags":               sorted(self.tags),
            "notes":              self.notes,
        }

    def __repr__(self) -> str:
        return (
            f"SnapshotAuditMetadata("
            f"trigger={self.trigger.value}, "
            f"seq={self.sequence_number})"
        )


SNAPSHOT_SYSTEM_ID_DEFAULT = "iios:execution:snapshot"
