"""artifacts/artifact_metadata.py — Artifact descriptor and lifecycle."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from iios.integration.research.governance.governance_constants import ArtifactStatus, ArtifactType
from iios.integration.research.governance.governance_exceptions import ArtifactLockedError


@dataclass
class ArtifactMetadata:
    """
    Describes a single research artifact: model, dataset, report, etc.

    Supports version tracking, locking, and archival transitions.
    """
    artifact_id:   str
    name:          str
    artifact_type: ArtifactType
    version:       str
    status:        ArtifactStatus
    entity_id:     Optional[str]   # owning project / experiment
    storage_path:  Optional[str]
    checksum:      Optional[str]
    size_bytes:    int
    mime_type:     str
    tags:          list[str]
    created_at:    float
    updated_at:    float
    created_by:    Optional[str]
    metadata:      dict[str, Any]

    @classmethod
    def create(
        cls,
        name:          str,
        artifact_type: ArtifactType,
        *,
        artifact_id:   Optional[str]        = None,
        version:       str                  = "1.0.0",
        entity_id:     Optional[str]        = None,
        storage_path:  Optional[str]        = None,
        checksum:      Optional[str]        = None,
        size_bytes:    int                  = 0,
        mime_type:     str                  = "application/octet-stream",
        tags:          Optional[list[str]]  = None,
        created_by:    Optional[str]        = None,
        metadata:      Optional[dict]       = None,
    ) -> "ArtifactMetadata":
        now = time.time()
        return cls(
            artifact_id   = artifact_id or f"art_{uuid.uuid4().hex[:10]}",
            name          = name,
            artifact_type = artifact_type,
            version       = version,
            status        = ArtifactStatus.DRAFT,
            entity_id     = entity_id,
            storage_path  = storage_path,
            checksum      = checksum,
            size_bytes     = size_bytes,
            mime_type     = mime_type,
            tags          = tags or [],
            created_at    = now,
            updated_at    = now,
            created_by    = created_by,
            metadata      = metadata or {},
        )

    def touch(self) -> None:
        self.updated_at = time.time()

    def lock(self) -> None:
        if self.status == ArtifactStatus.ARCHIVED:
            raise ArtifactLockedError(f"Artifact '{self.artifact_id}' is archived and cannot be locked")
        self.status     = ArtifactStatus.LOCKED
        self.updated_at = time.time()

    def archive(self) -> None:
        self.status     = ArtifactStatus.ARCHIVED
        self.updated_at = time.time()

    def promote(self) -> None:
        if self.status == ArtifactStatus.LOCKED:
            raise ArtifactLockedError(f"Artifact '{self.artifact_id}' is locked")
        self.status     = ArtifactStatus.PUBLISHED
        self.updated_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_id":   self.artifact_id,
            "name":          self.name,
            "artifact_type": self.artifact_type.value,
            "version":       self.version,
            "status":        self.status.value,
            "entity_id":     self.entity_id,
            "storage_path":  self.storage_path,
            "checksum":      self.checksum,
            "size_bytes":     self.size_bytes,
            "mime_type":     self.mime_type,
            "tags":          self.tags,
            "created_at":    self.created_at,
            "updated_at":    self.updated_at,
            "created_by":    self.created_by,
        }
