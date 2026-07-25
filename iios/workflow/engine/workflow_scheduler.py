"""
workflow_scheduler.py — iios.workflow.engine
---------------------------------------------
WorkflowScheduler — manages scheduling of workflow requests into
the WorkflowQueue with priority-aware ordering.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 2
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import DEFAULT_PRIORITY, WorkflowDispatchMode
from .workflow_priority import PriorityWorkflowItem
from .workflow_queue import WorkflowQueue
from .workflow_request import WorkflowEngineRequest

_log = get_logger(__name__)


@dataclass
class ScheduledWorkflowJob:
    """A scheduled workflow request awaiting dispatch."""
    job_id:       str
    request:      WorkflowEngineRequest
    mode:         WorkflowDispatchMode
    priority:     int
    scheduled_at: str
    run_at:       Optional[str]   # ISO timestamp; None = immediate

    def __lt__(self, other: "ScheduledWorkflowJob") -> bool:
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


class WorkflowScheduler:
    """
    Thread-safe workflow scheduler.

    Accepts workflow requests and places them into the WorkflowQueue
    with correct priority ordering based on dispatch mode and request
    priority.
    """

    def __init__(
        self,
        queue: Optional[WorkflowQueue] = None,
    ) -> None:
        self._queue:     WorkflowQueue                  = queue or WorkflowQueue()
        self._jobs:      Dict[str, ScheduledWorkflowJob] = {}
        self._item_ids:  Dict[str, str]                 = {}   # job_id → item_id
        self._seq:       int                            = 0
        self._lock       = threading.Lock()

    # ----------------------------------------------------------------
    # Schedule
    # ----------------------------------------------------------------

    def schedule(
        self,
        request:  WorkflowEngineRequest,
        *,
        priority: Optional[int] = None,
        run_at:   Optional[str] = None,
    ) -> ScheduledWorkflowJob:
        """
        Schedule a workflow request for execution.

        Assigns final priority (request.priority unless overridden),
        creates a ScheduledWorkflowJob, and enqueues it.

        Returns:
            ScheduledWorkflowJob
        """
        effective_priority = priority if priority is not None else request.priority
        with self._lock:
            self._seq += 1
            seq = self._seq

        item = PriorityWorkflowItem.create(request, seq, priority=effective_priority)
        job = ScheduledWorkflowJob(
            job_id       = f"wsj-{uuid.uuid4().hex[:12]}",
            request      = request,
            mode         = request.dispatch_mode,
            priority     = effective_priority,
            scheduled_at = datetime.now(tz=timezone.utc).isoformat(),
            run_at       = run_at,
        )
        with self._lock:
            self._jobs[job.job_id]     = job
            self._item_ids[job.job_id] = item.item_id

        self._queue.enqueue(item)
        _log.debug(
            f"Scheduler: scheduled job={job.job_id!r} "
            f"mode={job.mode.value!r} priority={effective_priority}"
        )
        return job

    # ----------------------------------------------------------------
    # Consume
    # ----------------------------------------------------------------

    def next(self) -> Optional[ScheduledWorkflowJob]:
        """Dequeue and return the next highest-priority ScheduledWorkflowJob."""
        item = self._queue.dequeue()
        if item is None:
            return None
        with self._lock:
            for jid, job in list(self._jobs.items()):
                if job.request.request_id == item.request.request_id:
                    del self._jobs[jid]
                    self._item_ids.pop(jid, None)
                    return job
        # Item dequeued but no matching job (already cancelled) — return None
        return None

    # ----------------------------------------------------------------
    # Cancel
    # ----------------------------------------------------------------

    def cancel_job(self, job_id: str) -> bool:
        with self._lock:
            job     = self._jobs.pop(job_id, None)
            item_id = self._item_ids.pop(job_id, None)
        if job is None:
            return False
        if item_id:
            self._queue.cancel(item_id)
        return True

    # ----------------------------------------------------------------
    # Introspection
    # ----------------------------------------------------------------

    def queue_size(self) -> int:
        return self._queue.size()

    def job_count(self) -> int:
        with self._lock:
            return len(self._jobs)

    def is_empty(self) -> bool:
        return self._queue.is_empty()

    def list_jobs(self) -> List[ScheduledWorkflowJob]:
        with self._lock:
            return list(self._jobs.values())

    def queue(self) -> WorkflowQueue:
        return self._queue
