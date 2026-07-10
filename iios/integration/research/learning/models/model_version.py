"""models/model_version.py — Version record for a model."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ModelVersion:
    """
    Tracks a specific version of a registered model.

    A new ModelVersion is created after each successful training run so that
    version history is preserved for rollback and A/B comparison.
    """
    version_id:     str
    model_id:       str
    version:        str
    parent_version: Optional[str]
    job_id:         Optional[str]
    artifact_id:    Optional[str]
    metrics:        dict[str, float]
    is_champion:    bool
    created_at:     float
    promoted_at:    Optional[float]
    notes:          str

    @classmethod
    def create(
        cls,
        model_id:       str,
        version:        str,
        *,
        version_id:     Optional[str] = None,
        parent_version: Optional[str] = None,
        job_id:         Optional[str] = None,
        artifact_id:    Optional[str] = None,
        metrics:        Optional[dict] = None,
        notes:          str           = "",
    ) -> "ModelVersion":
        return cls(
            version_id     = version_id or f"mv_{uuid.uuid4().hex[:10]}",
            model_id       = model_id,
            version        = version,
            parent_version = parent_version,
            job_id         = job_id,
            artifact_id    = artifact_id,
            metrics        = metrics or {},
            is_champion    = False,
            created_at     = time.time(),
            promoted_at    = None,
            notes          = notes,
        )

    def promote(self) -> None:
        self.is_champion  = True
        self.promoted_at  = time.time()

    def demote(self) -> None:
        self.is_champion = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "version_id":     self.version_id,
            "model_id":       self.model_id,
            "version":        self.version,
            "parent_version": self.parent_version,
            "job_id":         self.job_id,
            "artifact_id":    self.artifact_id,
            "metrics":        self.metrics,
            "is_champion":    self.is_champion,
            "created_at":     self.created_at,
            "promoted_at":    self.promoted_at,
            "notes":          self.notes,
        }
