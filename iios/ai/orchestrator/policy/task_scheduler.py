"""
task_scheduler.py -- iios.ai.orchestrator.policy
==================================================
:class:`TaskScheduler` — priority-based, dependency-aware task scheduling.

A10 Enterprise AI Orchestrator — Phase 3, Module 10
"""
from __future__ import annotations

import heapq
import threading
import time
from typing import Any, Callable, Dict, FrozenSet, List, Optional, Tuple

from ..core.task_types import ScheduledTask, SchedulerPolicy, TaskStatus
from ..exceptions.orchestrator_exceptions import (
    AITaskExecutionError,
    AITaskNotFoundError,
    AITaskQueueFullError,
)


class TaskScheduler:
    """
    Priority-based task scheduler with dependency resolution.

    Tasks are ordered by ``(-priority, scheduled_at)``.
    Tasks with unsatisfied dependencies are deferred until dependencies complete.
    Recurring tasks are re-queued automatically after each execution.
    """

    def __init__(self, policy: Optional[SchedulerPolicy] = None) -> None:
        self._policy:    SchedulerPolicy                       = policy or SchedulerPolicy.default()
        self._lock:      threading.Lock                        = threading.Lock()
        self._tasks:     Dict[str, ScheduledTask]              = {}
        self._heap:      List[Tuple[int, float, str]]          = []
        self._completed: FrozenSet[str]                        = frozenset()
        self._handlers:  Dict[str, Callable[[Dict], Any]]     = {}

    # ── handler registration ──────────────────────────────────────────────────

    def register_handler(self, action: str, handler_fn: Callable[[Dict], Any]) -> None:
        with self._lock:
            self._handlers[action] = handler_fn

    # ── task management ───────────────────────────────────────────────────────

    def schedule(self, task: ScheduledTask) -> str:
        """Enqueue *task*.  Returns the task_id."""
        with self._lock:
            if len(self._tasks) >= self._policy.max_queue_size:
                raise AITaskQueueFullError(
                    f"Task queue is full (max {self._policy.max_queue_size})"
                )
            queued = task.with_status(TaskStatus.QUEUED)
            self._tasks[queued.task_id] = queued
            heapq.heappush(self._heap, (-queued.priority, queued.scheduled_at, queued.task_id))
        return task.task_id

    def cancel_task(self, task_id: str) -> None:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                raise AITaskNotFoundError(f"Task '{task_id}' not found")
            if task.status.is_terminal():
                raise AITaskExecutionError(
                    f"Cannot cancel task in terminal state '{task.status}'"
                )
            self._tasks[task_id] = task.with_status(TaskStatus.CANCELLED)

    def get_task(self, task_id: str) -> ScheduledTask:
        with self._lock:
            task = self._tasks.get(task_id)
        if task is None:
            raise AITaskNotFoundError(f"Task '{task_id}' not found")
        return task

    # ── execution ─────────────────────────────────────────────────────────────

    def run_pending(self) -> List[str]:
        """
        Execute all due, dependency-satisfied tasks in priority order.
        Returns the list of executed task_ids.
        """
        executed: List[str] = []
        now = time.time()

        with self._lock:
            due: List[Tuple[int, float, str]] = []
            deferred: List[Tuple[int, float, str]] = []
            while self._heap:
                entry = heapq.heappop(self._heap)
                neg_pri, sched_at, task_id = entry
                task = self._tasks.get(task_id)
                if task is None or task.status.is_terminal():
                    continue
                if sched_at <= now and task.is_ready(self._completed):
                    due.append(entry)
                else:
                    deferred.append(entry)
            for r in deferred:
                heapq.heappush(self._heap, r)
            handlers  = dict(self._handlers)
            completed = set(self._completed)

        for neg_pri, sched_at, task_id in due:
            with self._lock:
                task = self._tasks.get(task_id)
                if task is None or task.status.is_terminal():
                    continue
                self._tasks[task_id] = task.with_status(TaskStatus.RUNNING)

            handler = handlers.get(task.action)
            if handler is None:
                with self._lock:
                    self._tasks[task_id] = self._tasks[task_id].with_status(TaskStatus.FAILED)
                executed.append(task_id)
                continue

            success   = False
            last_exc: Optional[Exception] = None
            params    = dict(task.parameters)

            for attempt in range(task.max_retries + 1):
                try:
                    handler(params)
                    success = True
                    break
                except Exception as exc:
                    last_exc = exc
                    if attempt < task.max_retries:
                        with self._lock:
                            self._tasks[task_id] = self._tasks[task_id].with_status(
                                TaskStatus.RETRYING
                            )

            with self._lock:
                if success:
                    self._tasks[task_id] = self._tasks[task_id].with_status(TaskStatus.COMPLETED)
                    completed.add(task_id)
                    self._completed = frozenset(completed)

                    if task.recurring_interval_s is not None:
                        import dataclasses as _dc
                        new_task = _dc.replace(
                            task,
                            scheduled_at = time.time() + task.recurring_interval_s,
                            status       = TaskStatus.QUEUED,
                        )
                        self._tasks[task_id] = new_task
                        heapq.heappush(
                            self._heap,
                            (-new_task.priority, new_task.scheduled_at, task_id),
                        )
                else:
                    self._tasks[task_id] = self._tasks[task_id].with_status(TaskStatus.FAILED)

            executed.append(task_id)

        return executed

    # ── stats ─────────────────────────────────────────────────────────────────

    def task_count(self) -> int:
        with self._lock:
            return len(self._tasks)

    def queued_count(self) -> int:
        with self._lock:
            return sum(1 for t in self._tasks.values() if t.status == TaskStatus.QUEUED)

    def completed_count(self) -> int:
        with self._lock:
            return sum(1 for t in self._tasks.values() if t.status == TaskStatus.COMPLETED)

    def failed_count(self) -> int:
        with self._lock:
            return sum(1 for t in self._tasks.values() if t.status == TaskStatus.FAILED)
