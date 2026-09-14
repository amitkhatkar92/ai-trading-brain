"""core/training_result.py — Outcome of a training job."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class TrainingResult:
    """
    Immutable record of a completed training run.

    ``metrics`` maps metric names to their final values, e.g.::

        {"train_loss": 0.08, "val_loss": 0.12, "val_accuracy": 0.94}

    The keys and semantics are defined by the model implementation.
    """

    result_id:        str
    job_id:           str
    model_id:         str
    model_version:    str
    artifact_id:      Optional[str]
    metrics:          dict[str, float]
    epochs_completed: int
    training_sec:     float
    is_success:       bool
    error:            Optional[str]
    created_at:       float

    # ── Factory ───────────────────────────────────────────────────────────────

    @classmethod
    def create(
        cls,
        job_id:           str,
        model_id:         str,
        model_version:    str,
        metrics:          dict[str, float],
        training_sec:     float,
        *,
        result_id:        Optional[str]   = None,
        artifact_id:      Optional[str]   = None,
        epochs_completed: int             = 0,
        is_success:       bool            = True,
        error:            Optional[str]   = None,
    ) -> "TrainingResult":
        return cls(
            result_id        = result_id or f"tr_{uuid.uuid4().hex[:12]}",
            job_id           = job_id,
            model_id         = model_id,
            model_version    = model_version,
            artifact_id      = artifact_id,
            metrics          = dict(metrics),
            epochs_completed = epochs_completed,
            training_sec     = training_sec,
            is_success       = is_success,
            error            = error,
            created_at       = time.time(),
        )

    # ── Accessors ─────────────────────────────────────────────────────────────

    def has_metric(self, name: str) -> bool:
        return name in self.metrics

    def get_metric(self, name: str, default: float = 0.0) -> float:
        return self.metrics.get(name, default)

    # ── Serialization ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_id":        self.result_id,
            "job_id":           self.job_id,
            "model_id":         self.model_id,
            "model_version":    self.model_version,
            "artifact_id":      self.artifact_id,
            "metrics":          self.metrics,
            "epochs_completed": self.epochs_completed,
            "training_sec":     self.training_sec,
            "is_success":       self.is_success,
            "error":            self.error,
            "created_at":       self.created_at,
        }
