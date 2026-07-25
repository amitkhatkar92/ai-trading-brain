"""
constants.py — iios.workflow.orchestration
-------------------------------------------
All enumerations, precedence tables, and string constants
for the Workflow Orchestration Framework.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 4
"""
from __future__ import annotations

from enum import Enum

# ── Versioning ────────────────────────────────────────────────────────────────
VERSION       = "1.0.0"
BUILD_VERSION = "c16-m4"

# ── Workflow Types ────────────────────────────────────────────────────────────
class WorkflowType(str, Enum):
    SEQUENTIAL    = "sequential"
    PARALLEL      = "parallel"
    CONDITIONAL   = "conditional"
    LOOP          = "loop"
    EVENT_DRIVEN  = "event_driven"
    SCHEDULED     = "scheduled"
    APPROVAL      = "approval"
    COMPENSATION  = "compensation"
    SAGA          = "saga"
    LONG_RUNNING  = "long_running"
    STATE_MACHINE = "state_machine"
    PIPELINE      = "pipeline"

# ── Step Types ────────────────────────────────────────────────────────────────
class StepType(str, Enum):
    TASK         = "task"
    DECISION     = "decision"
    PARALLEL     = "parallel"
    CONDITIONAL  = "conditional"
    DELAY        = "delay"
    WAIT         = "wait"
    EVENT        = "event"
    APPROVAL     = "approval"
    COMPENSATION = "compensation"
    SUB_WORKFLOW = "sub_workflow"

# ── Workflow Status ───────────────────────────────────────────────────────────
class WorkflowStatus(str, Enum):
    PENDING      = "pending"
    INITIALIZING = "initializing"
    RUNNING      = "running"
    PAUSED       = "paused"
    COMPLETED    = "completed"
    FAILED       = "failed"
    CANCELLED    = "cancelled"
    COMPENSATING = "compensating"
    RECOVERING   = "recovering"
    TIMED_OUT    = "timed_out"

# ── Step Status ───────────────────────────────────────────────────────────────
class StepStatus(str, Enum):
    PENDING      = "pending"
    RUNNING      = "running"
    COMPLETED    = "completed"
    FAILED       = "failed"
    SKIPPED      = "skipped"
    RETRYING     = "retrying"
    COMPENSATING = "compensating"
    TIMED_OUT    = "timed_out"

# ── Execution Mode ────────────────────────────────────────────────────────────
class ExecutionMode(str, Enum):
    SYNC      = "sync"
    ASYNC     = "async"
    PARALLEL  = "parallel"
    SCHEDULED = "scheduled"

# ── Orchestration Event Types ─────────────────────────────────────────────────
class OrchestrationEventType(str, Enum):
    WORKFLOW_EXECUTION_STARTED = "workflow_execution_started"
    WORKFLOW_STEP_STARTED      = "workflow_step_started"
    WORKFLOW_STEP_COMPLETED    = "workflow_step_completed"
    WORKFLOW_STEP_FAILED       = "workflow_step_failed"
    RETRY_TRIGGERED            = "retry_triggered"
    COMPENSATION_STARTED       = "compensation_started"
    CHECKPOINT_CREATED         = "checkpoint_created"
    WORKFLOW_RECOVERED         = "workflow_recovered"
    WORKFLOW_COMPLETED         = "workflow_completed"
    WORKFLOW_EXECUTION_FAILED  = "workflow_execution_failed"

# ── Terminal status sets ──────────────────────────────────────────────────────
TERMINAL_WORKFLOW_STATUSES: frozenset = frozenset({
    WorkflowStatus.COMPLETED,
    WorkflowStatus.FAILED,
    WorkflowStatus.CANCELLED,
    WorkflowStatus.TIMED_OUT,
})

TERMINAL_STEP_STATUSES: frozenset = frozenset({
    StepStatus.COMPLETED,
    StepStatus.FAILED,
    StepStatus.SKIPPED,
    StepStatus.TIMED_OUT,
})

# ── ID prefixes ───────────────────────────────────────────────────────────────
PREFIX_DEFINITION = "wdef-"
PREFIX_STEP       = "step-"
PREFIX_RUNTIME    = "wrt-"
PREFIX_REQUEST    = "wreq-"
PREFIX_RESULT     = "wres-"
PREFIX_CHECKPOINT = "wchk-"
PREFIX_EVENT      = "woevt-"
PREFIX_ENGINE     = "woe-"
PREFIX_JOB        = "wjob-"

# ── Defaults ──────────────────────────────────────────────────────────────────
DEFAULT_MAX_RETRIES        = 3
DEFAULT_TIMEOUT_SECONDS    = 300.0    # 5 min per step
DEFAULT_WORKFLOW_TIMEOUT   = 3_600.0  # 1 hour total
DEFAULT_BACKOFF_SECONDS    = 1.0
DEFAULT_BACKOFF_MULTIPLIER = 2.0
DEFAULT_MAX_BACKOFF        = 60.0
DEFAULT_MAX_HISTORY        = 10_000
DEFAULT_MAX_REGISTRY       = 5_000
DEFAULT_QUEUE_CAPACITY     = 1_000
DEFAULT_MAX_PARALLEL       = 32

# ── Actor labels ──────────────────────────────────────────────────────────────
ACTOR_ORCHESTRATION_ENGINE = "WorkflowOrchestrationEngine"
ACTOR_EXECUTOR             = "WorkflowExecutor"
ACTOR_STEP_EXECUTOR        = "WorkflowStepExecutor"
ACTOR_RECOVERY             = "WorkflowRecoveryEngine"
ACTOR_COMPENSATION         = "WorkflowCompensationEngine"
ACTOR_CHECKPOINT           = "WorkflowCheckpointManager"
ACTOR_SCHEDULER            = "WorkflowScheduler"
