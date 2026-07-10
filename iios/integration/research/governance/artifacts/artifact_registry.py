"""artifacts/artifact_registry.py — Thread-safe artifact store."""
from __future__ import annotations

import threading
from typing import Any, Optional

from iios.integration.research.governance.governance_constants import (
    ArtifactStatus,
    ArtifactType,
    DEFAULT_MAX_ARTIFACTS,
)
from iios.integration.research.governance.governance_exceptions import (
    ArtifactNotFoundError,
    LineageCapacityError,
)
from iios.integration.research.governance.artifacts.artifact_metadata import ArtifactMetadata


class ArtifactRegistry:
    """Thread-safe store for ArtifactMetadata instances."""

    def __init__(self, max_artifacts: int = DEFAULT_MAX_ARTIFACTS) -> None:
        self._artifacts: dict[str, ArtifactMetadata] = {}
        self._max  = max_artifacts
        self._lock = threading.RLock()

    def register(self, artifact: ArtifactMetadata) -> None:
        with self._lock:
            if len(self._artifacts) >= self._max:
                raise LineageCapacityError(f"Artifact registry capacity ({self._max}) reached")
            self._artifacts[artifact.artifact_id] = artifact

    def get(self, artifact_id: str) -> ArtifactMetadata:
        with self._lock:
            art = self._artifacts.get(artifact_id)
        if art is None:
            raise ArtifactNotFoundError(f"Artifact '{artifact_id}' not found")
        return art

    def has(self, artifact_id: str) -> bool:
        with self._lock:
            return artifact_id in self._artifacts

    def by_type(self, artifact_type: ArtifactType) -> list[ArtifactMetadata]:
        with self._lock:
            return [a for a in self._artifacts.values() if a.artifact_type == artifact_type]

    def by_status(self, status: ArtifactStatus) -> list[ArtifactMetadata]:
        with self._lock:
            return [a for a in self._artifacts.values() if a.status == status]

    def by_entity(self, entity_id: str) -> list[ArtifactMetadata]:
        with self._lock:
            return [a for a in self._artifacts.values() if a.entity_id == entity_id]

    def all_artifacts(self) -> list[ArtifactMetadata]:
        with self._lock:
            return list(self._artifacts.values())

    def count(self) -> int:
        with self._lock:
            return len(self._artifacts)

    def stats(self) -> dict[str, Any]:
        with self._lock:
            by_type: dict[str, int] = {}
            for a in self._artifacts.values():
                k = a.artifact_type.value
                by_type[k] = by_type.get(k, 0) + 1
            return {
                "total":    len(self._artifacts),
                "by_type":  by_type,
                "capacity": self._max,
            }
