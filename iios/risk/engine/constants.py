"""
constants.py — iios.risk.engine
=================================
Enumerations, state machine, identifiers, and numeric defaults for the
Institutional Risk Engine subsystem.

C11 Risk Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

from enum import Enum, IntEnum
from typing import Dict, FrozenSet

# ---------------------------------------------------------------------------
# System identifiers
# ---------------------------------------------------------------------------
ENGINE_SYSTEM_ID:     str = "iios:risk:engine"
SCHEDULER_SYSTEM_ID:  str = "iios:risk:engine:scheduler"
DISPATCHER_SYSTEM_ID: str = "iios:risk:engine:dispatcher"
REGISTRY_SYSTEM_ID:   str = "iios:risk:engine:registry"
FACTORY_SYSTEM_ID:    str = "iios:risk:engine:factory"

# ---------------------------------------------------------------------------
# Versioning
# ---------------------------------------------------------------------------
VERSION:        str = "1.0.0"
SCHEMA_VERSION: str = "1.0"

# ---------------------------------------------------------------------------
# Actor constants
# ---------------------------------------------------------------------------
ACTOR_ENGINE:     str = "iios:risk:engine"
ACTOR_SCHEDULER:  str = "iios:risk:engine:scheduler"
ACTOR_DISPATCHER: str = "iios:risk:engine:dispatcher"
ACTOR_OPERATOR:   str = "operator"
ACTOR_SYSTEM:     str = "iios:system"

# ---------------------------------------------------------------------------
# Default limits
# ---------------------------------------------------------------------------
DEFAULT_MAX_CONCURRENT_SESSIONS: int = 100
DEFAULT_MAX_PIPELINES:           int = 5_000
DEFAULT_MAX_HISTORY:             int = 1_000
DEFAULT_MAX_SCHEDULER_QUEUE:     int = 10_000
DEFAULT_MAX_ARCHIVED_PIPELINES:  int = 10_000

# ---------------------------------------------------------------------------
# Timeout defaults (seconds)
# ---------------------------------------------------------------------------
DEFAULT_COLLECT_TIMEOUT_S:  float = 30.0
DEFAULT_DISPATCH_TIMEOUT_S: float = 60.0
DEFAULT_PUBLISH_TIMEOUT_S:  float = 30.0


# ---------------------------------------------------------------------------
# EngineState — risk engine processing states
# ---------------------------------------------------------------------------
class EngineState(str, Enum):
    """
    States of a risk engine processing cycle.

    Each call to :meth:`RiskEngine.submit` drives a request through
    this state machine from IDLE to COMPLETED (or FAILED).

    Lifecycle progression (happy path)::

        IDLE → INITIALIZING → COLLECTING → VALIDATING
             → DISPATCHING → ASSESSING → MONITORING → PUBLISHING
             → COMPLETED → IDLE

    Failure::

        any active state → FAILED → IDLE

    Stop::

        any state → STOPPED (terminal)
    """
    IDLE         = "idle"
    INITIALIZING = "initializing"
    COLLECTING   = "collecting"
    VALIDATING   = "validating"
    DISPATCHING  = "dispatching"
    ASSESSING    = "assessing"
    MONITORING   = "monitoring"
    PUBLISHING   = "publishing"
    COMPLETED    = "completed"
    FAILED       = "failed"
    STOPPED      = "stopped"


# ---------------------------------------------------------------------------
# Valid engine-state transitions
# ---------------------------------------------------------------------------
VALID_ENGINE_TRANSITIONS: Dict[EngineState, FrozenSet[EngineState]] = {
    EngineState.IDLE: frozenset({
        EngineState.INITIALIZING,
        EngineState.STOPPED,
    }),
    EngineState.INITIALIZING: frozenset({
        EngineState.COLLECTING,
        EngineState.FAILED,
    }),
    EngineState.COLLECTING: frozenset({
        EngineState.VALIDATING,
        EngineState.FAILED,
    }),
    EngineState.VALIDATING: frozenset({
        EngineState.DISPATCHING,
        EngineState.FAILED,
    }),
    EngineState.DISPATCHING: frozenset({
        EngineState.ASSESSING,
        EngineState.MONITORING,
        EngineState.PUBLISHING,
        EngineState.FAILED,
    }),
    EngineState.ASSESSING: frozenset({
        EngineState.MONITORING,
        EngineState.PUBLISHING,
        EngineState.FAILED,
    }),
    EngineState.MONITORING: frozenset({
        EngineState.PUBLISHING,
        EngineState.FAILED,
    }),
    EngineState.PUBLISHING: frozenset({
        EngineState.COMPLETED,
        EngineState.FAILED,
    }),
    EngineState.COMPLETED: frozenset({
        EngineState.IDLE,
    }),
    EngineState.FAILED: frozenset({
        EngineState.IDLE,
    }),
    EngineState.STOPPED: frozenset(),  # terminal
}

# Active (non-terminal, non-idle) processing states
ACTIVE_ENGINE_STATES: FrozenSet[EngineState] = frozenset({
    EngineState.INITIALIZING,
    EngineState.COLLECTING,
    EngineState.VALIDATING,
    EngineState.DISPATCHING,
    EngineState.ASSESSING,
    EngineState.MONITORING,
    EngineState.PUBLISHING,
})

TERMINAL_ENGINE_STATES: FrozenSet[EngineState] = frozenset({
    EngineState.COMPLETED,
    EngineState.FAILED,
    EngineState.STOPPED,
})


# ---------------------------------------------------------------------------
# RiskWorkflowType — supported risk workflows
# ---------------------------------------------------------------------------
class RiskWorkflowType(str, Enum):
    """Supported risk workflow types."""
    PORTFOLIO_RISK_ASSESSMENT = "portfolio_risk_assessment"
    POSITION_RISK_ASSESSMENT  = "position_risk_assessment"
    ACCOUNT_RISK_ASSESSMENT   = "account_risk_assessment"
    EXPOSURE_MONITORING       = "exposure_monitoring"
    LIMIT_MONITORING          = "limit_monitoring"
    STRESS_TEST               = "stress_test"
    SCENARIO_ANALYSIS         = "scenario_analysis"
    INTRADAY_RISK_REVIEW      = "intraday_risk_review"
    EOD_RISK_REVIEW           = "eod_risk_review"


# ---------------------------------------------------------------------------
# SchedulerPriority
# ---------------------------------------------------------------------------
class SchedulerPriority(IntEnum):
    """Scheduling priority — lower integer = higher priority."""
    CRITICAL = 0
    HIGH     = 1
    NORMAL   = 2
    LOW      = 3
    BATCH    = 4


# ---------------------------------------------------------------------------
# ResponseStatus
# ---------------------------------------------------------------------------
class ResponseStatus(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"


# ---------------------------------------------------------------------------
# PipelineStatus
# ---------------------------------------------------------------------------
class PipelineStatus(str, Enum):
    PENDING   = "pending"
    RUNNING   = "running"
    COMPLETED = "completed"
    FAILED    = "failed"
    CANCELLED = "cancelled"


# ---------------------------------------------------------------------------
# RiskEngineEventType — nine engine events
# ---------------------------------------------------------------------------
class RiskEngineEventType(str, Enum):
    RISK_INITIALIZED         = "risk_initialized"
    RISK_STARTED             = "risk_started"
    RISK_COLLECTED           = "risk_collected"
    RISK_DISPATCHED          = "risk_dispatched"
    RISK_ASSESSMENT_STARTED  = "risk_assessment_started"
    RISK_PUBLISHED           = "risk_published"
    RISK_COMPLETED           = "risk_completed"
    RISK_FAILED              = "risk_failed"
    RISK_STOPPED             = "risk_stopped"


# ---------------------------------------------------------------------------
# Workflow routing sets
# ---------------------------------------------------------------------------

# Workflows that require deep assessment (policy + optimization framework)
ASSESSMENT_WORKFLOWS: FrozenSet[RiskWorkflowType] = frozenset({
    RiskWorkflowType.PORTFOLIO_RISK_ASSESSMENT,
    RiskWorkflowType.POSITION_RISK_ASSESSMENT,
    RiskWorkflowType.ACCOUNT_RISK_ASSESSMENT,
    RiskWorkflowType.STRESS_TEST,
    RiskWorkflowType.SCENARIO_ANALYSIS,
    RiskWorkflowType.INTRADAY_RISK_REVIEW,
    RiskWorkflowType.EOD_RISK_REVIEW,
})

# Workflows that are primarily monitoring (may skip full assessment)
MONITORING_WORKFLOWS: FrozenSet[RiskWorkflowType] = frozenset({
    RiskWorkflowType.EXPOSURE_MONITORING,
    RiskWorkflowType.LIMIT_MONITORING,
})
