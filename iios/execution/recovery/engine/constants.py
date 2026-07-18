"""
iios/execution/recovery/engine/constants.py
==========================================
Constants, enumerations, and runtime limits for the Execution Recovery Engine.

C7 Execution Recovery & Resilience — Phase 1, Module 2
"""
from __future__ import annotations

from enum import Enum
from typing import FrozenSet, Tuple

# ── System identifiers ────────────────────────────────────────────────────────

SYSTEM_ID      = "iios:execution:recovery:engine"
ENGINE_ID      = "iios:execution:recovery:engine:main"
MANAGER_ID     = "iios:execution:recovery:engine:manager"
SCHEDULER_ID   = "iios:execution:recovery:engine:scheduler"
DISPATCHER_ID  = "iios:execution:recovery:engine:dispatcher"
PIPELINE_ID    = "iios:execution:recovery:engine:pipeline"
SESSION_MGR_ID = "iios:execution:recovery:engine:session_manager"
REGISTRY_ID    = "iios:execution:recovery:engine:registry"
FACTORY_ID     = "iios:execution:recovery:engine:factory"

VERSION        = "1.0.0"
SCHEMA_VERSION = "1.0"

# ── Runtime limits ────────────────────────────────────────────────────────────

DEFAULT_MAX_REQUESTS          = 10_000
DEFAULT_MAX_HISTORY           = 2_000
DEFAULT_MAX_CONCURRENT        = 20
DEFAULT_QUEUE_SIZE            = 500
DEFAULT_SCHEDULER_INTERVAL_MS = 1_000
DEFAULT_DISPATCH_TIMEOUT_MS   = 30_000
DEFAULT_VERIFY_TIMEOUT_MS     = 60_000
DEFAULT_SESSION_TIMEOUT_MS    = 300_000   # 5 minutes

# ── Actor identifiers ─────────────────────────────────────────────────────────

ACTOR_ENGINE     = "recovery_engine"
ACTOR_MANAGER    = "recovery_manager"
ACTOR_SCHEDULER  = "recovery_scheduler"
ACTOR_DISPATCHER = "recovery_dispatcher"
ACTOR_PIPELINE   = "recovery_pipeline"
ACTOR_OPERATOR   = "operator"
ACTOR_SYSTEM     = "system"
ACTOR_POLICY     = "policy"
ACTOR_WATCHDOG   = "watchdog"

# ── Recovery Engine Workflow State ────────────────────────────────────────────

class RecoveryEngineState(str, Enum):
    """
    High-level state of an active recovery workflow within the engine.

    Distinct from the LifecycleAwareMixin internal state (RUNNING/STOPPED).
    """
    IDLE         = "idle"
    INITIALIZING = "initializing"
    DETECTING    = "detecting"
    ASSESSING    = "assessing"
    PLANNING     = "planning"
    DISPATCHING  = "dispatching"
    RECOVERING   = "recovering"
    VERIFYING    = "verifying"
    COMPLETED    = "completed"
    FAILED       = "failed"
    STOPPED      = "stopped"


ACTIVE_ENGINE_STATES: FrozenSet[RecoveryEngineState] = frozenset({
    RecoveryEngineState.INITIALIZING,
    RecoveryEngineState.DETECTING,
    RecoveryEngineState.ASSESSING,
    RecoveryEngineState.PLANNING,
    RecoveryEngineState.DISPATCHING,
    RecoveryEngineState.RECOVERING,
    RecoveryEngineState.VERIFYING,
})

TERMINAL_ENGINE_STATES: FrozenSet[RecoveryEngineState] = frozenset({
    RecoveryEngineState.COMPLETED,
    RecoveryEngineState.FAILED,
    RecoveryEngineState.STOPPED,
})

# ── Request ───────────────────────────────────────────────────────────────────

class RecoveryRequestType(str, Enum):
    """Classification of recovery requests."""
    MANUAL       = "manual"
    AUTOMATIC    = "automatic"
    SCHEDULED    = "scheduled"
    EVENT_DRIVEN = "event_driven"
    PRIORITY     = "priority"


class RecoveryRequestPriority(int, Enum):
    """Priority levels for recovery requests.  Higher value = higher priority."""
    LOW       = 1
    NORMAL    = 2
    HIGH      = 3
    CRITICAL  = 4
    EMERGENCY = 5

# ── Response ──────────────────────────────────────────────────────────────────

class RecoveryResponseStatus(str, Enum):
    """Final status of a recovery request."""
    SUCCESS   = "success"
    FAILED    = "failed"
    PARTIAL   = "partial"
    CANCELLED = "cancelled"
    TIMEOUT   = "timeout"


class RecoveryOutcome(str, Enum):
    """Detailed recovery outcome."""
    RECOVERED        = "recovered"
    PARTIAL_RECOVERY = "partial_recovery"
    UNRECOVERABLE    = "unrecoverable"
    ABORTED          = "aborted"
    TIMED_OUT        = "timed_out"
    UNKNOWN          = "unknown"

# ── Events ────────────────────────────────────────────────────────────────────

class RecoveryEngineEventType(str, Enum):
    """Domain event types emitted by the ExecutionRecoveryEngine."""
    RECOVERY_INITIALIZED = "recovery_initialized"
    RECOVERY_STARTED     = "recovery_started"
    FAILURE_DETECTED     = "failure_detected"
    RECOVERY_DISPATCHED  = "recovery_dispatched"
    RECOVERY_VERIFIED    = "recovery_verified"
    RECOVERY_COMPLETED   = "recovery_completed"
    RECOVERY_FAILED      = "recovery_failed"
    RECOVERY_STOPPED     = "recovery_stopped"
    ENGINE_STARTED       = "engine_started"
    ENGINE_STOPPED       = "engine_stopped"

# ── Pipeline ──────────────────────────────────────────────────────────────────

class PipelineStage(str, Enum):
    """Ordered stages of the recovery pipeline."""
    VALIDATE_CONTEXT    = "validate_context"
    INITIALIZE_SESSION  = "initialize_session"
    ASSESS_FAILURE      = "assess_failure"
    PLAN_RECOVERY       = "plan_recovery"
    DISPATCH_WORKFLOW   = "dispatch_workflow"
    COORDINATE_POLICIES = "coordinate_policies"
    COORDINATE_FAILOVER = "coordinate_failover"
    VERIFY_RESULT       = "verify_result"
    PUBLISH_SNAPSHOT    = "publish_snapshot"
    FINALIZE            = "finalize"


PIPELINE_STAGES_ORDERED: Tuple[PipelineStage, ...] = (
    PipelineStage.VALIDATE_CONTEXT,
    PipelineStage.INITIALIZE_SESSION,
    PipelineStage.ASSESS_FAILURE,
    PipelineStage.PLAN_RECOVERY,
    PipelineStage.DISPATCH_WORKFLOW,
    PipelineStage.COORDINATE_POLICIES,
    PipelineStage.COORDINATE_FAILOVER,
    PipelineStage.VERIFY_RESULT,
    PipelineStage.PUBLISH_SNAPSHOT,
    PipelineStage.FINALIZE,
)


class PipelineStageStatus(str, Enum):
    """Execution status of a single pipeline stage."""
    PENDING   = "pending"
    RUNNING   = "running"
    COMPLETED = "completed"
    FAILED    = "failed"
    SKIPPED   = "skipped"

# ── Scheduler ─────────────────────────────────────────────────────────────────

class SchedulerMode(str, Enum):
    """Recovery scheduling modes."""
    AUTOMATIC    = "automatic"
    MANUAL       = "manual"
    SCHEDULED    = "scheduled"
    EVENT_DRIVEN = "event_driven"
    PRIORITY     = "priority"
