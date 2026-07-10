"""core/experiment.py — Experiment tracking entity."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from iios.integration.research.learning.learning_constants import (
    ExperimentStatus,
    LearningType,
    ModelTask,
)
from iios.integration.research.learning.learning_exceptions import ExperimentError


@dataclass
class Experiment:
    """
    Groups related training jobs under a named experiment.

    Tracks which jobs belong to the experiment, which produced the best result,
    and what the optimisation metric was.
    """

    experiment_id:     str
    name:              str
    description:       Optional[str]
    status:            ExperimentStatus
    model_task:        ModelTask
    learning_type:     LearningType
    job_ids:           list[str]
    best_job_id:       Optional[str]
    best_metric_name:  str
    best_metric_value: float
    higher_is_better:  bool
    created_at:        float
    updated_at:        float
    completed_at:      Optional[float]
    tags:              list[str]
    metadata:          dict[str, Any]

    # ── Factory ───────────────────────────────────────────────────────────────

    @classmethod
    def create(
        cls,
        name:             str,
        model_task:       ModelTask,
        learning_type:    LearningType,
        *,
        experiment_id:    Optional[str] = None,
        description:      Optional[str] = None,
        best_metric_name: str           = "val_loss",
        higher_is_better: bool          = False,
        tags:             Optional[list] = None,
        metadata:         Optional[dict] = None,
    ) -> "Experiment":
        now = time.time()
        return cls(
            experiment_id     = experiment_id or f"exp_{uuid.uuid4().hex[:12]}",
            name              = name,
            description       = description,
            status            = ExperimentStatus.ACTIVE,
            model_task        = model_task,
            learning_type     = learning_type,
            job_ids           = [],
            best_job_id       = None,
            best_metric_name  = best_metric_name,
            best_metric_value = float("-inf") if higher_is_better else float("inf"),
            higher_is_better  = higher_is_better,
            created_at        = now,
            updated_at        = now,
            completed_at      = None,
            tags              = tags or [],
            metadata          = metadata or {},
        )

    # ── Job management ────────────────────────────────────────────────────────

    def add_job(self, job_id: str) -> None:
        if job_id not in self.job_ids:
            self.job_ids.append(job_id)
        self.updated_at = time.time()

    def update_best(self, job_id: str, metric_value: float) -> None:
        improved = (
            (self.higher_is_better and metric_value > self.best_metric_value) or
            (not self.higher_is_better and metric_value < self.best_metric_value)
        )
        if improved or self.best_job_id is None:
            self.best_job_id       = job_id
            self.best_metric_value = metric_value
        self.updated_at = time.time()

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def complete(self) -> None:
        self.status       = ExperimentStatus.COMPLETED
        self.completed_at = time.time()
        self.updated_at   = self.completed_at

    def fail(self, message: str = "") -> None:
        self.status       = ExperimentStatus.FAILED
        self.completed_at = time.time()
        self.updated_at   = self.completed_at
        if message:
            self.metadata["failure_reason"] = message

    def archive(self) -> None:
        self.status     = ExperimentStatus.ARCHIVED
        self.updated_at = time.time()

    def is_terminal(self) -> bool:
        return self.status in (
            ExperimentStatus.COMPLETED,
            ExperimentStatus.FAILED,
            ExperimentStatus.ARCHIVED,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id":     self.experiment_id,
            "name":              self.name,
            "description":       self.description,
            "status":            self.status.value,
            "model_task":        self.model_task.value,
            "learning_type":     self.learning_type.value,
            "job_count":         len(self.job_ids),
            "best_job_id":       self.best_job_id,
            "best_metric_name":  self.best_metric_name,
            "best_metric_value": self.best_metric_value,
            "higher_is_better":  self.higher_is_better,
            "created_at":        self.created_at,
            "updated_at":        self.updated_at,
            "completed_at":      self.completed_at,
            "tags":              self.tags,
            "metadata":          self.metadata,
        }
