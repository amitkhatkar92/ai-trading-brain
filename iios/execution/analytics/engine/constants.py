"""
iios/execution/analytics/engine/constants.py
============================================
Constants and enumerations for the C8 Execution Analytics Engine.

C8 Execution Analytics & Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

from enum import Enum
from typing import Dict, FrozenSet


# ── System identifiers ────────────────────────────────────────────────────────

ENGINE_SYSTEM_ID      = "iios:execution:analytics:engine"
MANAGER_SYSTEM_ID     = "iios:execution:analytics:engine:manager"
SCHEDULER_SYSTEM_ID   = "iios:execution:analytics:engine:scheduler"
DISPATCHER_SYSTEM_ID  = "iios:execution:analytics:engine:dispatcher"
SESSION_MGR_SYSTEM_ID = "iios:execution:analytics:engine:session_manager"
REGISTRY_SYSTEM_ID    = "iios:execution:analytics:engine:registry"
FACTORY_SYSTEM_ID     = "iios:execution:analytics:engine:factory"

# ── Versioning ────────────────────────────────────────────────────────────────

VERSION        = "1.0.0"
SCHEMA_VERSION = "1.0"

# ── Default limits ────────────────────────────────────────────────────────────

DEFAULT_MAX_REQUESTS    = 10_000
DEFAULT_MAX_HISTORY     = 2_000
DEFAULT_MAX_PIPELINES   = 500
DEFAULT_SCHEDULER_QUEUE = 1_000
DEFAULT_MAX_SESSIONS    = 5_000

# ── Actor constants ───────────────────────────────────────────────────────────

ACTOR_ENGINE     = "iios:execution:analytics:engine"
ACTOR_MANAGER    = "iios:execution:analytics:engine:manager"
ACTOR_SCHEDULER  = "iios:execution:analytics:engine:scheduler"
ACTOR_DISPATCHER = "iios:execution:analytics:engine:dispatcher"
ACTOR_SYSTEM     = "iios:system"
ACTOR_OPERATOR   = "operator"


# ── Engine state enumeration ──────────────────────────────────────────────────

class EngineAnalyticsState(str, Enum):
    """Operational states for the Analytics Engine during a single analytics cycle."""

    IDLE         = "idle"
    INITIALIZING = "initializing"
    COLLECTING   = "collecting"
    VALIDATING   = "validating"
    DISPATCHING  = "dispatching"
    ANALYZING    = "analyzing"
    PUBLISHING   = "publishing"
    COMPLETED    = "completed"
    FAILED       = "failed"
    STOPPED      = "stopped"


# ── Engine state machine ──────────────────────────────────────────────────────

ENGINE_STATE_TRANSITIONS: Dict[EngineAnalyticsState, FrozenSet[EngineAnalyticsState]] = {
    EngineAnalyticsState.IDLE: frozenset({
        EngineAnalyticsState.INITIALIZING,
        EngineAnalyticsState.STOPPED,
    }),
    EngineAnalyticsState.INITIALIZING: frozenset({
        EngineAnalyticsState.COLLECTING,
        EngineAnalyticsState.FAILED,
        EngineAnalyticsState.STOPPED,
    }),
    EngineAnalyticsState.COLLECTING: frozenset({
        EngineAnalyticsState.VALIDATING,
        EngineAnalyticsState.FAILED,
        EngineAnalyticsState.STOPPED,
    }),
    EngineAnalyticsState.VALIDATING: frozenset({
        EngineAnalyticsState.DISPATCHING,
        EngineAnalyticsState.FAILED,
        EngineAnalyticsState.STOPPED,
    }),
    EngineAnalyticsState.DISPATCHING: frozenset({
        EngineAnalyticsState.ANALYZING,
        EngineAnalyticsState.FAILED,
        EngineAnalyticsState.STOPPED,
    }),
    EngineAnalyticsState.ANALYZING: frozenset({
        EngineAnalyticsState.PUBLISHING,
        EngineAnalyticsState.COLLECTING,   # re-collect if data insufficient
        EngineAnalyticsState.FAILED,
        EngineAnalyticsState.STOPPED,
    }),
    EngineAnalyticsState.PUBLISHING: frozenset({
        EngineAnalyticsState.COMPLETED,
        EngineAnalyticsState.FAILED,
        EngineAnalyticsState.STOPPED,
    }),
    EngineAnalyticsState.COMPLETED: frozenset({
        EngineAnalyticsState.IDLE,
    }),
    EngineAnalyticsState.FAILED: frozenset({
        EngineAnalyticsState.IDLE,
        EngineAnalyticsState.STOPPED,
    }),
    EngineAnalyticsState.STOPPED: frozenset(),  # terminal
}

ACTIVE_ENGINE_STATES: FrozenSet[EngineAnalyticsState] = frozenset({
    EngineAnalyticsState.INITIALIZING,
    EngineAnalyticsState.COLLECTING,
    EngineAnalyticsState.VALIDATING,
    EngineAnalyticsState.DISPATCHING,
    EngineAnalyticsState.ANALYZING,
    EngineAnalyticsState.PUBLISHING,
})

TERMINAL_ENGINE_STATES: FrozenSet[EngineAnalyticsState] = frozenset({
    EngineAnalyticsState.STOPPED,
})


# ── Engine operation enumeration ──────────────────────────────────────────────

class EngineOperation(str, Enum):
    """Operations supported by the Execution Analytics Engine."""

    INITIALIZE      = "initialize"
    START_ANALYTICS = "start_analytics"
    STOP_ANALYTICS  = "stop_analytics"
    COLLECT         = "collect"
    DISPATCH        = "dispatch"
    PUBLISH         = "publish"
    QUERY           = "query"
    VALIDATE        = "validate"


# ── Analytics request type ────────────────────────────────────────────────────

class AnalyticsRequestType(str, Enum):
    """Classification of an analytics request."""

    ON_DEMAND = "on_demand"
    PERIODIC  = "periodic"
    EVENT     = "event_driven"
    SCHEDULED = "scheduled"
    PRIORITY  = "priority"


# ── Pipeline stage ────────────────────────────────────────────────────────────

class PipelineStage(str, Enum):
    """Stages in an analytics pipeline execution."""

    CREATED     = "created"
    QUEUED      = "queued"
    COLLECTING  = "collecting"
    DISPATCHING = "dispatching"
    PROCESSING  = "processing"
    COMPLETED   = "completed"
    FAILED      = "failed"
    CANCELLED   = "cancelled"


# ── Pipeline status ───────────────────────────────────────────────────────────

class PipelineStatus(str, Enum):
    """Overall pipeline status."""

    PENDING   = "pending"
    ACTIVE    = "active"
    COMPLETED = "completed"
    FAILED    = "failed"
    CANCELLED = "cancelled"


# ── Response status ───────────────────────────────────────────────────────────

class ResponseStatus(str, Enum):
    """Status of an analytics response."""

    SUCCESS  = "success"
    FAILED   = "failed"
    PARTIAL  = "partial"
    PENDING  = "pending"
    REJECTED = "rejected"


# ── Schedule type ─────────────────────────────────────────────────────────────

class ScheduleType(str, Enum):
    """How an analytics job is triggered by the scheduler."""

    ONCE      = "once"
    PERIODIC  = "periodic"
    CRON      = "cron"
    EVENT     = "event"
    ON_DEMAND = "on_demand"


# ── Health status ─────────────────────────────────────────────────────────────

class EngineHealthStatus(str, Enum):
    """Operational health of the analytics engine."""

    HEALTHY   = "healthy"
    DEGRADED  = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN   = "unknown"


# ── Engine event type ─────────────────────────────────────────────────────────

class EngineEventType(str, Enum):
    """Domain events emitted by the Execution Analytics Engine."""

    ANALYTICS_INITIALIZED = "analytics_initialized"
    ANALYTICS_STARTED     = "analytics_started"
    ANALYTICS_COLLECTED   = "analytics_collected"
    ANALYTICS_DISPATCHED  = "analytics_dispatched"
    ANALYTICS_COMPLETED   = "analytics_completed"
    ANALYTICS_PUBLISHED   = "analytics_published"
    ANALYTICS_FAILED      = "analytics_failed"
    ANALYTICS_STOPPED     = "analytics_stopped"
