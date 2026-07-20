"""
constants.py — iios.decision.engine
=====================================
Enumerations, state machine, identifiers, and numeric defaults for the
Institutional Decision Engine subsystem.

C9 Decision Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

from enum import Enum, IntEnum
from typing import Dict, FrozenSet

# ---------------------------------------------------------------------------
# System identifiers
# ---------------------------------------------------------------------------
ENGINE_SYSTEM_ID:     str = "iios:decision:engine"
MANAGER_SYSTEM_ID:    str = "iios:decision:engine:manager"
SCHEDULER_SYSTEM_ID:  str = "iios:decision:engine:scheduler"
DISPATCHER_SYSTEM_ID: str = "iios:decision:engine:dispatcher"
REGISTRY_SYSTEM_ID:   str = "iios:decision:engine:registry"
FACTORY_SYSTEM_ID:    str = "iios:decision:engine:factory"

# ---------------------------------------------------------------------------
# Versioning
# ---------------------------------------------------------------------------
VERSION:        str = "1.0.0"
SCHEMA_VERSION: str = "1.0"

# ---------------------------------------------------------------------------
# Actor constants
# ---------------------------------------------------------------------------
ACTOR_ENGINE:     str = "iios:decision:engine"
ACTOR_SCHEDULER:  str = "iios:decision:engine:scheduler"
ACTOR_DISPATCHER: str = "iios:decision:engine:dispatcher"
ACTOR_MANAGER:    str = "iios:decision:engine:manager"
ACTOR_SYSTEM:     str = "iios:system"
ACTOR_OPERATOR:   str = "operator"

# ---------------------------------------------------------------------------
# Default limits and tuning parameters
# ---------------------------------------------------------------------------
DEFAULT_MAX_ACTIVE:     int = 1_000
DEFAULT_MAX_COMPLETED:  int = 5_000
DEFAULT_MAX_HISTORY:    int = 2_000
DEFAULT_MAX_QUEUE:      int = 10_000
DEFAULT_WORKER_THREADS: int = 4
DEFAULT_DEADLINE_S:     float = 30.0       # seconds per decision
EMA_ALPHA:              float = 0.1        # smoothing for time averages


# ---------------------------------------------------------------------------
# PipelineState — states of a single decision processing pipeline
# ---------------------------------------------------------------------------
class PipelineState(str, Enum):
    """
    Lifecycle state of an individual :class:`DecisionPipeline`.

    IDLE → INITIALIZING → COLLECTING → VALIDATING → DISPATCHING →
    EVALUATING → PUBLISHING → COMPLETED
    Any state → FAILED
    Any state → CANCELLED
    Any running state → STOPPED
    """
    IDLE         = "idle"
    INITIALIZING = "initializing"
    COLLECTING   = "collecting"
    VALIDATING   = "validating"
    DISPATCHING  = "dispatching"
    EVALUATING   = "evaluating"
    PUBLISHING   = "publishing"
    COMPLETED    = "completed"
    FAILED       = "failed"
    CANCELLED    = "cancelled"
    STOPPED      = "stopped"


#: States that represent an in-flight pipeline
PIPELINE_ACTIVE_STATES: FrozenSet[PipelineState] = frozenset({
    PipelineState.IDLE,
    PipelineState.INITIALIZING,
    PipelineState.COLLECTING,
    PipelineState.VALIDATING,
    PipelineState.DISPATCHING,
    PipelineState.EVALUATING,
    PipelineState.PUBLISHING,
})

#: Terminal pipeline states
PIPELINE_TERMINAL_STATES: FrozenSet[PipelineState] = frozenset({
    PipelineState.COMPLETED,
    PipelineState.FAILED,
    PipelineState.CANCELLED,
    PipelineState.STOPPED,
})

#: Valid pipeline state transitions
PIPELINE_VALID_TRANSITIONS: Dict[PipelineState, FrozenSet[PipelineState]] = {
    PipelineState.IDLE: frozenset({
        PipelineState.INITIALIZING, PipelineState.FAILED, PipelineState.CANCELLED,
    }),
    PipelineState.INITIALIZING: frozenset({
        PipelineState.COLLECTING, PipelineState.FAILED, PipelineState.STOPPED,
    }),
    PipelineState.COLLECTING: frozenset({
        PipelineState.VALIDATING, PipelineState.FAILED, PipelineState.STOPPED,
    }),
    PipelineState.VALIDATING: frozenset({
        PipelineState.DISPATCHING, PipelineState.COLLECTING,
        PipelineState.FAILED, PipelineState.STOPPED,
    }),
    PipelineState.DISPATCHING: frozenset({
        PipelineState.EVALUATING, PipelineState.FAILED, PipelineState.STOPPED,
    }),
    PipelineState.EVALUATING: frozenset({
        PipelineState.PUBLISHING, PipelineState.FAILED, PipelineState.STOPPED,
    }),
    PipelineState.PUBLISHING: frozenset({
        PipelineState.COMPLETED, PipelineState.FAILED, PipelineState.STOPPED,
    }),
    PipelineState.COMPLETED:  frozenset(),
    PipelineState.FAILED:     frozenset(),
    PipelineState.CANCELLED:  frozenset(),
    PipelineState.STOPPED:    frozenset(),
}


# ---------------------------------------------------------------------------
# DecisionMode — how a decision was triggered / scheduled
# ---------------------------------------------------------------------------
class DecisionMode(str, Enum):
    """Scheduling mode for a decision request."""
    REAL_TIME    = "real_time"
    EVENT_DRIVEN = "event_driven"
    SCHEDULED    = "scheduled"
    MANUAL       = "manual"
    PRIORITY     = "priority"
    BATCH        = "batch"


# ---------------------------------------------------------------------------
# DecisionEngineEventType — the eight engine lifecycle event types
# ---------------------------------------------------------------------------
class DecisionEngineEventType(str, Enum):
    """The eight decision engine event types mandated by the specification."""
    DECISION_INITIALIZED = "decision_initialized"
    DECISION_STARTED     = "decision_started"
    DECISION_COLLECTED   = "decision_collected"
    DECISION_DISPATCHED  = "decision_dispatched"
    DECISION_COMPLETED   = "decision_completed"
    DECISION_PUBLISHED   = "decision_published"
    DECISION_FAILED      = "decision_failed"
    DECISION_STOPPED     = "decision_stopped"


# ---------------------------------------------------------------------------
# DecisionResponseStatus
# ---------------------------------------------------------------------------
class DecisionResponseStatus(str, Enum):
    """Outcome status for a :class:`DecisionResponse`."""
    SUCCESS = "success"
    FAILED  = "failed"
    PARTIAL = "partial"
    TIMEOUT = "timeout"


# ---------------------------------------------------------------------------
# EngineValidationCode — the six validation check codes
# ---------------------------------------------------------------------------
class EngineValidationCode(str, Enum):
    """Identifies a specific validation check in the engine validator."""
    SESSION_VALIDITY      = "session_validity"
    PIPELINE_CONSISTENCY  = "pipeline_consistency"
    LIFECYCLE_CONSISTENCY = "lifecycle_consistency"
    SNAPSHOT_CONSISTENCY  = "snapshot_consistency"
    SUBSYSTEM_HEALTH      = "subsystem_health"
    INPUT_COMPLETENESS    = "input_completeness"


# ---------------------------------------------------------------------------
# EngineHealthStatus
# ---------------------------------------------------------------------------
class EngineHealthStatus(str, Enum):
    """Overall health of the decision engine or one of its subsystems."""
    HEALTHY   = "healthy"
    DEGRADED  = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN   = "unknown"


# ---------------------------------------------------------------------------
# EngineOperationalStatus
# ---------------------------------------------------------------------------
class EngineOperationalStatus(str, Enum):
    """Operational status of the engine as a whole."""
    RUNNING  = "running"
    IDLE     = "idle"
    STARTING = "starting"
    STOPPING = "stopping"
    STOPPED  = "stopped"
    ERROR    = "error"
    UNKNOWN  = "unknown"


# ---------------------------------------------------------------------------
# DecisionPriority — scheduling priority (same values as M1 but standalone)
# ---------------------------------------------------------------------------
class DecisionPriority(IntEnum):
    """Decision scheduling priority (lower = higher urgency)."""
    CRITICAL   = 1
    HIGH       = 2
    MEDIUM     = 3
    LOW        = 4
    BACKGROUND = 5
