"""iios/integration/research/core/research_statistics.py"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ResearchStatistics:
    """
    Aggregated statistics snapshot for the research framework.

    Computed on demand from live registry state.
    """
    stat_id:              str   = field(default_factory=lambda: str(uuid.uuid4()))
    computed_at:          float = field(default_factory=time.time)
    total_projects:       int   = 0
    active_projects:      int   = 0
    total_experiments:    int   = 0
    running_experiments:  int   = 0
    completed_experiments: int  = 0
    failed_experiments:   int   = 0
    cancelled_experiments: int  = 0
    archived_experiments: int   = 0
    total_datasets:       int   = 0
    total_results:        int   = 0
    avg_duration_sec:     float = 0.0
    success_rate:         float = 0.0   # completed / (completed + failed), [0,1]

    @classmethod
    def compute(
        cls,
        projects:    list,
        experiments: list,
        datasets:    list,
        results:     list,
    ) -> "ResearchStatistics":
        from iios.integration.research.research_constants import (
            ResearchProjectStatus, ExperimentStatus,
        )
        s = cls()
        s.total_projects    = len(projects)
        s.active_projects   = sum(1 for p in projects if p.status == ResearchProjectStatus.ACTIVE)
        s.total_experiments = len(experiments)
        s.running_experiments   = sum(1 for e in experiments if e.status == ExperimentStatus.RUNNING)
        s.completed_experiments = sum(1 for e in experiments if e.status == ExperimentStatus.COMPLETED)
        s.failed_experiments    = sum(1 for e in experiments if e.status == ExperimentStatus.FAILED)
        s.cancelled_experiments = sum(1 for e in experiments if e.status == ExperimentStatus.CANCELLED)
        s.archived_experiments  = sum(1 for e in experiments if e.status == ExperimentStatus.ARCHIVED)
        s.total_datasets = len(datasets)
        s.total_results  = len(results)
        finished = [e for e in experiments if e.duration_sec > 0]
        if finished:
            s.avg_duration_sec = sum(e.duration_sec for e in finished) / len(finished)
        denom = s.completed_experiments + s.failed_experiments
        if denom > 0:
            s.success_rate = s.completed_experiments / denom
        return s

    def to_dict(self) -> dict[str, Any]:
        return {
            "stat_id":               self.stat_id,
            "computed_at":           self.computed_at,
            "total_projects":        self.total_projects,
            "active_projects":       self.active_projects,
            "total_experiments":     self.total_experiments,
            "running_experiments":   self.running_experiments,
            "completed_experiments": self.completed_experiments,
            "failed_experiments":    self.failed_experiments,
            "total_datasets":        self.total_datasets,
            "avg_duration_sec":      self.avg_duration_sec,
            "success_rate":          self.success_rate,
        }
