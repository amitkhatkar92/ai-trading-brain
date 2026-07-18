"""
iios/execution/analytics/lifecycle/constants.py
===============================================
Constants and enumerations for the C8 Execution Analytics Lifecycle.

C8 Execution Analytics & Intelligence — Phase 1, Module 1
"""
from __future__ import annotations

from enum import Enum
from typing import Dict, FrozenSet


# ── System identifiers ────────────────────────────────────────────────────────

LIFECYCLE_SYSTEM_ID = "iios:execution:analytics:lifecycle"
REGISTRY_SYSTEM_ID  = "iios:execution:analytics:lifecycle:registry"
FACTORY_SYSTEM_ID   = "iios:execution:analytics:lifecycle:factory"

# ── Versioning ────────────────────────────────────────────────────────────────

VERSION        = "1.0.0"
SCHEMA_VERSION = "1.0"

# ── Default limits ────────────────────────────────────────────────────────────

DEFAULT_MAX_SESSIONS    = 5_000
DEFAULT_MAX_HISTORY     = 1_000
DEFAULT_MAX_TRANSITIONS = 50_000

# ── Actor constants ───────────────────────────────────────────────────────────

ACTOR_LIFECYCLE = "iios:execution:analytics:lifecycle"
ACTOR_OPERATOR  = "operator"
ACTOR_SYSTEM    = "iios:system"
ACTOR_ANALYTICS = "iios:analytics:engine"
ACTOR_SCHEDULER = "iios:analytics:scheduler"


# ── Analytics state enumeration ───────────────────────────────────────────────

class AnalyticsState(str, Enum):
    """
    All possible lifecycle states for an analytics session.

    Lifecycle progression (happy path):
        CREATED → INITIALIZING → COLLECTING → ANALYZING → READY
                → ACTIVE → COMPLETED
        Any active state → PAUSED
        PAUSED → RESUMING → (back to prior active state)
        Any active state → FAILED
        Terminal states → ARCHIVED
    """

    CREATED      = "created"
    INITIALIZING = "initializing"
    COLLECTING   = "collecting"
    ANALYZING    = "analyzing"
    READY        = "ready"
    ACTIVE       = "active"
    PAUSED       = "paused"
    RESUMING     = "resuming"
    COMPLETED    = "completed"
    FAILED       = "failed"
    ARCHIVED     = "archived"


# ── State machine ─────────────────────────────────────────────────────────────

VALID_TRANSITIONS: Dict[AnalyticsState, FrozenSet[AnalyticsState]] = {
    AnalyticsState.CREATED: frozenset({
        AnalyticsState.INITIALIZING,
        AnalyticsState.FAILED,
    }),
    AnalyticsState.INITIALIZING: frozenset({
        AnalyticsState.COLLECTING,
        AnalyticsState.FAILED,
    }),
    AnalyticsState.COLLECTING: frozenset({
        AnalyticsState.ANALYZING,
        AnalyticsState.PAUSED,
        AnalyticsState.FAILED,
    }),
    AnalyticsState.ANALYZING: frozenset({
        AnalyticsState.READY,
        AnalyticsState.COLLECTING,    # re-collect if data insufficient
        AnalyticsState.PAUSED,
        AnalyticsState.FAILED,
    }),
    AnalyticsState.READY: frozenset({
        AnalyticsState.ACTIVE,
        AnalyticsState.PAUSED,
        AnalyticsState.FAILED,
    }),
    AnalyticsState.ACTIVE: frozenset({
        AnalyticsState.COMPLETED,
        AnalyticsState.PAUSED,
        AnalyticsState.ANALYZING,     # re-analyze cycle
        AnalyticsState.FAILED,
    }),
    AnalyticsState.PAUSED: frozenset({
        AnalyticsState.RESUMING,
        AnalyticsState.FAILED,
    }),
    AnalyticsState.RESUMING: frozenset({
        AnalyticsState.COLLECTING,
        AnalyticsState.ANALYZING,
        AnalyticsState.READY,
        AnalyticsState.ACTIVE,
        AnalyticsState.FAILED,
    }),
    AnalyticsState.COMPLETED: frozenset({
        AnalyticsState.ARCHIVED,
    }),
    AnalyticsState.FAILED: frozenset({
        AnalyticsState.ARCHIVED,
    }),
    AnalyticsState.ARCHIVED: frozenset(),  # terminal
}

#: States where the session is in-flight.
ACTIVE_STATES: FrozenSet[AnalyticsState] = frozenset({
    AnalyticsState.INITIALIZING,
    AnalyticsState.COLLECTING,
    AnalyticsState.ANALYZING,
    AnalyticsState.READY,
    AnalyticsState.ACTIVE,
    AnalyticsState.PAUSED,
    AnalyticsState.RESUMING,
})

#: States where the session has ended.
TERMINAL_STATES: FrozenSet[AnalyticsState] = frozenset({
    AnalyticsState.COMPLETED,
    AnalyticsState.FAILED,
    AnalyticsState.ARCHIVED,
})

#: States where no further transitions are allowed.
IMMUTABLE_STATES: FrozenSet[AnalyticsState] = frozenset({
    AnalyticsState.ARCHIVED,
})

#: States that represent a successful outcome.
SUCCESS_STATES: FrozenSet[AnalyticsState] = frozenset({
    AnalyticsState.COMPLETED,
    AnalyticsState.ARCHIVED,
})


# ── Analytics scope ───────────────────────────────────────────────────────────

class AnalyticsScope(str, Enum):
    """Defines the data scope of an analytics session."""

    EXECUTION   = "execution"    # single execution session
    PORTFOLIO   = "portfolio"    # portfolio-wide
    STRATEGY    = "strategy"     # strategy-level
    WORKFLOW    = "workflow"     # single workflow
    SYSTEM      = "system"       # full system scope
    CUSTOM      = "custom"       # caller-defined scope


# ── Analytics mode ────────────────────────────────────────────────────────────

class AnalyticsMode(str, Enum):
    """Operational mode of an analytics session."""

    REAL_TIME   = "real_time"    # continuous live data
    BATCH       = "batch"        # periodic batch analysis
    ON_DEMAND   = "on_demand"    # triggered manually or by event
    SCHEDULED   = "scheduled"    # time-scheduled
    REPLAY      = "replay"       # historical replay


# ── Analytics trigger ─────────────────────────────────────────────────────────

class AnalyticsTrigger(str, Enum):
    """Classifies what triggered an analytics session."""

    MANUAL       = "manual"
    AUTOMATIC    = "automatic"
    SCHEDULED    = "scheduled"
    EVENT_DRIVEN = "event_driven"
    SYSTEM       = "system"


# ── Event types ───────────────────────────────────────────────────────────────

class AnalyticsEventType(str, Enum):
    """Types of lifecycle events emitted by AnalyticsLifecycle."""

    ANALYTICS_CREATED     = "analytics_created"
    ANALYTICS_INITIALIZED = "analytics_initialized"
    ANALYTICS_STARTED     = "analytics_started"
    ANALYTICS_PAUSED      = "analytics_paused"
    ANALYTICS_RESUMED     = "analytics_resumed"
    ANALYTICS_COMPLETED   = "analytics_completed"
    ANALYTICS_FAILED      = "analytics_failed"
    ANALYTICS_ARCHIVED    = "analytics_archived"
