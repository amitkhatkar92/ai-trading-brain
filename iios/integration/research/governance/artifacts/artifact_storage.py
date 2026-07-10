"""artifacts/artifact_storage.py — In-memory path/checksum store."""
from __future__ import annotations

import threading
from typing import Any, Optional

from iios.integration.research.governance.artifacts.artifact_version import ArtifactVersion


class ArtifactStorage:
    """
    In-memory store mapping artifact_id → list of version entries.

    This is a lightweight facade over an append-only log. In production the
    persistence layer (S3, local FS, etc.) is injected externally — this class
    only tracks what was stored and where.
    """

    def __init__(self) -> None:
        self._versions: dict[str, list[ArtifactVersion]] = {}
        self._lock = threading.RLock()

    def store_version(self, version: ArtifactVersion) -> None:
        with self._lock:
            self._versions.setdefault(version.artifact_id, []).append(version)

    def get_versions(self, artifact_id: str) -> list[ArtifactVersion]:
        with self._lock:
            return list(self._versions.get(artifact_id, []))

    def latest_version(self, artifact_id: str) -> Optional[ArtifactVersion]:
        with self._lock:
            vs = self._versions.get(artifact_id)
        if not vs:
            return None
        return max(vs, key=lambda v: v.created_at)

    def total_artifacts(self) -> int:
        with self._lock:
            return len(self._versions)

    def total_versions(self) -> int:
        with self._lock:
            return sum(len(v) for v in self._versions.values())

    def stats(self) -> dict[str, Any]:
        return {
            "artifacts": self.total_artifacts(),
            "versions":  self.total_versions(),
        }
