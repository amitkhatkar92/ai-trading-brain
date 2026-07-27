"""
constants.py — iios.ai.foundation.lifecycle
============================================
Enumerations, state machine, identifiers, and numeric defaults for the
AI Foundation Lifecycle subsystem.

A1 AI Foundation — Phase 3, Module 1
"""
from __future__ import annotations

from enum import Enum
from typing import Dict, FrozenSet

# ---------------------------------------------------------------------------
# System identifiers
# ---------------------------------------------------------------------------
LIFECYCLE_SYSTEM_ID: str = "iios:ai:foundation:lifecycle"
REGISTRY_SYSTEM_ID:  str = "iios:ai:foundation:lifecycle:registry"
FACTORY_SYSTEM_ID:   str = "iios:ai:foundation:lifecycle:factory"

# ---------------------------------------------------------------------------
# Versioning
# ---------------------------------------------------------------------------
VERSION:        str = "1.0.0"
SCHEMA_VERSION: str = "1.0"

# ---------------------------------------------------------------------------
# Default capacity limits
# ---------------------------------------------------------------------------
DEFAULT_MAX_SESSIONS:    int = 1_000
DEFAULT_MAX_ARCHIVED:    int = 5_000
DEFAULT_MAX_HISTORY:     int = 500
DEFAULT_MAX_TRANSITIONS: int = 10_000
DEFAULT_MAX_EVENTS:      int = 200

# ---------------------------------------------------------------------------
# Actor identifiers
# ---------------------------------------------------------------------------
ACTOR_LIFECYCLE: str = "iios:ai:foundation:lifecycle"
ACTOR_ENGINE:    str = "iios:ai:foundation:engine"
ACTOR_GATEWAY:   str = "iios:ai:foundation:gateway"
ACTOR_OPERATOR:  str = "operator"
ACTOR_SYSTEM:    str = "iios:ai:system"


# ---------------------------------------------------------------------------
# AILifecycleState — standard operational states for ALL AI Platform modules
#
# This enum is the canonical state type used by AILifecycleAwareMixin and
# inherited/reused by every A2–A10 module.
# ---------------------------------------------------------------------------
class AILifecycleState(str, Enum):
    """
    Standard operational lifecycle states for all AI Platform modules.

    Lifecycle progression (happy path)::

        CREATED → INITIALIZED → RUNNING → STOPPING → STOPPED

    Pause / resume::

        RUNNING → PAUSED → RUNNING

    Failure and recovery::

        any non-terminal state → FAILED
        FAILED → INITIALIZED          (restart path)
    """
    CREATED     = "created"
    INITIALIZED = "initialized"
    RUNNING     = "running"
    PAUSED      = "paused"
    STOPPING    = "stopping"
    STOPPED     = "stopped"
    FAILED      = "failed"


# ---------------------------------------------------------------------------
# State machine — valid transitions
# ---------------------------------------------------------------------------
TERMINAL_STATES: FrozenSet[AILifecycleState] = frozenset({
    AILifecycleState.STOPPED,
    AILifecycleState.FAILED,
})

ACTIVE_STATES: FrozenSet[AILifecycleState] = frozenset({
    AILifecycleState.RUNNING,
    AILifecycleState.PAUSED,
})

VALID_TRANSITIONS: Dict[AILifecycleState, FrozenSet[AILifecycleState]] = {
    AILifecycleState.CREATED: frozenset({
        AILifecycleState.INITIALIZED,
        AILifecycleState.FAILED,
    }),
    AILifecycleState.INITIALIZED: frozenset({
        AILifecycleState.RUNNING,
        AILifecycleState.FAILED,
    }),
    AILifecycleState.RUNNING: frozenset({
        AILifecycleState.PAUSED,
        AILifecycleState.STOPPING,
        AILifecycleState.FAILED,
    }),
    AILifecycleState.PAUSED: frozenset({
        AILifecycleState.RUNNING,
        AILifecycleState.STOPPING,
        AILifecycleState.FAILED,
    }),
    AILifecycleState.STOPPING: frozenset({
        AILifecycleState.STOPPED,
        AILifecycleState.FAILED,
    }),
    AILifecycleState.STOPPED: frozenset({
        AILifecycleState.INITIALIZED,   # allow restart
    }),
    AILifecycleState.FAILED: frozenset({
        AILifecycleState.INITIALIZED,   # allow recovery
    }),
}


# ---------------------------------------------------------------------------
# Lifecycle event types
# ---------------------------------------------------------------------------
class AILifecycleEventType(str, Enum):
    """Structured event types emitted by the AI lifecycle state machine."""
    MODULE_INITIALIZED = "module_initialized"
    MODULE_STARTED     = "module_started"
    MODULE_PAUSED      = "module_paused"
    MODULE_RESUMED     = "module_resumed"
    MODULE_STOPPING    = "module_stopping"
    MODULE_STOPPED     = "module_stopped"
    MODULE_FAILED      = "module_failed"
    MODULE_RESTARTED   = "module_restarted"
    HEALTH_CHANGED     = "health_changed"
    HEARTBEAT          = "heartbeat"
