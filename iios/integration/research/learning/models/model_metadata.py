"""models/model_metadata.py — Persistent descriptor for a registered model."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from iios.integration.research.learning.learning_constants import (
    LearningType,
    ModelStatus,
    ModelTask,
)


@dataclass
class ModelMetadata:
    """
    Lightweight, serialisable descriptor for a model registered with the engine.

    This is the *registry entry* — it does NOT hold the model weights or any
    framework-specific artefacts.
    """

    model_id:      str
    name:          str
    version:       str
    model_task:    ModelTask
    learning_type: LearningType
    status:        ModelStatus
    description:   Optional[str]
    framework:     str                  # e.g. "custom", "sklearn", "torch"
    input_schema:  list[str]           # ordered feature names expected at inference
    output_schema: list[str]           # output key names
    dataset_id:    Optional[str]       # training dataset used
    artifact_id:   Optional[str]       # artefact store reference
    training_job_id: Optional[str]
    parent_model_id: Optional[str]     # for fine-tuned / distilled models
    created_at:    float
    updated_at:    float
    deployed_at:   Optional[float]
    tags:          list[str]
    metrics:       dict[str, float]    # best training metrics
    extra:         dict[str, Any]

    @classmethod
    def create(
        cls,
        name:          str,
        model_task:    ModelTask,
        learning_type: LearningType,
        *,
        model_id:      Optional[str] = None,
        version:       str           = "1.0.0",
        description:   Optional[str] = None,
        framework:     str           = "custom",
        input_schema:  Optional[list] = None,
        output_schema: Optional[list] = None,
        dataset_id:    Optional[str] = None,
        parent_model_id: Optional[str] = None,
        tags:          Optional[list] = None,
        metrics:       Optional[dict] = None,
    ) -> "ModelMetadata":
        now = time.time()
        return cls(
            model_id        = model_id or f"mdl_{uuid.uuid4().hex[:12]}",
            name            = name,
            version         = version,
            model_task      = model_task,
            learning_type   = learning_type,
            status          = ModelStatus.DRAFT,
            description     = description,
            framework       = framework,
            input_schema    = input_schema or [],
            output_schema   = output_schema or [],
            dataset_id      = dataset_id,
            artifact_id     = None,
            training_job_id = None,
            parent_model_id = parent_model_id,
            created_at      = now,
            updated_at      = now,
            deployed_at     = None,
            tags            = tags or [],
            metrics         = metrics or {},
            extra           = {},
        )

    # ── Lifecycle helpers ─────────────────────────────────────────────────────

    def mark_trained(self, job_id: str, metrics: dict[str, float]) -> None:
        self.status          = ModelStatus.TRAINED
        self.training_job_id = job_id
        self.metrics.update(metrics)
        self.updated_at      = time.time()

    def mark_validated(self) -> None:
        self.status     = ModelStatus.VALIDATED
        self.updated_at = time.time()

    def mark_deployed(self) -> None:
        self.status      = ModelStatus.DEPLOYED
        self.deployed_at = time.time()
        self.updated_at  = self.deployed_at

    def mark_archived(self) -> None:
        self.status     = ModelStatus.ARCHIVED
        self.updated_at = time.time()

    def touch(self) -> None:
        self.updated_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_id":         self.model_id,
            "name":             self.name,
            "version":          self.version,
            "model_task":       self.model_task.value,
            "learning_type":    self.learning_type.value,
            "status":           self.status.value,
            "description":      self.description,
            "framework":        self.framework,
            "input_schema":     self.input_schema,
            "output_schema":    self.output_schema,
            "dataset_id":       self.dataset_id,
            "artifact_id":      self.artifact_id,
            "training_job_id":  self.training_job_id,
            "parent_model_id":  self.parent_model_id,
            "created_at":       self.created_at,
            "updated_at":       self.updated_at,
            "deployed_at":      self.deployed_at,
            "tags":             self.tags,
            "metrics":          self.metrics,
        }
