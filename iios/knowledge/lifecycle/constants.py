"""
constants.py — iios.knowledge.lifecycle
=========================================
Enumerations, state machine, identifiers, and defaults for the
Institutional Knowledge Lifecycle subsystem.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 1
"""
from __future__ import annotations

from enum import Enum
from typing import Dict, FrozenSet

# ---------------------------------------------------------------------------
# System identifiers
# ---------------------------------------------------------------------------
LIFECYCLE_SYSTEM_ID: str = "iios:knowledge:lifecycle"
REGISTRY_SYSTEM_ID:  str = "iios:knowledge:lifecycle:registry"
FACTORY_SYSTEM_ID:   str = "iios:knowledge:lifecycle:factory"

# ---------------------------------------------------------------------------
# Versioning
# ---------------------------------------------------------------------------
VERSION:        str = "1.0.0"
SCHEMA_VERSION: str = "1.0"

# ---------------------------------------------------------------------------
# Default limits
# ---------------------------------------------------------------------------
DEFAULT_MAX_SESSIONS:    int = 5_000
DEFAULT_MAX_ARCHIVED:    int = 10_000
DEFAULT_MAX_HISTORY:     int = 1_000
DEFAULT_MAX_TRANSITIONS: int = 50_000

# ---------------------------------------------------------------------------
# Actor constants
# ---------------------------------------------------------------------------
ACTOR_LIFECYCLE:  str = "iios:knowledge:lifecycle"
ACTOR_OPERATOR:   str = "operator"
ACTOR_SYSTEM:     str = "iios:system"


# ---------------------------------------------------------------------------
# KnowledgeLifecycleState — thirteen lifecycle states
# ---------------------------------------------------------------------------
class KnowledgeLifecycleState(str, Enum):
    """
    All possible lifecycle states for a knowledge session.

    Lifecycle progression (happy path)::

        CREATED → INITIALIZING → COLLECTING → VALIDATING → READY
                → CAPTURING → INDEXING_PENDING → PUBLISHED
                → COMPLETED → ARCHIVED

    Pause / resume::

        READY | PUBLISHED → PAUSED → RESUMING → CAPTURING | READY

    Failure::

        any non-terminal state → FAILED → ARCHIVED
    """
    CREATED          = "created"
    INITIALIZING     = "initializing"
    COLLECTING       = "collecting"
    VALIDATING       = "validating"
    READY            = "ready"
    CAPTURING        = "capturing"
    INDEXING_PENDING = "indexing_pending"
    PUBLISHED        = "published"
    PAUSED           = "paused"
    RESUMING         = "resuming"
    COMPLETED        = "completed"
    FAILED           = "failed"
    ARCHIVED         = "archived"


# ---------------------------------------------------------------------------
# KnowledgeType
# ---------------------------------------------------------------------------
class KnowledgeType(str, Enum):
    """Classification of the knowledge artifact being tracked."""
    FACT        = "fact"
    RULE        = "rule"
    CONCEPT     = "concept"
    PATTERN     = "pattern"
    STRATEGY    = "strategy"
    INSIGHT     = "insight"
    SIGNAL      = "signal"
    POLICY      = "policy"
    PROCEDURE   = "procedure"
    REFERENCE   = "reference"
    ANNOTATION  = "annotation"
    CUSTOM      = "custom"


# ---------------------------------------------------------------------------
# KnowledgeScope
# ---------------------------------------------------------------------------
class KnowledgeScope(str, Enum):
    """Institutional scope of the knowledge session."""
    GLOBAL      = "global"
    PLATFORM    = "platform"
    DOMAIN      = "domain"
    SUBSYSTEM   = "subsystem"
    SESSION     = "session"


# ---------------------------------------------------------------------------
# KnowledgeSource
# ---------------------------------------------------------------------------
class KnowledgeSource(str, Enum):
    """Provenance / origin classification of the knowledge artifact."""
    MARKET_DATA  = "market_data"
    EXECUTION    = "execution"
    ANALYTICS    = "analytics"
    GOVERNANCE   = "governance"
    EXTERNAL     = "external"
    INTERNAL     = "internal"
    DERIVED      = "derived"
    MANUAL       = "manual"
    AUTOMATED    = "automated"
    UNKNOWN      = "unknown"


# ---------------------------------------------------------------------------
# KnowledgeEventType
# ---------------------------------------------------------------------------
class KnowledgeEventType(str, Enum):
    """Domain event types emitted by the knowledge lifecycle subsystem."""
    KNOWLEDGE_CREATED         = "knowledge.created"
    KNOWLEDGE_INITIALIZED     = "knowledge.initialized"
    KNOWLEDGE_VALIDATED       = "knowledge.validated"
    KNOWLEDGE_CAPTURE_STARTED = "knowledge.capture_started"
    KNOWLEDGE_PUBLISHED       = "knowledge.published"
    KNOWLEDGE_PAUSED          = "knowledge.paused"
    KNOWLEDGE_RESUMED         = "knowledge.resumed"
    KNOWLEDGE_COMPLETED       = "knowledge.completed"
    KNOWLEDGE_FAILED          = "knowledge.failed"
    KNOWLEDGE_ARCHIVED        = "knowledge.archived"


# ---------------------------------------------------------------------------
# State machine
# ---------------------------------------------------------------------------

ACTIVE_STATES: FrozenSet[KnowledgeLifecycleState] = frozenset({
    KnowledgeLifecycleState.CREATED,
    KnowledgeLifecycleState.INITIALIZING,
    KnowledgeLifecycleState.COLLECTING,
    KnowledgeLifecycleState.VALIDATING,
    KnowledgeLifecycleState.READY,
    KnowledgeLifecycleState.CAPTURING,
    KnowledgeLifecycleState.INDEXING_PENDING,
    KnowledgeLifecycleState.PUBLISHED,
    KnowledgeLifecycleState.PAUSED,
    KnowledgeLifecycleState.RESUMING,
})

TERMINAL_STATES: FrozenSet[KnowledgeLifecycleState] = frozenset({
    KnowledgeLifecycleState.COMPLETED,
    KnowledgeLifecycleState.FAILED,
    KnowledgeLifecycleState.ARCHIVED,
})

IMMUTABLE_STATES: FrozenSet[KnowledgeLifecycleState] = frozenset({
    KnowledgeLifecycleState.ARCHIVED,
})

SUCCESS_STATES: FrozenSet[KnowledgeLifecycleState] = frozenset({
    KnowledgeLifecycleState.PUBLISHED,
    KnowledgeLifecycleState.COMPLETED,
})

#: Strict valid transitions for the knowledge lifecycle state machine.
VALID_TRANSITIONS: Dict[KnowledgeLifecycleState, FrozenSet[KnowledgeLifecycleState]] = {
    KnowledgeLifecycleState.CREATED: frozenset({
        KnowledgeLifecycleState.INITIALIZING,
    }),
    KnowledgeLifecycleState.INITIALIZING: frozenset({
        KnowledgeLifecycleState.COLLECTING,
        KnowledgeLifecycleState.FAILED,
    }),
    KnowledgeLifecycleState.COLLECTING: frozenset({
        KnowledgeLifecycleState.VALIDATING,
        KnowledgeLifecycleState.FAILED,
    }),
    KnowledgeLifecycleState.VALIDATING: frozenset({
        KnowledgeLifecycleState.READY,
        KnowledgeLifecycleState.FAILED,
    }),
    KnowledgeLifecycleState.READY: frozenset({
        KnowledgeLifecycleState.CAPTURING,
        KnowledgeLifecycleState.PAUSED,
        KnowledgeLifecycleState.FAILED,
    }),
    KnowledgeLifecycleState.CAPTURING: frozenset({
        KnowledgeLifecycleState.INDEXING_PENDING,
        KnowledgeLifecycleState.FAILED,
    }),
    KnowledgeLifecycleState.INDEXING_PENDING: frozenset({
        KnowledgeLifecycleState.PUBLISHED,
        KnowledgeLifecycleState.FAILED,
    }),
    KnowledgeLifecycleState.PUBLISHED: frozenset({
        KnowledgeLifecycleState.PAUSED,
        KnowledgeLifecycleState.COMPLETED,
        KnowledgeLifecycleState.FAILED,
    }),
    KnowledgeLifecycleState.PAUSED: frozenset({
        KnowledgeLifecycleState.RESUMING,
        KnowledgeLifecycleState.ARCHIVED,
        KnowledgeLifecycleState.FAILED,
    }),
    KnowledgeLifecycleState.RESUMING: frozenset({
        KnowledgeLifecycleState.CAPTURING,
        KnowledgeLifecycleState.READY,
        KnowledgeLifecycleState.FAILED,
    }),
    KnowledgeLifecycleState.COMPLETED: frozenset({
        KnowledgeLifecycleState.ARCHIVED,
    }),
    KnowledgeLifecycleState.FAILED: frozenset({
        KnowledgeLifecycleState.ARCHIVED,
    }),
    KnowledgeLifecycleState.ARCHIVED: frozenset(),
}
