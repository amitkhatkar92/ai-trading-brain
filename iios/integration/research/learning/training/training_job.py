"""training/training_job.py — TrainingJob entity (lifecycle + state machine)."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from iios.integration.research.learning.learning_constants import (
    JobStatus,
    LearningType,
    ModelTask,
)
from iios.integration.research.learning.learning_exceptions import JobStateError
from iios.integration.research.learning.core.learning_configuration import LearningConfiguration

_TERMINAL = {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED}
_VALID_TRANSITIONS: dict[JobStatus, set[JobStatus]] = {
    JobStatus.PENDING:   {JobStatus.QUEUED, JobStatus.RUNNING, JobStatus.CANCELLED},
    JobStatus.QUEUED:    {JobStatus.RUNNING, JobStatus.CANCELLED},
    JobStatus.RUNNING:   {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.PAUSED},
    JobStatus.PAUSED:    {JobStatus.RUNNING, JobStatus.CANCELLED},
    JobStatus.COMPLETED: set(),
    JobStatus.FAILED:    set(),
    JobStatus.CANCELLED: set(),
}


@dataclass
class TrainingJob:
    """
    Represents a single model training request.

    Lifecycle::

        PENDING → QUEUED → RUNNING → COMPLETED
                                  ↘ FAILED
                  ↘ CANCELLED (from any non-terminal)
    """

    job_id:             str
    model_id:           str
    dataset_id:         str
    feature_pipeline_id: Optional[str]
    config:             LearningConfiguration
    status:             JobStatus
    learning_type:      LearningType
    model_task:         ModelTask
    created_at:         float
    started_at:         Optional[float]
    completed_at:       Optional[float]
    error_message:      Optional[str]
    result_id:          Optional[str]
    experiment_id:      Optional[str]
    tags:               list[str]
    metadata:           dict[str, Any]

    # ── Factory ───────────────────────────────────────────────────────────────

    @classmethod
    def create(
        cls,
        model_id:           str,
        dataset_id:         str,
        config:             LearningConfiguration,
        *,
        job_id:             Optional[str]  = None,
        feature_pipeline_id: Optional[str] = None,
        learning_type:      LearningType   = LearningType.SUPERVISED,
        model_task:         ModelTask      = ModelTask.REGRESSION,
        experiment_id:      Optional[str]  = None,
        tags:               Optional[list] = None,
        metadata:           Optional[dict] = None,
    ) -> "TrainingJob":
        return cls(
            job_id              = job_id or f"job_{uuid.uuid4().hex[:12]}",
            model_id            = model_id,
            dataset_id          = dataset_id,
            feature_pipeline_id = feature_pipeline_id,
            config              = config,
            status              = JobStatus.PENDING,
            learning_type       = learning_type,
            model_task          = model_task,
            created_at          = time.time(),
            started_at          = None,
            completed_at        = None,
            error_message       = None,
            result_id           = None,
            experiment_id       = experiment_id,
            tags                = tags or [],
            metadata            = metadata or {},
        )

    # ── Transitions ───────────────────────────────────────────────────────────

    def _transition(self, new_status: JobStatus) -> None:
        allowed = _VALID_TRANSITIONS.get(self.status, set())
        if new_status not in allowed:
            raise JobStateError(
                f"Cannot transition job '{self.job_id}' from {self.status.value} "
                f"to {new_status.value}"
            )
        self.status = new_status

    def start(self) -> None:
        self._transition(JobStatus.RUNNING)
        self.started_at = time.time()

    def complete(self, result_id: str) -> None:
        self._transition(JobStatus.COMPLETED)
        self.result_id    = result_id
        self.completed_at = time.time()

    def fail(self, error: str) -> None:
        self._transition(JobStatus.FAILED)
        self.error_message = error
        self.completed_at  = time.time()

    def cancel(self) -> None:
        self._transition(JobStatus.CANCELLED)
        self.completed_at = time.time()

    # ── Queries ───────────────────────────────────────────────────────────────

    def is_terminal(self) -> bool:
        return self.status in _TERMINAL

    def elapsed_sec(self) -> float:
        if self.started_at is None:
            return 0.0
        end = self.completed_at or time.time()
        return end - self.started_at

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id":              self.job_id,
            "model_id":            self.model_id,
            "dataset_id":          self.dataset_id,
            "feature_pipeline_id": self.feature_pipeline_id,
            "status":              self.status.value,
            "learning_type":       self.learning_type.value,
            "model_task":          self.model_task.value,
            "created_at":          self.created_at,
            "started_at":          self.started_at,
            "completed_at":        self.completed_at,
            "elapsed_sec":         self.elapsed_sec(),
            "error_message":       self.error_message,
            "result_id":           self.result_id,
            "experiment_id":       self.experiment_id,
            "tags":                self.tags,
            "config":              self.config.to_dict(),
        }
