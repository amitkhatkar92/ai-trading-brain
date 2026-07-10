"""lineage/artifact_lineage.py — Artifact-specific lineage tracking."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from iios.integration.research.governance.governance_constants import ArtifactType


@dataclass
class ArtifactLineageRecord:
    """
    Tracks the lineage of a single artifact:
    what created it, what it depends on, and what it feeds into.
    """
    record_id:       str
    artifact_id:     str
    artifact_type:   ArtifactType
    artifact_name:   str
    artifact_version: str
    source_ids:      list[str]    # upstream entity IDs
    derived_from:    Optional[str]  # direct parent artifact_id (for versioned chains)
    produced_by:     Optional[str]  # experiment_id or job_id that created this artifact
    checksum:        Optional[str]
    storage_path:    Optional[str]
    created_at:      float
    metadata:        dict[str, Any]

    @classmethod
    def create(
        cls,
        artifact_id:      str,
        artifact_type:    ArtifactType,
        artifact_name:    str,
        artifact_version: str = "1.0.0",
        *,
        record_id:    Optional[str]  = None,
        source_ids:   Optional[list] = None,
        derived_from: Optional[str]  = None,
        produced_by:  Optional[str]  = None,
        checksum:     Optional[str]  = None,
        storage_path: Optional[str]  = None,
        metadata:     Optional[dict] = None,
    ) -> "ArtifactLineageRecord":
        return cls(
            record_id        = record_id or f"alr_{uuid.uuid4().hex[:10]}",
            artifact_id      = artifact_id,
            artifact_type    = artifact_type,
            artifact_name    = artifact_name,
            artifact_version = artifact_version,
            source_ids       = source_ids or [],
            derived_from     = derived_from,
            produced_by      = produced_by,
            checksum         = checksum,
            storage_path     = storage_path,
            created_at       = time.time(),
            metadata         = metadata or {},
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id":        self.record_id,
            "artifact_id":      self.artifact_id,
            "artifact_type":    self.artifact_type.value,
            "artifact_name":    self.artifact_name,
            "artifact_version": self.artifact_version,
            "source_ids":       self.source_ids,
            "derived_from":     self.derived_from,
            "produced_by":      self.produced_by,
            "checksum":         self.checksum,
            "storage_path":     self.storage_path,
            "created_at":       self.created_at,
        }
