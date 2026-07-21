"""
constants.py — iios.portfolio.engine
======================================
Enumerations, state machine, identifiers, and numeric defaults for the
Institutional Portfolio Engine subsystem.

C10 Portfolio Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

from enum import Enum
from typing import Dict, FrozenSet

# ---------------------------------------------------------------------------
# System identifiers
# ---------------------------------------------------------------------------
ENGINE_SYSTEM_ID:      str = "iios:portfolio:engine"
SCHEDULER_SYSTEM_ID:   str = "iios:portfolio:engine:scheduler"
DISPATCHER_SYSTEM_ID:  str = "iios:portfolio:engine:dispatcher"
REGISTRY_SYSTEM_ID:    str = "iios:portfolio:engine:registry"
FACTORY_SYSTEM_ID:     str = "iios:portfolio:engine:factory"

# ---------------------------------------------------------------------------
# Versioning
# ---------------------------------------------------------------------------
VERSION:        str = "1.0.0"
SCHEMA_VERSION: str = "1.0"

# ---------------------------------------------------------------------------
# Actor constants
# ---------------------------------------------------------------------------
ACTOR_ENGINE:     str = "iios:portfolio:engine"
ACTOR_SCHEDULER:  str = "iios:portfolio:engine:scheduler"
ACTOR_DISPATCHER: str = "iios:portfolio:engine:dispatcher"
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
DEFAULT_COLLECT_TIMEOUT_S:   float = 30.0
DEFAULT_DISPATCH_TIMEOUT_S:  float = 60.0
DEFAULT_PUBLISH_TIMEOUT_S:   float = 30.0

# ---------------------------------------------------------------------------
# EngineState — per-workflow processing states
# ---------------------------------------------------------------------------
class EngineState(str, Enum):
    """
    States of a portfolio engine processing cycle.

    Each call to :meth:`PortfolioEngine.submit` drives a request through
    this state machine from IDLE to COMPLETED (or FAILED).

    Lifecycle progression (happy path)::

        IDLE → INITIALIZING → COLLECTING → VALIDATING
             → DISPATCHING → ALLOCATING/REBALANCING → PUBLISHING
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
    ALLOCATING   = "allocating"
    REBALANCING  = "rebalancing"
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
        EngineState.ALLOCATING,
        EngineState.REBALANCING,
        EngineState.PUBLISHING,
        EngineState.FAILED,
    }),
    EngineState.ALLOCATING: frozenset({
        EngineState.PUBLISHING,
        EngineState.FAILED,
    }),
    EngineState.REBALANCING: frozenset({
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
    EngineState.STOPPED: frozenset(),   # terminal
}

# Active (non-terminal, non-idle) processing states
ACTIVE_ENGINE_STATES: FrozenSet[EngineState] = frozenset({
    EngineState.INITIALIZING,
    EngineState.COLLECTING,
    EngineState.VALIDATING,
    EngineState.DISPATCHING,
    EngineState.ALLOCATING,
    EngineState.REBALANCING,
    EngineState.PUBLISHING,
})

TERMINAL_ENGINE_STATES: FrozenSet[EngineState] = frozenset({
    EngineState.COMPLETED,
    EngineState.FAILED,
    EngineState.STOPPED,
})


# ---------------------------------------------------------------------------
# PortfolioWorkflowType
# ---------------------------------------------------------------------------
class PortfolioWorkflowType(str, Enum):
    """Supported portfolio workflow types."""
    PORTFOLIO_CREATION       = "portfolio_creation"
    PORTFOLIO_UPDATE         = "portfolio_update"
    PORTFOLIO_VALIDATION     = "portfolio_validation"
    PORTFOLIO_REBALANCING    = "portfolio_rebalancing"
    CAPITAL_ALLOCATION       = "capital_allocation"
    EXPOSURE_MANAGEMENT      = "exposure_management"
    RISK_SYNCHRONIZATION     = "risk_synchronization"
    PORTFOLIO_SYNCHRONIZATION = "portfolio_synchronization"
    PORTFOLIO_CLOSURE        = "portfolio_closure"


# ---------------------------------------------------------------------------
# PortfolioOperationType
# ---------------------------------------------------------------------------
class PortfolioOperationType(str, Enum):
    """Engine operation identifiers."""
    INITIALIZE       = "initialize"
    START_PORTFOLIO  = "start_portfolio"
    STOP_PORTFOLIO   = "stop_portfolio"
    COLLECT          = "collect"
    DISPATCH         = "dispatch"
    PUBLISH          = "publish"
    QUERY            = "query"
    VALIDATE         = "validate"


# ---------------------------------------------------------------------------
# PortfolioEventType
# ---------------------------------------------------------------------------
class PortfolioEventType(str, Enum):
    """Event types emitted by the Portfolio Engine."""
    PORTFOLIO_INITIALIZED = "portfolio_initialized"
    PORTFOLIO_STARTED     = "portfolio_started"
    PORTFOLIO_COLLECTED   = "portfolio_collected"
    PORTFOLIO_DISPATCHED  = "portfolio_dispatched"
    PORTFOLIO_PUBLISHED   = "portfolio_published"
    PORTFOLIO_COMPLETED   = "portfolio_completed"
    PORTFOLIO_FAILED      = "portfolio_failed"
    PORTFOLIO_STOPPED     = "portfolio_stopped"


# ---------------------------------------------------------------------------
# PipelineStatus
# ---------------------------------------------------------------------------
class PipelineStatus(str, Enum):
    """Lifecycle status of a portfolio pipeline."""
    PENDING    = "pending"
    RUNNING    = "running"
    COMPLETED  = "completed"
    FAILED     = "failed"
    CANCELLED  = "cancelled"


# ---------------------------------------------------------------------------
# SchedulerPriority
# ---------------------------------------------------------------------------
class SchedulerPriority(int, Enum):
    """Priority levels for the portfolio scheduler (lower int = higher priority)."""
    CRITICAL = 0
    HIGH     = 1
    NORMAL   = 2
    LOW      = 3


# ---------------------------------------------------------------------------
# ValidationCode
# ---------------------------------------------------------------------------
class ValidationCode(str, Enum):
    """Validation check identifiers."""
    SESSION_VALIDITY      = "session_validity"
    PIPELINE_CONSISTENCY  = "pipeline_consistency"
    LIFECYCLE_CONSISTENCY = "lifecycle_consistency"
    SNAPSHOT_CONSISTENCY  = "snapshot_consistency"
    SUBSYSTEM_HEALTH      = "subsystem_health"
    INPUT_COMPLETENESS    = "input_completeness"


# ---------------------------------------------------------------------------
# ResponseStatus
# ---------------------------------------------------------------------------
class ResponseStatus(str, Enum):
    """Portfolio response outcome status."""
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
