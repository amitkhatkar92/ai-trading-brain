"""
orchestration_types.py -- iios.ai.orchestrator.core
=====================================================
Status enums for all orchestration domain objects.

A10 Enterprise AI Orchestrator — Phase 3, Module 10
"""
from __future__ import annotations

from enum import Enum


class ObjectiveStatus(str, Enum):
    """Lifecycle status of an orchestration objective."""
    PENDING   = "pending"
    PLANNING  = "planning"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED    = "failed"
    CANCELLED = "cancelled"

    def is_terminal(self) -> bool:
        return self in (ObjectiveStatus.COMPLETED, ObjectiveStatus.FAILED, ObjectiveStatus.CANCELLED)


class PlanStatus(str, Enum):
    """Lifecycle status of an execution plan."""
    DRAFT     = "draft"
    READY     = "ready"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED    = "failed"
    CANCELLED = "cancelled"

    def is_terminal(self) -> bool:
        return self in (PlanStatus.COMPLETED, PlanStatus.FAILED, PlanStatus.CANCELLED)


class WorkflowStatus(str, Enum):
    """Lifecycle status of a workflow instance."""
    PENDING   = "pending"
    RUNNING   = "running"
    PAUSED    = "paused"
    COMPLETED = "completed"
    FAILED    = "failed"
    CANCELLED = "cancelled"

    def is_terminal(self) -> bool:
        return self in (WorkflowStatus.COMPLETED, WorkflowStatus.FAILED, WorkflowStatus.CANCELLED)

    def is_active(self) -> bool:
        return self in (WorkflowStatus.RUNNING, WorkflowStatus.PAUSED)


class TaskStatus(str, Enum):
    """Lifecycle status of a scheduled task."""
    PENDING   = "pending"
    QUEUED    = "queued"
    RUNNING   = "running"
    COMPLETED = "completed"
    FAILED    = "failed"
    CANCELLED = "cancelled"
    RETRYING  = "retrying"

    def is_terminal(self) -> bool:
        return self in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED)


class StepStatus(str, Enum):
    """Execution status of an individual plan or workflow step."""
    PENDING   = "pending"
    RUNNING   = "running"
    COMPLETED = "completed"
    FAILED    = "failed"
    SKIPPED   = "skipped"

    def is_terminal(self) -> bool:
        return self in (StepStatus.COMPLETED, StepStatus.FAILED, StepStatus.SKIPPED)


class ExecutionMode(str, Enum):
    """Execution mode for plan steps."""
    SEQUENTIAL = "sequential"
    PARALLEL   = "parallel"
    MIXED      = "mixed"
