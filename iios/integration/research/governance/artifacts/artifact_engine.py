"""artifacts/artifact_engine.py — Artifact lifecycle orchestrator."""
from __future__ import annotations

from typing import Any, Optional

from iios.integration.research.governance.governance_constants import ArtifactStatus, ArtifactType
from iios.integration.research.governance.artifacts.artifact_metadata import ArtifactMetadata
from iios.integration.research.governance.artifacts.artifact_version  import ArtifactVersion
from iios.integration.research.governance.artifacts.artifact_registry import ArtifactRegistry
from iios.integration.research.governance.artifacts.artifact_storage  import ArtifactStorage


class ArtifactEngine:
    """Facade for artifact registration, versioning, and lifecycle management."""

    def __init__(self) -> None:
        self._registry = ArtifactRegistry()
        self._storage  = ArtifactStorage()

    def register(
        self,
        name:          str,
        artifact_type: ArtifactType,
        **kwargs:      Any,
    ) -> ArtifactMetadata:
        art = ArtifactMetadata.create(name, artifact_type, **kwargs)
        self._registry.register(art)
        # Record initial version
        v = ArtifactVersion.create(
            art.artifact_id,
            art.version,
            checksum=art.checksum,
            storage_path=art.storage_path,
            size_bytes=art.size_bytes,
            created_by=art.created_by,
        )
        self._storage.store_version(v)
        return art

    def get(self, artifact_id: str) -> ArtifactMetadata:
        return self._registry.get(artifact_id)

    def add_version(
        self,
        artifact_id:  str,
        new_version:  str,
        *,
        checksum:     Optional[str] = None,
        storage_path: Optional[str] = None,
        size_bytes:    int          = 0,
        change_notes: str           = "",
        created_by:   Optional[str] = None,
    ) -> ArtifactVersion:
        art = self._registry.get(artifact_id)
        v   = ArtifactVersion.create(
            artifact_id,
            new_version,
            checksum=checksum,
            storage_path=storage_path,
            size_bytes=size_bytes,
            change_notes=change_notes,
            created_by=created_by,
        )
        self._storage.store_version(v)
        art.version      = new_version
        art.checksum     = checksum
        art.storage_path = storage_path
        art.touch()
        return v

    def lock_artifact(self, artifact_id: str) -> None:
        self._registry.get(artifact_id).lock()

    def archive_artifact(self, artifact_id: str) -> None:
        self._registry.get(artifact_id).archive()

    def versions(self, artifact_id: str) -> list[ArtifactVersion]:
        return self._storage.get_versions(artifact_id)

    def by_entity(self, entity_id: str) -> list[ArtifactMetadata]:
        return self._registry.by_entity(entity_id)

    def stats(self) -> dict[str, Any]:
        return {
            "registry": self._registry.stats(),
            "storage":  self._storage.stats(),
        }
