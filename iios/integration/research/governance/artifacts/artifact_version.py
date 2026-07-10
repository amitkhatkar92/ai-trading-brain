"""artifacts/artifact_version.py — Version history for an artifact."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ArtifactVersion:
    """
    A single version entry in an artifact's version history.
    """
    version_id:   str
    artifact_id:  str
    version:      str
    checksum:     Optional[str]
    storage_path: Optional[str]
    size_bytes:    int
    change_notes: str
    created_at:   float
    created_by:   Optional[str]

    @classmethod
    def create(
        cls,
        artifact_id:  str,
        version:      str,
        *,
        version_id:   Optional[str] = None,
        checksum:     Optional[str] = None,
        storage_path: Optional[str] = None,
        size_bytes:    int          = 0,
        change_notes: str           = "",
        created_by:   Optional[str] = None,
    ) -> "ArtifactVersion":
        return cls(
            version_id   = version_id or f"av_{uuid.uuid4().hex[:10]}",
            artifact_id  = artifact_id,
            version      = version,
            checksum     = checksum,
            storage_path = storage_path,
            size_bytes    = size_bytes,
            change_notes = change_notes,
            created_at   = time.time(),
            created_by   = created_by,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "version_id":   self.version_id,
            "artifact_id":  self.artifact_id,
            "version":      self.version,
            "checksum":     self.checksum,
            "storage_path": self.storage_path,
            "size_bytes":    self.size_bytes,
            "change_notes": self.change_notes,
            "created_at":   self.created_at,
            "created_by":   self.created_by,
        }
