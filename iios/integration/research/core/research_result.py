"""iios/integration/research/core/research_result.py"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.integration.research.research_constants import ExperimentStatus


@dataclass
class ResearchResult:
    """
    The output of a completed (or failed) experiment run.

    Stores metrics, artifact references, and success/failure state.
    """
    result_id:     str             = field(default_factory=lambda: str(uuid.uuid4()))
    experiment_id: str             = ""
    project_id:    str             = ""
    is_success:    bool            = False
    metrics:       dict[str, Any]  = field(default_factory=dict)
    artifacts:     list[str]       = field(default_factory=list)   # file paths / URIs
    summary:       str             = ""
    error:         str             = ""
    duration_sec:  float           = 0.0
    created_at:    float           = field(default_factory=time.time)
    metadata:      dict[str, Any]  = field(default_factory=dict)

    def has_metric(self, key: str) -> bool:
        return key in self.metrics

    def get_metric(self, key: str, default: Any = None) -> Any:
        return self.metrics.get(key, default)

    def add_artifact(self, path: str) -> None:
        if path not in self.artifacts:
            self.artifacts.append(path)

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_id":     self.result_id,
            "experiment_id": self.experiment_id,
            "project_id":    self.project_id,
            "is_success":    self.is_success,
            "metrics":       dict(self.metrics),
            "artifacts":     list(self.artifacts),
            "summary":       self.summary,
            "error":         self.error,
            "duration_sec":  self.duration_sec,
            "created_at":    self.created_at,
        }
