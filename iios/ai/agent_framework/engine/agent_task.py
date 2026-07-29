"""
agent_task.py -- iios.ai.agent_framework.engine
================================================
:class:`TaskStatus`   — task life-cycle states.
:class:`TaskPriority` — task scheduling priority.
:class:`AgentTask`    — immutable task request.
:class:`AgentResult`  — immutable task execution result.

A5 AI Agent Framework — Phase 3, Module 5
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Any, FrozenSet, Optional, Tuple


class TaskStatus(str, Enum):
    """Life-cycle states of a task."""

    PENDING   = "pending"
    RUNNING   = "running"
    COMPLETED = "completed"
    FAILED    = "failed"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    """Scheduling priority for task dispatch."""

    LOW      = "low"
    NORMAL   = "normal"
    HIGH     = "high"
    CRITICAL = "critical"


@dataclass(frozen=True)
class AgentTask:
    """
    Immutable task request dispatched to an agent.

    ``task_type`` is a free-form string that the receiving agent uses to
    route the request to the right handler (e.g. ``"analyse_market"``).
    ``payload`` carries the task-specific input data.
    """

    task_id:    str
    agent_id:   str
    task_type:  str
    payload:    Any
    priority:   TaskPriority
    created_at: float
    timeout_ms: Optional[float]
    metadata:   FrozenSet[Tuple[str, Any]]

    @classmethod
    def create(
        cls,
        agent_id:   str,
        task_type:  str,
        payload:    Any                   = None,
        priority:   TaskPriority          = TaskPriority.NORMAL,
        timeout_ms: Optional[float]       = None,
        **meta: Any,
    ) -> "AgentTask":
        return cls(
            task_id    = str(uuid.uuid4()),
            agent_id   = agent_id,
            task_type  = task_type,
            payload    = payload,
            priority   = priority,
            created_at = time.time(),
            timeout_ms = timeout_ms,
            metadata   = frozenset(meta.items()),
        )

    def get_meta(self, key: str, default: Any = None) -> Any:
        for k, v in self.metadata:
            if k == key:
                return v
        return default


@dataclass(frozen=True)
class AgentResult:
    """
    Immutable task execution result.

    Both successful and failed executions produce an :class:`AgentResult`.
    Inspect ``status`` first; ``error`` is populated only on failures.
    ``execution_ms`` is the wall-clock time inside the agent.
    """

    task_id:      str
    agent_id:     str
    status:       TaskStatus
    output:       Any
    error:        Optional[str]
    started_at:   float
    completed_at: float
    execution_ms: float

    @classmethod
    def success(
        cls,
        task:       AgentTask,
        output:     Any,
        started_at: float,
    ) -> "AgentResult":
        """Build a successful result."""
        completed_at = time.time()
        return cls(
            task_id      = task.task_id,
            agent_id     = task.agent_id,
            status       = TaskStatus.COMPLETED,
            output       = output,
            error        = None,
            started_at   = started_at,
            completed_at = completed_at,
            execution_ms = (completed_at - started_at) * 1_000,
        )

    @classmethod
    def failure(
        cls,
        task:       AgentTask,
        error:      str,
        started_at: float,
    ) -> "AgentResult":
        """Build a failed result."""
        completed_at = time.time()
        return cls(
            task_id      = task.task_id,
            agent_id     = task.agent_id,
            status       = TaskStatus.FAILED,
            output       = None,
            error        = error,
            started_at   = started_at,
            completed_at = completed_at,
            execution_ms = (completed_at - started_at) * 1_000,
        )

    def is_success(self) -> bool:
        return self.status == TaskStatus.COMPLETED

    def is_failure(self) -> bool:
        return self.status == TaskStatus.FAILED
