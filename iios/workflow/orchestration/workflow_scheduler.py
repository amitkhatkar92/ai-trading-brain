"""
workflow_scheduler.py — iios.workflow.orchestration
----------------------------------------------------
WorkflowScheduler — schedules workflow executions at a specific time
or on a recurring interval using threading.Timer.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 4
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import PREFIX_JOB
from .exceptions import WorkflowSchedulerError
from .workflow_definition import WorkflowExecutionRequest

_log = get_logger(__name__)


@dataclass
class ScheduledJob:
    """Mutable state for a scheduled workflow job."""
    job_id:            str
    definition_id:     str
    context_data:      Dict[str, Any]
    interval_seconds:  float           # 0 = run once
    next_run_at:       float           # monotonic time
    cancelled:         bool
    run_count:         int
    timer:             Optional[threading.Timer]
    created_at:        str


class WorkflowScheduler:
    """
    Timer-based workflow scheduler.

    Supports:
    - One-shot execution at a specific delay
    - Recurring execution at a fixed interval

    Thread-safe.
    """

    def __init__(
        self,
        executor_fn: Optional[Callable[[WorkflowExecutionRequest], Any]] = None,
    ) -> None:
        self._executor_fn = executor_fn
        self._jobs:  Dict[str, ScheduledJob] = {}
        self._lock   = threading.Lock()
        self._running = False

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start(self, executor_fn: Optional[Callable] = None) -> None:
        if executor_fn:
            self._executor_fn = executor_fn
        with self._lock:
            self._running = True
        _log.info("Scheduler: started")

    def stop(self) -> None:
        with self._lock:
            self._running = False
            jobs = list(self._jobs.values())

        for job in jobs:
            self._cancel_timer(job)
        _log.info("Scheduler: stopped")

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self._running

    # ── Scheduling ────────────────────────────────────────────────────────────

    def schedule_once(
        self,
        definition_id:   str,
        delay_seconds:   float,
        *,
        context_data:    Optional[Dict[str, Any]] = None,
        workflow_id:     Optional[str]            = None,
    ) -> str:
        """Schedule a workflow to run once after delay_seconds."""
        return self._schedule(
            definition_id  = definition_id,
            delay_seconds  = delay_seconds,
            interval_seconds = 0.0,
            context_data   = context_data or {},
            workflow_id    = workflow_id,
        )

    def schedule_recurring(
        self,
        definition_id:    str,
        interval_seconds: float,
        *,
        initial_delay:    float                   = 0.0,
        context_data:     Optional[Dict[str, Any]] = None,
        workflow_id:      Optional[str]           = None,
    ) -> str:
        """Schedule a workflow to run at a fixed interval."""
        if interval_seconds <= 0:
            raise WorkflowSchedulerError(
                f"interval_seconds must be > 0, got {interval_seconds}"
            )
        return self._schedule(
            definition_id   = definition_id,
            delay_seconds   = initial_delay,
            interval_seconds = interval_seconds,
            context_data    = context_data or {},
            workflow_id     = workflow_id,
        )

    def _schedule(
        self,
        definition_id:   str,
        delay_seconds:   float,
        interval_seconds: float,
        context_data:    Dict[str, Any],
        workflow_id:     Optional[str],
    ) -> str:
        import time
        job_id = f"{PREFIX_JOB}{uuid.uuid4().hex[:8]}"
        job = ScheduledJob(
            job_id           = job_id,
            definition_id    = definition_id,
            context_data     = dict(context_data),
            interval_seconds = interval_seconds,
            next_run_at      = time.monotonic() + delay_seconds,
            cancelled        = False,
            run_count        = 0,
            timer            = None,
            created_at       = datetime.now(tz=timezone.utc).isoformat(),
        )
        with self._lock:
            self._jobs[job_id] = job

        self._arm_timer(job, delay_seconds)
        _log.debug(
            f"Scheduler: job={job_id!r} definition={definition_id!r} "
            f"delay={delay_seconds:.1f}s interval={interval_seconds:.1f}s"
        )
        return job_id

    def _arm_timer(self, job: ScheduledJob, delay: float) -> None:
        import time
        timer = threading.Timer(max(delay, 0.0), self._fire, args=(job.job_id,))
        timer.daemon = True
        timer.start()
        with self._lock:
            if job.job_id in self._jobs:
                self._jobs[job.job_id].timer = timer

    def _fire(self, job_id: str) -> None:
        import time
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None or job.cancelled:
                return

        _log.debug(f"Scheduler: firing job={job_id!r}")
        job.run_count += 1

        if self._executor_fn:
            try:
                wf_id   = f"scheduled-{job_id}-{job.run_count}"
                request = WorkflowExecutionRequest.create(
                    workflow_id   = wf_id,
                    definition_id = job.definition_id,
                    context_data  = job.context_data,
                )
                self._executor_fn(request)
            except Exception as exc:
                _log.error(f"Scheduler: job={job_id!r} execution error: {exc!r}")

        # Reschedule if recurring
        with self._lock:
            still_exists = job_id in self._jobs
            interval     = job.interval_seconds

        if still_exists and interval > 0 and not job.cancelled:
            self._arm_timer(job, interval)

    # ── Cancellation ──────────────────────────────────────────────────────────

    def cancel(self, job_id: str) -> bool:
        with self._lock:
            job = self._jobs.pop(job_id, None)
        if job:
            self._cancel_timer(job)
            return True
        return False

    def _cancel_timer(self, job: ScheduledJob) -> None:
        job.cancelled = True
        if job.timer:
            job.timer.cancel()

    # ── Introspection ─────────────────────────────────────────────────────────

    def job_count(self) -> int:
        with self._lock:
            return len(self._jobs)

    def list_jobs(self) -> List[str]:
        with self._lock:
            return list(self._jobs.keys())
