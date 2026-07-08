"""
iios/intelligence/workflow/workflow_engine.py
============================================
WorkflowEngine — master facade for all workflow operations.

Coordinates:
  - WorkflowRegistry  (named workflow storage)
  - WorkflowExecutor  (run a definition)
  - WorkflowScheduler (scheduled/recurring execution)
  - Event emission    (workflow lifecycle events)

Singleton: get_workflow_engine() / reset_workflow_engine()
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Callable, Optional

from ..intelligence_constants import WorkflowType, ScheduleType
from ..intelligence_exceptions import WorkflowNotFoundError
from .workflow_builder   import WorkflowBuilder, WorkflowDefinition
from .workflow_registry  import WorkflowRegistry,  get_workflow_registry,  reset_workflow_registry
from .workflow_executor  import WorkflowExecutor,  WorkflowRunResult, get_workflow_executor, reset_workflow_executor
from .workflow_scheduler import WorkflowScheduler, ScheduledWorkflow, get_workflow_scheduler, reset_workflow_scheduler

log = logging.getLogger(__name__)

__all__ = [
    "WorkflowEngine",
    "get_workflow_engine",
    "reset_workflow_engine",
]


class WorkflowEngine:
    """
    Single entry point for all workflow operations in IIOS.

    Usage
    -----
    engine = get_workflow_engine()
    engine.initialize()

    # Register
    engine.register(my_definition)

    # Execute named workflow
    result = engine.run("my_wf")

    # Execute inline
    result = engine.run_definition(defn, context={"key": "val"})

    # Build fluently
    wf = engine.builder("my_id").name("...").step("s1", fn).build()

    # Schedule
    sched = engine.schedule_interval(defn, interval_s=60)
    """

    def __init__(
        self,
        registry:  Optional[WorkflowRegistry]  = None,
        executor:  Optional[WorkflowExecutor]  = None,
        scheduler: Optional[WorkflowScheduler] = None,
    ) -> None:
        self._registry  = registry  or get_workflow_registry()
        self._executor  = executor  or get_workflow_executor()
        self._scheduler = scheduler or get_workflow_scheduler()
        self._lock      = threading.Lock()
        self._initialized = False

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def initialize(self) -> "WorkflowEngine":
        with self._lock:
            self._initialized = True
        return self

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    def start_scheduler(self) -> None:
        self._scheduler.start()

    def stop_scheduler(self) -> None:
        self._scheduler.stop()

    # ── Registry ──────────────────────────────────────────────────────────────

    def register(
        self,
        definition: WorkflowDefinition,
        overwrite:  bool = False,
    ) -> None:
        self._registry.register(definition, overwrite=overwrite)

    def unregister(self, workflow_id: str) -> bool:
        return self._registry.unregister(workflow_id)

    def has(self, workflow_id: str) -> bool:
        return self._registry.has(workflow_id)

    def get_definition(self, workflow_id: str) -> WorkflowDefinition:
        return self._registry.get(workflow_id)

    def list_workflows(self) -> list[str]:
        return self._registry.list_ids()

    # ── Execution ─────────────────────────────────────────────────────────────

    def run(
        self,
        workflow_id: str,
        context:     dict[str, Any] | None = None,
        version:     Optional[str]         = None,
    ) -> WorkflowRunResult:
        """Execute a registered workflow by ID."""
        defn = self._registry.get(workflow_id, version)
        return self._executor.execute(defn, context=context)

    def run_definition(
        self,
        definition: WorkflowDefinition,
        context:    dict[str, Any] | None = None,
    ) -> WorkflowRunResult:
        """Execute an unregistered / inline workflow definition."""
        return self._executor.execute(definition, context=context)

    # ── Fluent builder ────────────────────────────────────────────────────────

    def builder(self, workflow_id: Optional[str] = None) -> WorkflowBuilder:
        return WorkflowBuilder(workflow_id)

    # ── Scheduling ────────────────────────────────────────────────────────────

    def schedule_once(
        self,
        definition: WorkflowDefinition,
        delay_s:    float = 0.0,
        context:    dict | None = None,
        on_complete: Optional[Callable] = None,
    ) -> ScheduledWorkflow:
        return self._scheduler.schedule_once(
            definition, delay_s=delay_s, context=context, on_complete=on_complete
        )

    def schedule_interval(
        self,
        definition: WorkflowDefinition,
        interval_s: float,
        delay_s:    float = 0.0,
        context:    dict | None = None,
        max_runs:   Optional[int] = None,
    ) -> ScheduledWorkflow:
        return self._scheduler.schedule_interval(
            definition, interval_s=interval_s, delay_s=delay_s,
            context=context, max_runs=max_runs,
        )

    def trigger(self, schedule_id: str) -> WorkflowRunResult:
        return self._scheduler.trigger(schedule_id)

    def cancel_schedule(self, schedule_id: str) -> bool:
        return self._scheduler.cancel(schedule_id)

    # ── Stats / health ────────────────────────────────────────────────────────

    def stats(self) -> dict:
        return {
            "registry":  self._registry.stats(),
            "scheduler": self._scheduler.stats(),
            "initialized": self._initialized,
        }

    def health(self) -> dict:
        return {
            "status":      "healthy" if self._initialized else "not_initialized",
            "initialized": self._initialized,
            "scheduler_running": self._scheduler.is_running,
        }


# ── Singleton ─────────────────────────────────────────────────────────────────

_we_lock = threading.Lock()
_we_inst: Optional[WorkflowEngine] = None


def get_workflow_engine() -> WorkflowEngine:
    global _we_inst
    if _we_inst is None:
        with _we_lock:
            if _we_inst is None:
                _we_inst = WorkflowEngine()
    return _we_inst


def reset_workflow_engine() -> None:
    global _we_inst
    with _we_lock:
        if _we_inst is not None:
            try:
                _we_inst.stop_scheduler()
            except Exception:
                pass
        _we_inst = None
