"""iios/execution/oms/persistence/storage_snapshot.py
==================================================
StorageSnapshot — point-in-time view of a repository's active records.

C6 Execution Intelligence — Phase 2, Module 5
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.execution.oms.persistence.constants import (
    SCHEMA_VERSION,
    RecordStatus,
    RecordType,
    RepositoryHealth,
)
from iios.execution.oms.persistence.storage_metadata import StorageMetadata


@dataclass(frozen=True)
class StorageSnapshot:
    """
    Immutable snapshot of a repository's record inventory.

    Contains only StorageMetadata (no payloads) to avoid exposing
    sensitive data and to keep snapshot size bounded.
    """
    snapshot_id:     str   = field(default_factory=lambda: str(uuid.uuid4()))
    repository_id:   str   = ""
    schema_version:  str   = SCHEMA_VERSION
    total_records:   int   = 0
    total_active:    int   = 0
    total_archived:  int   = 0
    total_deleted:   int   = 0
    total_corrupted: int   = 0
    records:         tuple[StorageMetadata, ...] = field(default_factory=tuple)
    health:          RepositoryHealth = RepositoryHealth.HEALTHY
    taken_at:        float = field(default_factory=time.time)
    metadata:        dict[str, Any] = field(default_factory=dict)

    def active_records(self) -> list[StorageMetadata]:
        return [r for r in self.records if r.status == RecordStatus.ACTIVE]

    def archived_records(self) -> list[StorageMetadata]:
        return [r for r in self.records if r.status == RecordStatus.ARCHIVED]

    def by_type(self, record_type: RecordType) -> list[StorageMetadata]:
        return [r for r in self.records if r.record_type == record_type]

    @property
    def is_healthy(self) -> bool:
        return self.health == RepositoryHealth.HEALTHY

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id":    self.snapshot_id,
            "repository_id":  self.repository_id,
            "schema_version": self.schema_version,
            "total_records":  self.total_records,
            "total_active":   self.total_active,
            "total_archived": self.total_archived,
            "total_deleted":  self.total_deleted,
            "health":         self.health.value,
            "taken_at":       self.taken_at,
        }
