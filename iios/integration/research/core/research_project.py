"""iios/integration/research/core/research_project.py"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.integration.research.research_constants import (
    ResearchProjectStatus,
)
from iios.integration.research.core.research_metadata import ResearchMetadata


@dataclass
class ResearchProject:
    """
    Top-level research project container.

    A project groups related experiments and datasets under a common
    research objective and hypothesis.
    """
    project_id:      str                   = field(default_factory=lambda: str(uuid.uuid4()))
    name:            str                   = ""
    description:     str                   = ""
    objective:       str                   = ""
    hypothesis:      str                   = ""
    methodology:     str                   = ""
    status:          ResearchProjectStatus = ResearchProjectStatus.DRAFT
    owner:           str                   = ""
    tags:            list[str]             = field(default_factory=list)
    experiment_ids:  list[str]             = field(default_factory=list)
    dataset_ids:     list[str]             = field(default_factory=list)
    created_at:      float                 = field(default_factory=time.time)
    updated_at:      float                 = field(default_factory=time.time)
    completed_at:    float | None          = None
    metadata:        ResearchMetadata      = field(default_factory=ResearchMetadata)

    def touch(self) -> None:
        self.updated_at = time.time()
        self.metadata.touch()

    def add_experiment(self, experiment_id: str) -> None:
        if experiment_id not in self.experiment_ids:
            self.experiment_ids.append(experiment_id)
            self.touch()

    def remove_experiment(self, experiment_id: str) -> None:
        self.experiment_ids = [e for e in self.experiment_ids if e != experiment_id]
        self.touch()

    def add_dataset(self, dataset_id: str) -> None:
        if dataset_id not in self.dataset_ids:
            self.dataset_ids.append(dataset_id)
            self.touch()

    def is_active(self) -> bool:
        return self.status == ResearchProjectStatus.ACTIVE

    def experiment_count(self) -> int:
        return len(self.experiment_ids)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id":     self.project_id,
            "name":           self.name,
            "description":    self.description,
            "objective":      self.objective,
            "hypothesis":     self.hypothesis,
            "methodology":    self.methodology,
            "status":         self.status.value,
            "owner":          self.owner,
            "tags":           list(self.tags),
            "experiment_ids": list(self.experiment_ids),
            "dataset_ids":    list(self.dataset_ids),
            "created_at":     self.created_at,
            "updated_at":     self.updated_at,
            "completed_at":   self.completed_at,
        }
