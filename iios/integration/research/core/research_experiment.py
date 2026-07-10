"""iios/integration/research/core/research_experiment.py"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.integration.research.research_constants import (
    ExperimentPriority,
    ExperimentStatus,
    DEFAULT_EXPERIMENT_VERSION,
)
from iios.integration.research.core.research_metadata import ResearchMetadata


@dataclass
class ResearchExperiment:
    """
    One discrete research experiment.

    An experiment is the atomic unit of research execution.
    It has a lifecycle (DRAFT → RUNNING → COMPLETED/FAILED),
    optional dataset associations, and a versioned result.
    """
    experiment_id:  str               = field(default_factory=lambda: str(uuid.uuid4()))
    project_id:     str               = ""
    name:           str               = ""
    description:    str               = ""
    hypothesis:     str               = ""
    status:         ExperimentStatus  = ExperimentStatus.DRAFT
    priority:       ExperimentPriority = ExperimentPriority.NORMAL
    version:        str               = DEFAULT_EXPERIMENT_VERSION
    parent_id:      str               = ""   # for versioned experiments
    config:         dict[str, Any]    = field(default_factory=dict)
    dataset_ids:    list[str]         = field(default_factory=list)
    session_id:     str               = ""
    result_id:      str               = ""
    started_at:     float | None      = None
    completed_at:   float | None      = None
    duration_sec:   float             = 0.0
    error_message:  str               = ""
    tags:           list[str]         = field(default_factory=list)
    created_at:     float             = field(default_factory=time.time)
    updated_at:     float             = field(default_factory=time.time)
    metadata:       ResearchMetadata  = field(default_factory=ResearchMetadata)

    def touch(self) -> None:
        self.updated_at = time.time()

    def is_terminal(self) -> bool:
        return self.status in (
            ExperimentStatus.COMPLETED,
            ExperimentStatus.FAILED,
            ExperimentStatus.CANCELLED,
            ExperimentStatus.ARCHIVED,
        )

    def is_active(self) -> bool:
        return self.status in (ExperimentStatus.RUNNING, ExperimentStatus.PAUSED)

    def elapsed_sec(self) -> float:
        if self.started_at is None:
            return 0.0
        end = self.completed_at or time.time()
        return end - self.started_at

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id":  self.experiment_id,
            "project_id":     self.project_id,
            "name":           self.name,
            "status":         self.status.value,
            "priority":       self.priority.value,
            "version":        self.version,
            "parent_id":      self.parent_id,
            "config":         dict(self.config),
            "dataset_ids":    list(self.dataset_ids),
            "session_id":     self.session_id,
            "result_id":      self.result_id,
            "started_at":     self.started_at,
            "completed_at":   self.completed_at,
            "duration_sec":   self.duration_sec,
            "error_message":  self.error_message,
            "tags":           list(self.tags),
            "created_at":     self.created_at,
        }
