"""
iios/infrastructure/scheduler/job_scheduler.py
===============================================
Main scheduler with background tick loop.

Supports CRON, INTERVAL, and ONCE job types.
"""

from __future__ import annotations

import datetime
import logging
import threading
import time
import uuid
from typing import Any, Callable, Optional

from ..infrastructure_constants import (
    DEFAULT_SCHEDULER_TICK_SECONDS,
    DEFAULT_RETRY_ATTEMPTS,
    DEFAULT_RETRY_BACKOFF_SECONDS,
    JobType,
    JobStatus,
)
from ..infrastructure_exceptions import SchedulerError
from ..infrastructure_models import JobDefinition, JobExecution
from .cron_job import CronExpression
from .interval_job import IntervalSchedule
from .scheduler_registry import SchedulerRegistry

__all__ = ["JobScheduler", "get_scheduler", "reset_scheduler"]

_LOG = logging.getLogger("iios.infrastructure.scheduler")
_sched_lock = threading.Lock()
_scheduler: Optional["JobScheduler"] = None


class _JobState:
    """Runtime state for one scheduled job."""

    def __init__(self, definition: JobDefinition) -> None:
        self.definition = definition
        self.last_run: Optional[datetime.datetime] = None
        self.executions: list[JobExecution] = []
        self._cron: Optional[CronExpression] = None
        self._interval: Optional[IntervalSchedule] = None
        self._fired_once = False

        if definition.job_type == JobType.CRON and definition.schedule:
            self._cron = CronExpression(definition.schedule)
        elif definition.job_type == JobType.INTERVAL and definition.schedule:
            self._interval = IntervalSchedule(seconds=float(definition.schedule))

    def is_due(self, now: datetime.datetime) -> bool:
        if not self.definition.enabled:
            return False
        if self.definition.job_type == JobType.ONCE:
            return not self._fired_once
        if self.definition.job_type == JobType.CRON and self._cron:
            return self._cron.matches(now)
        if self.definition.job_type == JobType.INTERVAL and self._interval:
            return self._interval.is_due(now)
        return False

    def mark_fired(self, now: datetime.datetime) -> None:
        self.last_run = now
        self._fired_once = True
        if self._interval:
            self._interval.mark_fired(now)


class JobScheduler:
    """Background job scheduler.

    Usage::

        scheduler = get_scheduler()
        scheduler.start()

        scheduler.add_cron("morning_report", "0 9 * * 1-5", morning_report_fn)
        scheduler.add_interval("heartbeat", 30, send_heartbeat)
        scheduler.add_once("startup", init_fn)

        scheduler.stop()
    """

    def __init__(self, tick: float = DEFAULT_SCHEDULER_TICK_SECONDS) -> None:
        self._registry = SchedulerRegistry()
        self._states: dict[str, _JobState] = {}
        self._callables: dict[str, Callable] = {}
        self._tick = tick
        self._worker: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._running = False
        self._lock = threading.RLock()
        self._total_runs = 0
        self._total_failures = 0

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        with self._lock:
            if self._running:
                return
            self._stop_event.clear()
            self._worker = threading.Thread(
                target=self._tick_loop,
                daemon=True,
                name="iios.scheduler.worker",
            )
            self._worker.start()
            self._running = True
        _LOG.info("JobScheduler started (tick=%.1fs)", self._tick)

    def stop(self, timeout: float = 5.0) -> None:
        with self._lock:
            if not self._running:
                return
            self._stop_event.set()
            self._running = False
        if self._worker:
            self._worker.join(timeout=timeout)
            self._worker = None
        _LOG.info("JobScheduler stopped")

    @property
    def is_running(self) -> bool:
        return self._running

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def add_cron(
        self,
        name: str,
        expression: str,
        fn: Callable,
        *,
        max_retries: int = DEFAULT_RETRY_ATTEMPTS,
        tags: Optional[list[str]] = None,
        allow_override: bool = False,
    ) -> str:
        job = JobDefinition(
            job_id=str(uuid.uuid4()),
            name=name,
            job_type=JobType.CRON,
            callable_path=f"{fn.__module__}.{fn.__qualname__}",
            schedule=expression,
            max_retries=max_retries,
            tags=tags or [],
        )
        return self._register(job, fn, allow_override)

    def add_interval(
        self,
        name: str,
        seconds: float,
        fn: Callable,
        *,
        max_retries: int = DEFAULT_RETRY_ATTEMPTS,
        tags: Optional[list[str]] = None,
        allow_override: bool = False,
    ) -> str:
        job = JobDefinition(
            job_id=str(uuid.uuid4()),
            name=name,
            job_type=JobType.INTERVAL,
            callable_path=f"{fn.__module__}.{fn.__qualname__}",
            schedule=str(seconds),
            max_retries=max_retries,
            tags=tags or [],
        )
        return self._register(job, fn, allow_override)

    def add_once(
        self,
        name: str,
        fn: Callable,
        *,
        tags: Optional[list[str]] = None,
    ) -> str:
        job = JobDefinition(
            job_id=str(uuid.uuid4()),
            name=name,
            job_type=JobType.ONCE,
            callable_path=f"{fn.__module__}.{fn.__qualname__}",
            schedule="",
            tags=tags or [],
        )
        return self._register(job, fn, False)

    def remove(self, job_id: str) -> bool:
        with self._lock:
            ok = self._registry.remove(job_id)
            self._states.pop(job_id, None)
            self._callables.pop(job_id, None)
        return ok

    def disable(self, job_id: str) -> None:
        self._registry.disable(job_id)

    def enable(self, job_id: str) -> None:
        self._registry.enable(job_id)

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def jobs(self) -> list[JobDefinition]:
        return self._registry.all()

    def executions(self, job_id: str) -> list[JobExecution]:
        with self._lock:
            state = self._states.get(job_id)
        return state.executions if state else []

    def stats(self) -> dict[str, Any]:
        return {
            "running": self._running,
            "job_count": self._registry.count(),
            "total_runs": self._total_runs,
            "total_failures": self._total_failures,
        }

    def reset(self) -> None:
        self.stop()
        with self._lock:
            self._registry.clear()
            self._states.clear()
            self._callables.clear()
            self._total_runs = 0
            self._total_failures = 0

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _register(self, job: JobDefinition, fn: Callable, allow_override: bool) -> str:
        with self._lock:
            self._registry.add(job, allow_override=allow_override)
            self._states[job.job_id] = _JobState(job)
            self._callables[job.job_id] = fn
        return job.job_id

    def _tick_loop(self) -> None:
        while not self._stop_event.is_set():
            now = datetime.datetime.now()
            with self._lock:
                due = [
                    jid for jid, state in self._states.items()
                    if state.is_due(now)
                ]

            for jid in due:
                self._run_job(jid, now)

            # Sleep until next tick; wake early if stopped
            self._stop_event.wait(self._tick)

    def _run_job(self, job_id: str, now: datetime.datetime) -> None:
        with self._lock:
            state = self._states.get(job_id)
            fn = self._callables.get(job_id)
            if state is None or fn is None:
                return
            state.mark_fired(now)

        execution = JobExecution(job_id=job_id)
        execution.start()
        max_retries = state.definition.max_retries

        for attempt in range(max_retries + 1):
            try:
                result = fn()
                execution.succeed(result)
                with self._lock:
                    self._total_runs += 1
                    state.executions.append(execution)
                return
            except Exception as exc:
                if attempt < max_retries:
                    delay = DEFAULT_RETRY_BACKOFF_SECONDS * (2 ** attempt)
                    _LOG.warning("Job '%s' attempt %d failed: %s — retrying in %.1fs",
                                 state.definition.name, attempt + 1, exc, delay)
                    time.sleep(delay)
                else:
                    execution.fail(str(exc))
                    with self._lock:
                        self._total_failures += 1
                        state.executions.append(execution)
                    _LOG.error("Job '%s' permanently failed: %s",
                               state.definition.name, exc)


def get_scheduler() -> JobScheduler:
    global _scheduler
    with _sched_lock:
        if _scheduler is None:
            _scheduler = JobScheduler()
        return _scheduler


def reset_scheduler() -> None:
    global _scheduler
    with _sched_lock:
        if _scheduler is not None:
            _scheduler.reset()
        _scheduler = None
