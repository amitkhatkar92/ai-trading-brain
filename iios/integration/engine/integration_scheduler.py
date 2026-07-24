"""
integration_scheduler.py — iios.integration.engine
----------------------------------------------------
IntegrationScheduler — manages a priority queue of scheduled
integration requests.

Supports:
  IMMEDIATE, CONTINUOUS, SCHEDULED, EVENT_DRIVEN,
  PRIORITY, BATCH, RETRY dispatch modes.

C15 Enterprise Integration & Connectivity — Phase 1, Module 2
"""
from __future__ import annotations

import heapq
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import DEFAULT_PRIORITY, DEFAULT_QUEUE_SIZE, SchedulerMode
from .integration_request import IntegrationRequest

_log = get_logger(__name__)


@dataclass
class ScheduledJob:
    """A scheduled integration request with priority and mode metadata."""
    job_id:      str
    request:     IntegrationRequest
    mode:        SchedulerMode
    priority:    int
    scheduled_at: str
    run_at:      Optional[str]   # ISO timestamp; None = immediate

    def __lt__(self, other: "ScheduledJob") -> bool:
        # Lower priority number = higher urgency for the heap
        return self.priority < other.priority

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id":       self.job_id,
            "request_id":   self.request.request_id,
            "mode":         self.mode.value,
            "priority":     self.priority,
            "scheduled_at": self.scheduled_at,
            "run_at":       self.run_at,
        }


class IntegrationScheduler:
    """
    Thread-safe priority queue for scheduled integration requests.

    Supports all SchedulerModes.  The engine calls ``next()`` to
    retrieve the highest-priority pending job.
    """

    def __init__(self, max_queue: int = DEFAULT_QUEUE_SIZE) -> None:
        self._max   = max_queue
        self._heap: List[ScheduledJob] = []   # min-heap by priority
        self._jobs: Dict[str, ScheduledJob] = {}
        self._cancelled: set = set()
        self._lock  = threading.Lock()

    # ----------------------------------------------------------------
    # Submit
    # ----------------------------------------------------------------

    def submit(
        self,
        request:  IntegrationRequest,
        mode:     SchedulerMode   = SchedulerMode.IMMEDIATE,
        priority: int             = DEFAULT_PRIORITY,
        run_at:   Optional[str]   = None,
    ) -> str:
        """
        Add a request to the scheduling queue.

        Returns:
            job_id
        """
        job = ScheduledJob(
            job_id       = f"job-{uuid.uuid4().hex[:12]}",
            request      = request,
            mode         = mode,
            priority     = priority,
            scheduled_at = datetime.now(tz=timezone.utc).isoformat(),
            run_at       = run_at,
        )
        with self._lock:
            if len(self._jobs) >= self._max:
                _log.warning(
                    f"Scheduler queue full ({self._max}); dropping job for "
                    f"request={request.request_id!r}"
                )
                return job.job_id   # silently drop but return id
            heapq.heappush(self._heap, job)
            self._jobs[job.job_id] = job
        _log.debug(
            f"Scheduler: submitted job={job.job_id!r} "
            f"mode={mode.value!r} priority={priority}"
        )
        return job.job_id

    def cancel(self, job_id: str) -> bool:
        with self._lock:
            if job_id in self._jobs:
                self._cancelled.add(job_id)
                return True
        return False

    # ----------------------------------------------------------------
    # Consume
    # ----------------------------------------------------------------

    def next(self) -> Optional[ScheduledJob]:
        """Return and remove the highest-priority non-cancelled job."""
        with self._lock:
            while self._heap:
                job = heapq.heappop(self._heap)
                self._jobs.pop(job.job_id, None)
                if job.job_id in self._cancelled:
                    self._cancelled.discard(job.job_id)
                    continue
                return job
            return None

    def peek(self) -> Optional[ScheduledJob]:
        """Return (without removing) the highest-priority non-cancelled job."""
        with self._lock:
            for job in self._heap:
                if job.job_id not in self._cancelled:
                    return job
            return None

    # ----------------------------------------------------------------
    # Introspection
    # ----------------------------------------------------------------

    def queue_size(self) -> int:
        with self._lock:
            return len(self._jobs) - len(self._cancelled)

    def pending_job_ids(self) -> List[str]:
        with self._lock:
            return [
                jid for jid in self._jobs
                if jid not in self._cancelled
            ]

    def clear(self) -> None:
        with self._lock:
            self._heap.clear()
            self._jobs.clear()
            self._cancelled.clear()
