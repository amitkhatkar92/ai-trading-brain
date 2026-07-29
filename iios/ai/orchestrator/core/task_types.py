"""
task_types.py -- iios.ai.orchestrator.core
==========================================
Frozen dataclasses for scheduled tasks and scheduler configuration.

A10 Enterprise AI Orchestrator — Phase 3, Module 10
"""
from __future__ import annotations

import dataclasses
import time
import uuid
from dataclasses import dataclass
from typing import FrozenSet, Optional, Tuple

from .orchestration_types import TaskStatus


@dataclass(frozen=True)
class ScheduledTask:
    """Immutable scheduled task descriptor."""
    task_id:              str
    name:                 str
    action:               str
    parameters:           FrozenSet[Tuple[str, str]]
    priority:             int             # higher = run first
    scheduled_at:         float           # epoch seconds
    recurring_interval_s: Optional[float] # None = one-shot
    max_retries:          int
    dependencies:         FrozenSet[str]  # task_ids that must complete first
    status:               TaskStatus

    @classmethod
    def create(
        cls,
        name:                 str,
        action:               str,
        priority:             int   = 0,
        scheduled_at:         float = 0.0,
        recurring_interval_s: Optional[float] = None,
        max_retries:          int   = 0,
        dependencies:         FrozenSet[str] = frozenset(),
        **parameters: str,
    ) -> "ScheduledTask":
        return cls(
            task_id              = str(uuid.uuid4()),
            name                 = name,
            action               = action,
            parameters           = frozenset(parameters.items()),
            priority             = priority,
            scheduled_at         = scheduled_at if scheduled_at > 0 else time.time(),
            recurring_interval_s = recurring_interval_s,
            max_retries          = max_retries,
            dependencies         = dependencies,
            status               = TaskStatus.PENDING,
        )

    def get_param(self, key: str, default: str = "") -> str:
        for k, v in self.parameters:
            if k == key:
                return v
        return default

    def with_status(self, status: TaskStatus) -> "ScheduledTask":
        return dataclasses.replace(self, status=status)

    def is_due(self) -> bool:
        return self.status in (TaskStatus.PENDING, TaskStatus.QUEUED) and time.time() >= self.scheduled_at

    def is_ready(self, completed_ids: FrozenSet[str]) -> bool:
        """True when all declared dependencies have completed."""
        return self.dependencies.issubset(completed_ids)


@dataclass(frozen=True)
class SchedulerPolicy:
    """Immutable task scheduler configuration."""
    max_concurrent:    int
    max_queue_size:    int
    default_timeout_s: int
    retry_backoff_s:   float

    @classmethod
    def default(cls) -> "SchedulerPolicy":
        return cls(
            max_concurrent    = 10,
            max_queue_size    = 1000,
            default_timeout_s = 300,
            retry_backoff_s   = 0.0,
        )
