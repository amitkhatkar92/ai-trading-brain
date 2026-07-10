"""learning_registry.py — Thread-safe registry for TrainingJob objects."""
from __future__ import annotations

import threading
from typing import Any, Optional

from iios.integration.research.learning.learning_constants import (
    DEFAULT_MAX_JOBS,
    JobStatus,
)
from iios.integration.research.learning.learning_exceptions import (
    JobAlreadyExistsError,
    JobCapacityError,
    JobNotFoundError,
)
from iios.integration.research.learning.training.training_job import TrainingJob


class LearningRegistry:
    """
    Central in-memory registry for all TrainingJob objects.

    TrainingScheduler handles priority ordering; this class is the source of
    truth for job lookup and status queries.

    Thread-safe via a single RLock.
    """

    def __init__(self, max_jobs: int = DEFAULT_MAX_JOBS) -> None:
        self._jobs:   dict[str, TrainingJob] = {}
        self._max     = max_jobs
        self._lock    = threading.RLock()
        self._total   = 0

    def register(self, job: TrainingJob) -> None:
        with self._lock:
            if job.job_id in self._jobs:
                raise JobAlreadyExistsError(f"Job '{job.job_id}' already registered")
            if len(self._jobs) >= self._max:
                raise JobCapacityError(f"Registry capacity ({self._max}) reached")
            self._jobs[job.job_id] = job
            self._total += 1

    def get(self, job_id: str) -> TrainingJob:
        with self._lock:
            job = self._jobs.get(job_id)
        if job is None:
            raise JobNotFoundError(f"Job '{job_id}' not found")
        return job

    def has(self, job_id: str) -> bool:
        with self._lock:
            return job_id in self._jobs

    def remove(self, job_id: str) -> None:
        with self._lock:
            if job_id not in self._jobs:
                raise JobNotFoundError(f"Job '{job_id}' not found")
            del self._jobs[job_id]

    def all_jobs(self, status: Optional[JobStatus] = None) -> list[TrainingJob]:
        with self._lock:
            jobs = list(self._jobs.values())
        if status is not None:
            jobs = [j for j in jobs if j.status == status]
        return jobs

    def count(self) -> int:
        with self._lock:
            return len(self._jobs)

    def stats(self) -> dict[str, Any]:
        with self._lock:
            by_status: dict[str, int] = {}
            for job in self._jobs.values():
                key = job.status.value
                by_status[key] = by_status.get(key, 0) + 1
            return {
                "total":          len(self._jobs),
                "total_ever":     self._total,
                "capacity":       self._max,
                "by_status":      by_status,
            }
