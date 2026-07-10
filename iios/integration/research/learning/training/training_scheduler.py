"""training/training_scheduler.py — Priority queue scheduler for TrainingJob execution."""
from __future__ import annotations

import heapq
import threading
import time
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


class TrainingScheduler:
    """
    Priority-based FIFO queue for TrainingJob scheduling.

    Jobs are enqueued with a priority (lower = higher priority).
    ``pop_next()`` returns the highest-priority pending job.
    """

    def __init__(self, max_jobs: int = DEFAULT_MAX_JOBS) -> None:
        self._jobs:   dict[str, TrainingJob] = {}
        self._heap:   list[tuple[int, float, str]] = []   # (priority, created_at, job_id)
        self._max     = max_jobs
        self._lock    = threading.RLock()
        self._enqueued = 0

    def enqueue(self, job: TrainingJob, priority: int = 5) -> None:
        with self._lock:
            if job.job_id in self._jobs:
                raise JobAlreadyExistsError(f"Job '{job.job_id}' already scheduled")
            if len(self._jobs) >= self._max:
                raise JobCapacityError(f"Scheduler capacity ({self._max}) reached")
            self._jobs[job.job_id] = job
            heapq.heappush(self._heap, (priority, job.created_at, job.job_id))
            self._enqueued += 1
            job.status = JobStatus.QUEUED

    def pop_next(self) -> Optional[TrainingJob]:
        """Return and remove the next QUEUED job (highest priority). None if empty."""
        with self._lock:
            while self._heap:
                _, _, job_id = heapq.heappop(self._heap)
                job = self._jobs.get(job_id)
                if job is not None and job.status == JobStatus.QUEUED:
                    return job
            return None

    def peek_next(self) -> Optional[TrainingJob]:
        """Return (but do NOT remove) the next QUEUED job."""
        with self._lock:
            for _, _, job_id in self._heap:
                job = self._jobs.get(job_id)
                if job is not None and job.status == JobStatus.QUEUED:
                    return job
            return None

    def get(self, job_id: str) -> TrainingJob:
        with self._lock:
            job = self._jobs.get(job_id)
        if job is None:
            raise JobNotFoundError(f"Job '{job_id}' not found in scheduler")
        return job

    def has(self, job_id: str) -> bool:
        with self._lock:
            return job_id in self._jobs

    def remove(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs.pop(job_id, None)
            if job is None:
                raise JobNotFoundError(f"Job '{job_id}' not found")
            # Heap cleanup happens lazily via pop_next()

    def pending_count(self) -> int:
        with self._lock:
            return sum(1 for j in self._jobs.values()
                       if j.status in (JobStatus.PENDING, JobStatus.QUEUED))

    def all_jobs(self, status: Optional[JobStatus] = None) -> list[TrainingJob]:
        with self._lock:
            jobs = list(self._jobs.values())
        if status is not None:
            jobs = [j for j in jobs if j.status == status]
        return jobs

    def stats(self) -> dict[str, Any]:
        with self._lock:
            by_status: dict[str, int] = {}
            for job in self._jobs.values():
                key = job.status.value
                by_status[key] = by_status.get(key, 0) + 1
            return {
                "total":      len(self._jobs),
                "enqueued":   self._enqueued,
                "by_status":  by_status,
                "capacity":   self._max,
            }
