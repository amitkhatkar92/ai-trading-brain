"""evaluation/evaluation_report.py — Result of a model evaluation run."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from iios.integration.research.learning.learning_constants import ModelTask, ValidationStatus


@dataclass
class EvaluationReport:
    """
    Captures the outcome of evaluating a model on a specific dataset.

    Immutable once created via ``create()``.
    """
    report_id:     str
    model_id:      str
    model_version: str
    dataset_id:    str
    model_task:    ModelTask
    status:        ValidationStatus
    metrics:       dict[str, float]
    n_samples:     int
    evaluation_sec: float
    error:         Optional[str]
    created_at:    float
    metadata:      dict[str, Any]

    @classmethod
    def create(
        cls,
        model_id:       str,
        model_version:  str,
        dataset_id:     str,
        model_task:     ModelTask,
        metrics:        dict[str, float],
        evaluation_sec: float,
        *,
        report_id:   Optional[str] = None,
        n_samples:   int           = 0,
        status:      ValidationStatus = ValidationStatus.PASSED,
        error:       Optional[str] = None,
        metadata:    Optional[dict] = None,
    ) -> "EvaluationReport":
        return cls(
            report_id      = report_id or f"eval_{uuid.uuid4().hex[:10]}",
            model_id       = model_id,
            model_version  = model_version,
            dataset_id     = dataset_id,
            model_task     = model_task,
            status         = status,
            metrics        = dict(metrics),
            n_samples      = n_samples,
            evaluation_sec = evaluation_sec,
            error          = error,
            created_at     = time.time(),
            metadata       = metadata or {},
        )

    @property
    def is_success(self) -> bool:
        return self.status == ValidationStatus.PASSED

    def has_metric(self, name: str) -> bool:
        return name in self.metrics

    def get_metric(self, name: str, default: float = 0.0) -> float:
        return self.metrics.get(name, default)

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id":      self.report_id,
            "model_id":       self.model_id,
            "model_version":  self.model_version,
            "dataset_id":     self.dataset_id,
            "model_task":     self.model_task.value,
            "status":         self.status.value,
            "metrics":        self.metrics,
            "n_samples":      self.n_samples,
            "evaluation_sec": self.evaluation_sec,
            "error":          self.error,
            "created_at":     self.created_at,
        }
