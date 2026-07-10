"""models/model_artifact.py — Binary/path artefact reference for a trained model."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class ModelArtifact:
    """
    Stores the location and checksum of a serialised model artefact.

    The framework itself does NOT read or write the artefact bytes — that is
    delegated entirely to the concrete model via ``BaseModel.save()`` /
    ``BaseModel.load()``.  This record simply tracks *where* the artefact lives.
    """
    artifact_id:  str
    model_id:     str
    model_version: str
    storage_path: str         # filesystem path, S3 URI, etc.
    size_bytes:   int
    checksum:     Optional[str]
    format:       str         # "pkl", "pt", "onnx", "custom", ...
    created_at:   float
    metadata:     dict[str, Any]

    @classmethod
    def create(
        cls,
        model_id:      str,
        model_version: str,
        storage_path:  str,
        *,
        artifact_id:   Optional[str] = None,
        size_bytes:    int           = 0,
        checksum:      Optional[str] = None,
        format:        str           = "custom",
        metadata:      Optional[dict] = None,
    ) -> "ModelArtifact":
        return cls(
            artifact_id   = artifact_id or f"art_{uuid.uuid4().hex[:12]}",
            model_id      = model_id,
            model_version = model_version,
            storage_path  = storage_path,
            size_bytes    = size_bytes,
            checksum      = checksum,
            format        = format,
            created_at    = time.time(),
            metadata      = metadata or {},
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_id":   self.artifact_id,
            "model_id":      self.model_id,
            "model_version": self.model_version,
            "storage_path":  self.storage_path,
            "size_bytes":    self.size_bytes,
            "checksum":      self.checksum,
            "format":        self.format,
            "created_at":    self.created_at,
        }
