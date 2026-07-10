"""training/checkpoint_manager.py — Lightweight checkpoint tracking per job."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any, Optional

from iios.integration.research.learning.learning_constants import (
    CheckpointStatus,
    DEFAULT_MAX_CHECKPOINTS,
)
from iios.integration.research.learning.learning_exceptions import CheckpointError


@dataclass
class Checkpoint:
    """A single training checkpoint."""
    checkpoint_id: str
    job_id:        str
    epoch:         int
    metrics:       dict[str, float]
    storage_path:  Optional[str]
    status:        CheckpointStatus
    created_at:    float

    @classmethod
    def create(
        cls,
        job_id:        str,
        epoch:         int,
        metrics:       dict[str, float],
        *,
        checkpoint_id: Optional[str]  = None,
        storage_path:  Optional[str]  = None,
    ) -> "Checkpoint":
        return cls(
            checkpoint_id = checkpoint_id or f"ckpt_{uuid.uuid4().hex[:10]}",
            job_id        = job_id,
            epoch         = epoch,
            metrics       = dict(metrics),
            storage_path  = storage_path,
            status        = CheckpointStatus.CREATED,
            created_at    = time.time(),
        )

    def validate(self) -> None:
        self.status = CheckpointStatus.VALID

    def mark_corrupt(self) -> None:
        self.status = CheckpointStatus.CORRUPT

    def to_dict(self) -> dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "job_id":        self.job_id,
            "epoch":         self.epoch,
            "metrics":       self.metrics,
            "storage_path":  self.storage_path,
            "status":        self.status.value,
            "created_at":    self.created_at,
        }


class CheckpointManager:
    """
    Manages per-job checkpoint records in memory (no I/O).

    Jobs needing persistence delegate serialisation to ``BaseModel.save()``.
    """

    def __init__(self, max_per_job: int = DEFAULT_MAX_CHECKPOINTS) -> None:
        self._store:   dict[str, list[Checkpoint]] = {}  # job_id → checkpoints
        self._max      = max_per_job

    def add(self, checkpoint: Checkpoint) -> None:
        job_checkpoints = self._store.setdefault(checkpoint.job_id, [])
        if len(job_checkpoints) >= self._max:
            # Evict oldest (keep the best metric checkpoint)
            job_checkpoints.sort(key=lambda c: c.created_at)
            job_checkpoints.pop(0)
        job_checkpoints.append(checkpoint)

    def latest(self, job_id: str) -> Optional[Checkpoint]:
        checkpoints = self._store.get(job_id, [])
        if not checkpoints:
            return None
        return max(checkpoints, key=lambda c: c.epoch)

    def best(
        self,
        job_id:           str,
        metric:           str,
        higher_is_better: bool = True,
    ) -> Optional[Checkpoint]:
        checkpoints = [c for c in self._store.get(job_id, []) if metric in c.metrics]
        if not checkpoints:
            return None
        return max(checkpoints, key=lambda c: (c.metrics[metric] if higher_is_better
                                               else -c.metrics[metric]))

    def all_for_job(self, job_id: str) -> list[Checkpoint]:
        return list(self._store.get(job_id, []))

    def clear_job(self, job_id: str) -> None:
        self._store.pop(job_id, None)

    def count(self, job_id: Optional[str] = None) -> int:
        if job_id is not None:
            return len(self._store.get(job_id, []))
        return sum(len(v) for v in self._store.values())
