"""
iios/intelligence/intelligence_constants.py
============================================
Enumerations and constants for the IIOS Intelligence Orchestration Engine.

The Intelligence Orchestration Engine is the mandatory coordination layer
for all AI capabilities within IIOS.  No AI engine communicates directly
with another AI engine — every intelligence workflow passes through here.

Error-code prefix: INT-
"""

from __future__ import annotations

from enum import Enum
from typing import Final

__all__ = [
    # Enumerations
    "EngineType",
    "EngineStatus",
    "WorkflowType",
    "StepType",
    "StepStatus",
    "SessionStatus",
    "ExecutionStatus",
    "Priority",
    "PolicyType",
    "EventType",
    "CheckpointStatus",
    "RecoveryMode",
    "ScheduleType",
    "OrchestratorStatus",
    # Limits
    "MAX_CONCURRENT_SESSIONS",
    "MAX_CONCURRENT_WORKFLOWS",
    "MAX_WORKFLOW_STEPS",
    "MAX_NESTING_DEPTH",
    "MAX_RETRY_ATTEMPTS",
    "MAX_CHECKPOINT_AGE_SECONDS",
    "SESSION_TTL_SECONDS",
    "WORKFLOW_TIMEOUT_MS",
    "STEP_TIMEOUT_MS",
    "DEFAULT_THREAD_POOL_SIZE",
    "MAX_SCHEDULED_WORKFLOWS",
    "EVENT_QUEUE_MAX_SIZE",
    # String constants
    "INTELLIGENCE_ENGINE_VERSION",
    "SYSTEM_ACTOR",
    "WILDCARD_ENGINE",
    # Well-known workflow IDs
    "WF_FULL_ANALYSIS",
    "WF_RISK_CHECK",
    "WF_STRATEGY_CYCLE",
    "WF_LEARNING_CYCLE",
]


# ── Engine types (registration keys for all current & future AI engines) ─────

class EngineType(str, Enum):
    """Registered AI engine types within IIOS."""
    REASONING   = "reasoning_engine"
    DEBATE      = "debate_engine"
    HYPOTHESIS  = "hypothesis_engine"
    FORECAST    = "forecast_engine"
    DECISION    = "decision_engine"
    STRATEGY    = "strategy_engine"
    RISK        = "risk_engine"
    PORTFOLIO   = "portfolio_engine"
    LEARNING    = "learning_engine"
    EXECUTION   = "execution_engine"
    AGENT       = "agent_engine"
    PLUGIN      = "plugin_engine"
    ONTOLOGY    = "ontology_engine"
    OBSERVATION = "observation_engine"
    KNOWLEDGE   = "knowledge_engine"


# ── Engine lifecycle ──────────────────────────────────────────────────────────

class EngineStatus(str, Enum):
    REGISTERED   = "registered"
    INITIALIZING = "initializing"
    READY        = "ready"
    BUSY         = "busy"
    DEGRADED     = "degraded"
    ERROR        = "error"
    DISABLED     = "disabled"
    UNREGISTERED = "unregistered"


# ── Workflow types ────────────────────────────────────────────────────────────

class WorkflowType(str, Enum):
    SEQUENTIAL   = "sequential"    # Steps run one after another
    PARALLEL     = "parallel"      # Steps run concurrently
    CONDITIONAL  = "conditional"   # Branch based on condition
    EVENT_DRIVEN = "event_driven"  # Steps triggered by events
    DYNAMIC      = "dynamic"       # Steps added at runtime
    NESTED       = "nested"        # Sub-workflows
    LONG_RUNNING = "long_running"  # Checkpointed, resumable


# ── Step types ────────────────────────────────────────────────────────────────

class StepType(str, Enum):
    ENGINE_CALL  = "engine_call"   # Call a registered AI engine
    COMPUTATION  = "computation"   # Plain Python callable
    CONDITION    = "condition"     # Boolean gate
    FORK         = "fork"          # Split into parallel branches
    JOIN         = "join"          # Merge parallel branches
    WAIT         = "wait"          # Wait for external event
    SUB_WORKFLOW = "sub_workflow"  # Nested workflow
    CHECKPOINT   = "checkpoint"    # Explicit checkpoint marker
    NOTIFICATION = "notification"  # Emit event/notification


# ── Step / execution status ───────────────────────────────────────────────────

class StepStatus(str, Enum):
    PENDING   = "pending"
    RUNNING   = "running"
    COMPLETED = "completed"
    FAILED    = "failed"
    SKIPPED   = "skipped"
    CANCELLED = "cancelled"
    TIMEOUT   = "timeout"
    RETRYING  = "retrying"
    WAITING   = "waiting"


class ExecutionStatus(str, Enum):
    PENDING   = "pending"
    RUNNING   = "running"
    COMPLETED = "completed"
    FAILED    = "failed"
    CANCELLED = "cancelled"
    TIMEOUT   = "timeout"
    PAUSED    = "paused"
    RECOVERING = "recovering"


# ── Session status ────────────────────────────────────────────────────────────

class SessionStatus(str, Enum):
    PENDING    = "pending"
    ACTIVE     = "active"
    PAUSED     = "paused"
    COMPLETED  = "completed"
    FAILED     = "failed"
    EXPIRED    = "expired"
    CANCELLED  = "cancelled"
    RECOVERING = "recovering"


# ── Priority ──────────────────────────────────────────────────────────────────

class Priority(int, Enum):
    LOW      = 10
    NORMAL   = 50
    HIGH     = 75
    CRITICAL = 100


# ── Policy types ──────────────────────────────────────────────────────────────

class PolicyType(str, Enum):
    RETRY        = "retry"
    TIMEOUT      = "timeout"
    FALLBACK     = "fallback"
    PRIORITY     = "priority"
    DEPENDENCY   = "dependency"
    RESOURCE     = "resource"
    LOAD_BALANCE = "load_balance"
    CANCELLATION = "cancellation"


# ── Events ────────────────────────────────────────────────────────────────────

class EventType(str, Enum):
    SESSION_STARTED     = "session.started"
    SESSION_COMPLETED   = "session.completed"
    SESSION_FAILED      = "session.failed"
    SESSION_EXPIRED     = "session.expired"
    WORKFLOW_STARTED    = "workflow.started"
    WORKFLOW_COMPLETED  = "workflow.completed"
    WORKFLOW_FAILED     = "workflow.failed"
    WORKFLOW_PAUSED     = "workflow.paused"
    WORKFLOW_RESUMED    = "workflow.resumed"
    STEP_STARTED        = "step.started"
    STEP_COMPLETED      = "step.completed"
    STEP_FAILED         = "step.failed"
    ENGINE_REGISTERED   = "engine.registered"
    ENGINE_UNREGISTERED = "engine.unregistered"
    ENGINE_ERROR        = "engine.error"
    ORCHESTRATOR_READY  = "orchestrator.ready"
    ORCHESTRATOR_SHUTDOWN = "orchestrator.shutdown"
    CHECKPOINT_SAVED    = "checkpoint.saved"
    CHECKPOINT_RESTORED = "checkpoint.restored"


# ── Checkpoint status ─────────────────────────────────────────────────────────

class CheckpointStatus(str, Enum):
    NONE      = "none"
    SAVING    = "saving"
    SAVED     = "saved"
    RESTORING = "restoring"
    RESTORED  = "restored"
    FAILED    = "failed"
    EXPIRED   = "expired"


# ── Recovery mode ─────────────────────────────────────────────────────────────

class RecoveryMode(str, Enum):
    RESTART  = "restart"    # Restart from beginning
    RESUME   = "resume"     # Resume from last checkpoint
    SKIP     = "skip"       # Skip failed step and continue
    ABORT    = "abort"      # Abort on failure


# ── Schedule types ────────────────────────────────────────────────────────────

class ScheduleType(str, Enum):
    ONCE      = "once"       # Run once at a future time
    INTERVAL  = "interval"   # Repeat every N seconds
    CRON      = "cron"       # Cron-like schedule
    ON_EVENT  = "on_event"   # Trigger on event
    ON_DEMAND = "on_demand"  # Manual trigger only


# ── Orchestrator lifecycle ────────────────────────────────────────────────────

class OrchestratorStatus(str, Enum):
    UNINITIALIZED = "uninitialized"
    INITIALIZING  = "initializing"
    READY         = "ready"
    DEGRADED      = "degraded"
    SHUTTING_DOWN = "shutting_down"
    STOPPED       = "stopped"


# ── Limits ────────────────────────────────────────────────────────────────────

MAX_CONCURRENT_SESSIONS:   Final[int]   = 256
MAX_CONCURRENT_WORKFLOWS:  Final[int]   = 512
MAX_WORKFLOW_STEPS:        Final[int]   = 1_024
MAX_NESTING_DEPTH:         Final[int]   = 16
MAX_RETRY_ATTEMPTS:        Final[int]   = 5
MAX_CHECKPOINT_AGE_SECONDS: Final[int]  = 86_400   # 24 h
SESSION_TTL_SECONDS:       Final[int]   = 7_200    # 2 h
WORKFLOW_TIMEOUT_MS:       Final[float] = 300_000.0  # 5 min
STEP_TIMEOUT_MS:           Final[float] = 60_000.0   # 1 min
DEFAULT_THREAD_POOL_SIZE:  Final[int]   = 8
MAX_SCHEDULED_WORKFLOWS:   Final[int]   = 256
EVENT_QUEUE_MAX_SIZE:      Final[int]   = 10_000


# ── Metadata ──────────────────────────────────────────────────────────────────

INTELLIGENCE_ENGINE_VERSION: Final[str] = "1.0.0"
SYSTEM_ACTOR:                Final[str] = "iios:intelligence:system"
WILDCARD_ENGINE:             Final[str] = "*"


# ── Well-known built-in workflow IDs ─────────────────────────────────────────

WF_FULL_ANALYSIS:  Final[str] = "builtin.full_analysis"
WF_RISK_CHECK:     Final[str] = "builtin.risk_check"
WF_STRATEGY_CYCLE: Final[str] = "builtin.strategy_cycle"
WF_LEARNING_CYCLE: Final[str] = "builtin.learning_cycle"
