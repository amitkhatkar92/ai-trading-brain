"""
iios/intelligence/workflow/workflow_scheduler.py
=================================================
WorkflowScheduler — schedules workflows for deferred or recurring execution.

Supports:
  ONCE       — run once after a delay
  INTERVAL   — repeat every N seconds
  ON_EVENT   — trigger on event subscription (external trigger)
  ON_DEMAND  — manual trigger only (registered but not auto-run)

The scheduler runs a background daemon thread that checks the schedule
every second and dispatches ready workflows to the executor.

Singleton: get_workflow_scheduler() / reset_workflow_scheduler()
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from ..intelligence_constants import ScheduleType, MAX_SCHEDULED_WORKFLOWS
from ..intelligence_exceptions import (
    WorkflowNotFoundError,
    SchedulerNotRunningError,
    WorkflowAlreadyRegisteredError,
)
from .workflow_builder  import WorkflowDefinition
from .workflow_executor import WorkflowExecutor, WorkflowRunResult, get_workflow_executor

log = logging.getLogger(__name__)

__all__ = [
    "ScheduledWorkflow",
    "WorkflowScheduler",
    "get_workflow_scheduler",
    "reset_workflow_scheduler",
]


@dataclass
class ScheduledWorkflow:
    """Metadata for a scheduled workflow entry."""
    schedule_id:   str
    workflow_id:   str
    definition:    WorkflowDefinition
    schedule_type: ScheduleType
    run_at:        float                    = 0.0   # Next/only run timestamp
    interval_s:    float                    = 0.0   # For INTERVAL type
    context:       dict[str, Any]           = field(default_factory=dict)
    max_runs:      Optional[int]            = None   # None = unlimited
    run_count:     int                      = 0
    enabled:       bool                     = True
    last_run_at:   Optional[float]          = None
    last_result:   Optional[WorkflowRunResult] = None
    on_complete:   Optional[Callable]       = field(default=None, repr=False)
    created_at:    float                    = field(default_factory=time.time)

    @property
    def is_due(self) -> bool:
        if not self.enabled:
            return False
        if self.schedule_type == ScheduleType.ON_DEMAND:
            return False
        if self.max_runs is not None and self.run_count >= self.max_runs:
            return False
        return time.time() >= self.run_at

    def advance(self) -> None:
        """Advance the next run time after a successful dispatch."""
        self.run_count  += 1
        self.last_run_at = time.time()
        if self.schedule_type == ScheduleType.INTERVAL and self.interval_s > 0:
            self.run_at = time.time() + self.interval_s
        elif self.schedule_type == ScheduleType.ONCE:
            self.enabled = False

    def to_dict(self) -> dict:
        return {
            "schedule_id":   self.schedule_id,
            "workflow_id":   self.workflow_id,
            "schedule_type": self.schedule_type.value,
            "run_at":        self.run_at,
            "interval_s":    self.interval_s,
            "run_count":     self.run_count,
            "enabled":       self.enabled,
            "last_run_at":   self.last_run_at,
        }


class WorkflowScheduler:
    """
    Runs scheduled workflows via a background daemon thread.
    """

    def __init__(self, executor: Optional[WorkflowExecutor] = None) -> None:
        self._executor    = executor or get_workflow_executor()
        self._schedules:  dict[str, ScheduledWorkflow] = {}
        self._lock        = threading.RLock()
        self._running     = False
        self._thread:     Optional[threading.Thread] = None
        self._tick_s      = 1.0   # check interval

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start(self) -> None:
        with self._lock:
            if self._running:
                return
            self._running = True
            self._thread  = threading.Thread(
                target=self._loop, daemon=True, name="workflow-scheduler"
            )
            self._thread.start()
            log.info("WorkflowScheduler started")

    def stop(self) -> None:
        with self._lock:
            self._running = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None
        log.info("WorkflowScheduler stopped")

    @property
    def is_running(self) -> bool:
        return self._running

    # ── Scheduling ────────────────────────────────────────────────────────────

    def schedule_once(
        self,
        definition: WorkflowDefinition,
        delay_s:    float             = 0.0,
        context:    dict | None       = None,
        on_complete: Optional[Callable] = None,
    ) -> ScheduledWorkflow:
        return self._add(ScheduledWorkflow(
            schedule_id   = str(uuid.uuid4()),
            workflow_id   = definition.workflow_id,
            definition    = definition,
            schedule_type = ScheduleType.ONCE,
            run_at        = time.time() + delay_s,
            context       = context or {},
            max_runs      = 1,
            on_complete   = on_complete,
        ))

    def schedule_interval(
        self,
        definition: WorkflowDefinition,
        interval_s: float,
        delay_s:    float = 0.0,
        context:    dict | None = None,
        max_runs:   Optional[int] = None,
        on_complete: Optional[Callable] = None,
    ) -> ScheduledWorkflow:
        return self._add(ScheduledWorkflow(
            schedule_id   = str(uuid.uuid4()),
            workflow_id   = definition.workflow_id,
            definition    = definition,
            schedule_type = ScheduleType.INTERVAL,
            run_at        = time.time() + delay_s,
            interval_s    = interval_s,
            context       = context or {},
            max_runs      = max_runs,
            on_complete   = on_complete,
        ))

    def schedule_on_demand(
        self,
        definition: WorkflowDefinition,
        context:    dict | None = None,
    ) -> ScheduledWorkflow:
        return self._add(ScheduledWorkflow(
            schedule_id   = str(uuid.uuid4()),
            workflow_id   = definition.workflow_id,
            definition    = definition,
            schedule_type = ScheduleType.ON_DEMAND,
            context       = context or {},
        ))

    def trigger(self, schedule_id: str) -> Optional[WorkflowRunResult]:
        """Manually trigger an ON_DEMAND or any scheduled workflow immediately."""
        with self._lock:
            sw = self._schedules.get(schedule_id)
            if sw is None:
                raise WorkflowNotFoundError(schedule_id)
        return self._dispatch(sw)

    def cancel(self, schedule_id: str) -> bool:
        with self._lock:
            sw = self._schedules.pop(schedule_id, None)
            return sw is not None

    def enable(self, schedule_id: str) -> None:
        with self._lock:
            sw = self._schedules.get(schedule_id)
            if sw:
                sw.enabled = True

    def disable(self, schedule_id: str) -> None:
        with self._lock:
            sw = self._schedules.get(schedule_id)
            if sw:
                sw.enabled = False

    # ── Query ─────────────────────────────────────────────────────────────────

    def list_schedules(self) -> list[ScheduledWorkflow]:
        with self._lock:
            return list(self._schedules.values())

    def get_schedule(self, schedule_id: str) -> ScheduledWorkflow:
        with self._lock:
            sw = self._schedules.get(schedule_id)
            if sw is None:
                raise WorkflowNotFoundError(schedule_id)
            return sw

    def stats(self) -> dict:
        with self._lock:
            total   = len(self._schedules)
            enabled = sum(1 for s in self._schedules.values() if s.enabled)
            return {
                "total":   total,
                "enabled": enabled,
                "running": self._running,
            }

    # ── Internal ──────────────────────────────────────────────────────────────

    def _add(self, sw: ScheduledWorkflow) -> ScheduledWorkflow:
        with self._lock:
            if len(self._schedules) >= MAX_SCHEDULED_WORKFLOWS:
                raise OverflowError(
                    f"Scheduler capacity ({MAX_SCHEDULED_WORKFLOWS}) exceeded"
                )
            self._schedules[sw.schedule_id] = sw
            return sw

    def _loop(self) -> None:
        while self._running:
            try:
                self._tick()
            except Exception as exc:
                log.error("Scheduler tick error: %s", exc)
            time.sleep(self._tick_s)

    def _tick(self) -> None:
        with self._lock:
            due = [sw for sw in self._schedules.values() if sw.is_due]
        for sw in due:
            try:
                self._dispatch(sw)
            except Exception as exc:
                log.error("Dispatch failed for %r: %s", sw.schedule_id, exc)

    def _dispatch(self, sw: ScheduledWorkflow) -> WorkflowRunResult:
        result = self._executor.execute(sw.definition, context=sw.context)
        with self._lock:
            sw.last_result = result
            sw.advance()
        if sw.on_complete:
            try:
                sw.on_complete(result)
            except Exception as exc:
                log.warning("on_complete callback raised: %s", exc)
        return result


# ── Singleton ─────────────────────────────────────────────────────────────────

_sched_lock = threading.Lock()
_sched_inst: Optional[WorkflowScheduler] = None


def get_workflow_scheduler() -> WorkflowScheduler:
    global _sched_inst
    if _sched_inst is None:
        with _sched_lock:
            if _sched_inst is None:
                _sched_inst = WorkflowScheduler()
    return _sched_inst


def reset_workflow_scheduler() -> None:
    global _sched_inst
    with _sched_lock:
        if _sched_inst is not None:
            try:
                _sched_inst.stop()
            except Exception:
                pass
        _sched_inst = None
