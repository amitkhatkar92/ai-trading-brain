"""models/model_registry.py — Thread-safe registry of ModelMetadata."""
from __future__ import annotations

import threading
from typing import Any, Optional

from iios.integration.research.learning.learning_constants import (
    DEFAULT_MAX_MODELS,
    ModelStatus,
    ModelTask,
)
from iios.integration.research.learning.learning_exceptions import (
    ModelError,
    ModelNotFoundError,
    ModelVersionError,
)
from iios.integration.research.learning.models.model_metadata  import ModelMetadata
from iios.integration.research.learning.models.model_version   import ModelVersion
from iios.integration.research.learning.models.model_artifact  import ModelArtifact
from iios.integration.research.learning.models.model_statistics import ModelStatistics


class ModelRegistry:
    """
    Central in-memory store for ModelMetadata, ModelVersion, and ModelArtifact.

    Thread-safe via a single RLock.
    Capacity is capped at ``max_models`` total metadata entries.
    """

    def __init__(self, max_models: int = DEFAULT_MAX_MODELS) -> None:
        self._models:    dict[str, ModelMetadata]          = {}
        self._versions:  dict[str, list[ModelVersion]]     = {}   # model_id → versions
        self._artifacts: dict[str, ModelArtifact]          = {}   # artifact_id → artefact
        self._max        = max_models
        self._lock       = threading.RLock()
        self._total_registered = 0

    # ── Model CRUD ────────────────────────────────────────────────────────────

    def register(self, meta: ModelMetadata) -> ModelMetadata:
        with self._lock:
            if meta.model_id not in self._models and len(self._models) >= self._max:
                raise ModelError(f"Model registry capacity ({self._max}) reached")
            if meta.model_id not in self._models:
                self._total_registered += 1
            self._models[meta.model_id] = meta
        return meta

    def get(self, model_id: str) -> ModelMetadata:
        with self._lock:
            meta = self._models.get(model_id)
        if meta is None:
            raise ModelNotFoundError(f"Model '{model_id}' not found")
        return meta

    def remove(self, model_id: str) -> None:
        with self._lock:
            if model_id not in self._models:
                raise ModelNotFoundError(f"Model '{model_id}' not found")
            del self._models[model_id]
            self._versions.pop(model_id, None)

    def has(self, model_id: str) -> bool:
        with self._lock:
            return model_id in self._models

    # ── Queries ───────────────────────────────────────────────────────────────

    def all_models(self) -> list[ModelMetadata]:
        with self._lock:
            return list(self._models.values())

    def by_task(self, task: ModelTask) -> list[ModelMetadata]:
        with self._lock:
            return [m for m in self._models.values() if m.model_task == task]

    def by_status(self, status: ModelStatus) -> list[ModelMetadata]:
        with self._lock:
            return [m for m in self._models.values() if m.status == status]

    def find_by_name(self, name: str) -> list[ModelMetadata]:
        with self._lock:
            return [m for m in self._models.values() if m.name == name]

    # ── Version management ────────────────────────────────────────────────────

    def add_version(self, version: ModelVersion) -> None:
        with self._lock:
            if version.model_id not in self._models:
                raise ModelNotFoundError(f"Model '{version.model_id}' not found")
            vlist = self._versions.setdefault(version.model_id, [])
            vlist.append(version)

    def versions(self, model_id: str) -> list[ModelVersion]:
        with self._lock:
            return list(self._versions.get(model_id, []))

    def get_version(self, model_id: str, version: str) -> ModelVersion:
        with self._lock:
            for v in self._versions.get(model_id, []):
                if v.version == version:
                    return v
        raise ModelVersionError(f"Version '{version}' not found for model '{model_id}'")

    # ── Artifact management ───────────────────────────────────────────────────

    def store_artifact(self, artifact: ModelArtifact) -> None:
        with self._lock:
            self._artifacts[artifact.artifact_id] = artifact
            if artifact.model_id in self._models:
                self._models[artifact.model_id].artifact_id = artifact.artifact_id

    def get_artifact(self, artifact_id: str) -> ModelArtifact:
        with self._lock:
            art = self._artifacts.get(artifact_id)
        if art is None:
            raise ModelError(f"Artifact '{artifact_id}' not found")
        return art

    # ── Stats ─────────────────────────────────────────────────────────────────

    def count(self) -> int:
        with self._lock:
            return len(self._models)

    def stats(self) -> dict[str, Any]:
        with self._lock:
            model_list = list(self._models.values())
        return {
            **ModelStatistics.compute(model_list).to_dict(),
            "total_versions":   sum(len(v) for v in self._versions.values()),
            "total_artifacts":  len(self._artifacts),
            "capacity":         self._max,
        }
