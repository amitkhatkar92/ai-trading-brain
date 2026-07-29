"""
agent_metrics.py -- iios.ai.agent_framework.core
=================================================
:class:`MetricRecord`  — single named measurement.
:class:`AgentMetrics`  — immutable aggregate metrics for one agent.

All state transitions return a *new* instance.

A5 AI Agent Framework — Phase 3, Module 5
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import FrozenSet, Optional


@dataclass(frozen=True)
class MetricRecord:
    """A single named measurement attached to an agent."""

    metric_id:   str
    agent_id:    str
    name:        str
    value:       float
    unit:        str
    recorded_at: float

    @classmethod
    def create(
        cls,
        agent_id: str,
        name:     str,
        value:    float,
        unit:     str = "count",
    ) -> "MetricRecord":
        return cls(
            metric_id   = str(uuid.uuid4()),
            agent_id    = agent_id,
            name        = name,
            value       = value,
            unit        = unit,
            recorded_at = time.time(),
        )


@dataclass(frozen=True)
class AgentMetrics:
    """
    Immutable aggregate metrics for one agent.

    Use :meth:`empty` to initialise, then :meth:`with_task_assigned`,
    :meth:`with_task_completed`, :meth:`with_task_failed` to derive
    updated instances as tasks progress.
    """

    agent_id:           str
    tasks_assigned:     int
    tasks_completed:    int
    tasks_failed:       int
    total_execution_ms: float
    avg_execution_ms:   float
    last_task_at:       Optional[float]
    custom_records:     FrozenSet[MetricRecord]

    @classmethod
    def empty(cls, agent_id: str) -> "AgentMetrics":
        """Return zeroed metrics for a newly created agent."""
        return cls(
            agent_id           = agent_id,
            tasks_assigned     = 0,
            tasks_completed    = 0,
            tasks_failed       = 0,
            total_execution_ms = 0.0,
            avg_execution_ms   = 0.0,
            last_task_at       = None,
            custom_records     = frozenset(),
        )

    # ── State transitions ─────────────────────────────────────────────────────

    def with_task_assigned(self) -> "AgentMetrics":
        """Return metrics incremented by one task assignment."""
        return AgentMetrics(
            agent_id           = self.agent_id,
            tasks_assigned     = self.tasks_assigned + 1,
            tasks_completed    = self.tasks_completed,
            tasks_failed       = self.tasks_failed,
            total_execution_ms = self.total_execution_ms,
            avg_execution_ms   = self.avg_execution_ms,
            last_task_at       = self.last_task_at,
            custom_records     = self.custom_records,
        )

    def with_task_completed(self, execution_ms: float) -> "AgentMetrics":
        """Return metrics updated after a successful task completion."""
        new_completed = self.tasks_completed + 1
        new_total     = self.total_execution_ms + execution_ms
        return AgentMetrics(
            agent_id           = self.agent_id,
            tasks_assigned     = self.tasks_assigned,
            tasks_completed    = new_completed,
            tasks_failed       = self.tasks_failed,
            total_execution_ms = new_total,
            avg_execution_ms   = new_total / new_completed,
            last_task_at       = time.time(),
            custom_records     = self.custom_records,
        )

    def with_task_failed(self) -> "AgentMetrics":
        """Return metrics updated after a failed task."""
        return AgentMetrics(
            agent_id           = self.agent_id,
            tasks_assigned     = self.tasks_assigned,
            tasks_completed    = self.tasks_completed,
            tasks_failed       = self.tasks_failed + 1,
            total_execution_ms = self.total_execution_ms,
            avg_execution_ms   = self.avg_execution_ms,
            last_task_at       = self.last_task_at,
            custom_records     = self.custom_records,
        )

    def with_custom_record(self, record: MetricRecord) -> "AgentMetrics":
        """Return metrics with a custom :class:`MetricRecord` appended."""
        return AgentMetrics(
            agent_id           = self.agent_id,
            tasks_assigned     = self.tasks_assigned,
            tasks_completed    = self.tasks_completed,
            tasks_failed       = self.tasks_failed,
            total_execution_ms = self.total_execution_ms,
            avg_execution_ms   = self.avg_execution_ms,
            last_task_at       = self.last_task_at,
            custom_records     = self.custom_records | {record},
        )

    # ── Derived ──────────────────────────────────────────────────────────────

    @property
    def success_rate(self) -> float:
        """0.0 – 1.0.  Returns 0.0 when no tasks have completed or failed."""
        total = self.tasks_completed + self.tasks_failed
        return self.tasks_completed / total if total > 0 else 0.0
