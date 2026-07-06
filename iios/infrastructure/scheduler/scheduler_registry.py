"""
iios/infrastructure/scheduler/scheduler_registry.py
====================================================
Registry for JobDefinition objects.
"""

from __future__ import annotations

import threading
from typing import Optional

from ..infrastructure_exceptions import SchedulerError
from ..infrastructure_models import JobDefinition

__all__ = ["SchedulerRegistry"]


class SchedulerRegistry:
    """Stores and retrieves JobDefinition objects."""

    def __init__(self) -> None:
        self._jobs: dict[str, JobDefinition] = {}
        self._lock = threading.RLock()

    def add(self, job: JobDefinition, allow_override: bool = False) -> None:
        with self._lock:
            if job.job_id in self._jobs and not allow_override:
                raise SchedulerError(
                    f"Job '{job.job_id}' already registered",
                    code="INF-SCH-001",
                    context={"job_id": job.job_id},
                )
            self._jobs[job.job_id] = job

    def get(self, job_id: str) -> JobDefinition:
        with self._lock:
            j = self._jobs.get(job_id)
        if j is None:
            raise SchedulerError(
                f"Job '{job_id}' not found",
                code="INF-SCH-002",
                context={"job_id": job_id},
            )
        return j

    def get_optional(self, job_id: str) -> Optional[JobDefinition]:
        with self._lock:
            return self._jobs.get(job_id)

    def remove(self, job_id: str) -> bool:
        with self._lock:
            return self._jobs.pop(job_id, None) is not None

    def all(self) -> list[JobDefinition]:
        with self._lock:
            return list(self._jobs.values())

    def enabled(self) -> list[JobDefinition]:
        with self._lock:
            return [j for j in self._jobs.values() if j.enabled]

    def disable(self, job_id: str) -> None:
        job = self.get(job_id)
        job.enabled = False

    def enable(self, job_id: str) -> None:
        job = self.get(job_id)
        job.enabled = True

    def count(self) -> int:
        with self._lock:
            return len(self._jobs)

    def clear(self) -> None:
        with self._lock:
            self._jobs.clear()
