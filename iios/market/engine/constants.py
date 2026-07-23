"""
constants.py — iios.market.engine
===================================
Enumerations, state machine, identifiers, and numeric defaults for the
Institutional Market Engine subsystem.

C12 Market Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

from enum import Enum, IntEnum
from typing import Dict, FrozenSet

# ---------------------------------------------------------------------------
# System identifiers
# ---------------------------------------------------------------------------
ENGINE_SYSTEM_ID:     str = "iios:market:engine"
SCHEDULER_SYSTEM_ID:  str = "iios:market:engine:scheduler"
DISPATCHER_SYSTEM_ID: str = "iios:market:engine:dispatcher"
REGISTRY_SYSTEM_ID:   str = "iios:market:engine:registry"
FACTORY_SYSTEM_ID:    str = "iios:market:engine:factory"

# ---------------------------------------------------------------------------
# Versioning
# ---------------------------------------------------------------------------
VERSION:        str = "1.0.0"
SCHEMA_VERSION: str = "1.0"

# ---------------------------------------------------------------------------
# Actor constants
# ---------------------------------------------------------------------------
ACTOR_ENGINE:     str = "iios:market:engine"
ACTOR_SCHEDULER:  str = "iios:market:engine:scheduler"
ACTOR_DISPATCHER: str = "iios:market:engine:dispatcher"
ACTOR_OPERATOR:   str = "operator"
ACTOR_SYSTEM:     str = "iios:system"

# ---------------------------------------------------------------------------
# Default limits
# ---------------------------------------------------------------------------
DEFAULT_MAX_CONCURRENT_SESSIONS: int = 200
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
# EngineState — market engine processing states
# ---------------------------------------------------------------------------
class EngineState(str, Enum):
    """
    States of a market engine processing cycle.

    Each call to :meth:`MarketEngine.submit` drives a request through
    this state machine from IDLE to COMPLETED (or FAILED).

    Lifecycle progression (happy path)::

        IDLE → INITIALIZING → COLLECTING → VALIDATING
             → DISPATCHING → ANALYZING → MONITORING → PUBLISHING
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
    ANALYZING    = "analyzing"
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
        EngineState.ANALYZING,
        EngineState.MONITORING,
        EngineState.PUBLISHING,
        EngineState.FAILED,
    }),
    EngineState.ANALYZING: frozenset({
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
    EngineState.ANALYZING,
    EngineState.MONITORING,
    EngineState.PUBLISHING,
})

TERMINAL_ENGINE_STATES: FrozenSet[EngineState] = frozenset({
    EngineState.COMPLETED,
    EngineState.FAILED,
    EngineState.STOPPED,
})


# ---------------------------------------------------------------------------
# MarketWorkflowType — supported market workflows
# ---------------------------------------------------------------------------
class MarketWorkflowType(str, Enum):
    """Supported market workflow types."""
    MARKET_OVERVIEW       = "market_overview"
    REGIME_DETECTION      = "regime_detection"
    SECTOR_ANALYSIS       = "sector_analysis"
    INDEX_ANALYSIS        = "index_analysis"
    BREADTH_REVIEW        = "breadth_review"
    VOLATILITY_MONITORING = "volatility_monitoring"
    ECONOMIC_EVENT_REVIEW = "economic_event_review"
    INTRADAY_MONITORING   = "intraday_monitoring"
    EOD_REVIEW            = "eod_review"


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
# MarketEngineEventType — nine engine events
# ---------------------------------------------------------------------------
class MarketEngineEventType(str, Enum):
    MARKET_INITIALIZED     = "market_initialized"
    MARKET_STARTED         = "market_started"
    MARKET_COLLECTED       = "market_collected"
    MARKET_DISPATCHED      = "market_dispatched"
    MARKET_ANALYSIS_STARTED = "market_analysis_started"
    MARKET_PUBLISHED       = "market_published"
    MARKET_COMPLETED       = "market_completed"
    MARKET_FAILED          = "market_failed"
    MARKET_STOPPED         = "market_stopped"


# ---------------------------------------------------------------------------
# Workflow routing sets
# ---------------------------------------------------------------------------

# Workflows that require deep analysis (policy + analytics framework)
ANALYSIS_WORKFLOWS: FrozenSet[MarketWorkflowType] = frozenset({
    MarketWorkflowType.MARKET_OVERVIEW,
    MarketWorkflowType.REGIME_DETECTION,
    MarketWorkflowType.SECTOR_ANALYSIS,
    MarketWorkflowType.INDEX_ANALYSIS,
    MarketWorkflowType.BREADTH_REVIEW,
    MarketWorkflowType.ECONOMIC_EVENT_REVIEW,
    MarketWorkflowType.EOD_REVIEW,
})

# Workflows that are primarily monitoring (may skip full analysis)
MONITORING_WORKFLOWS: FrozenSet[MarketWorkflowType] = frozenset({
    MarketWorkflowType.VOLATILITY_MONITORING,
    MarketWorkflowType.INTRADAY_MONITORING,
})
