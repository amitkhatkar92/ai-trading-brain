"""iios/integration/research/core/research_session.py"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.integration.research.research_constants import ResearchSessionStatus


@dataclass
class ResearchSession:
    """
    Execution session for one experiment run.

    Created by the ExperimentRunner when an experiment starts.
    Captures timing, step progress, and optional checkpoint state.
    """
    session_id:     str                   = field(default_factory=lambda: str(uuid.uuid4()))
    experiment_id:  str                   = ""
    project_id:     str                   = ""
    status:         ResearchSessionStatus = ResearchSessionStatus.IDLE
    step:           int                   = 0
    total_steps:    int                   = 0
    started_at:     float | None          = None
    ended_at:       float | None          = None
    last_checkpoint: str                  = ""   # checkpoint_id
    error_message:  str                   = ""
    created_at:     float                 = field(default_factory=time.time)
    metadata:       dict[str, Any]        = field(default_factory=dict)

    def start(self) -> None:
        self.status     = ResearchSessionStatus.ACTIVE
        self.started_at = time.time()

    def end(self, failed: bool = False) -> None:
        self.status   = ResearchSessionStatus.FAILED if failed else ResearchSessionStatus.COMPLETED
        self.ended_at = time.time()

    def abort(self) -> None:
        self.status   = ResearchSessionStatus.ABORTED
        self.ended_at = time.time()

    def is_active(self) -> bool:
        return self.status in (ResearchSessionStatus.ACTIVE, ResearchSessionStatus.PAUSED)

    def duration_sec(self) -> float:
        if self.started_at is None:
            return 0.0
        end = self.ended_at or time.time()
        return end - self.started_at

    def progress(self) -> float:
        if self.total_steps <= 0:
            return 0.0
        return min(1.0, self.step / self.total_steps)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id":    self.session_id,
            "experiment_id": self.experiment_id,
            "project_id":    self.project_id,
            "status":        self.status.value,
            "step":          self.step,
            "total_steps":   self.total_steps,
            "started_at":    self.started_at,
            "ended_at":      self.ended_at,
        }
