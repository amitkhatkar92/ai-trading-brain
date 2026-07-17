"""iios/execution/monitoring/lifecycle/constants.py
==================================================
Constants, enumerations, and state machine for the IIOS
Execution Monitoring Lifecycle.

C6 Execution Intelligence — Phase 6, Module 1
"""
from __future__ import annotations

from enum import Enum

# ── System identifiers ────────────────────────────────────────────────────────

LIFECYCLE_SYSTEM_ID = "iios:execution:monitoring:lifecycle"
REGISTRY_SYSTEM_ID  = "iios:execution:monitoring:lifecycle:registry"
FACTORY_SYSTEM_ID   = "iios:execution:monitoring:lifecycle:factory"
VALIDATOR_SYSTEM_ID = "iios:execution:monitoring:lifecycle:validator"

VERSION        = "1.0.0"
SCHEMA_VERSION = "1.0"

# ── Defaults ──────────────────────────────────────────────────────────────────

DEFAULT_MAX_SESSIONS = 5_000
DEFAULT_MAX_HISTORY  = 1_000

# ── Actor labels ──────────────────────────────────────────────────────────────

ACTOR_SYSTEM    = "iios:system"
ACTOR_LIFECYCLE = "iios:execution:monitoring:lifecycle"
ACTOR_REGISTRY  = "iios:execution:monitoring:lifecycle:registry"
ACTOR_FACTORY   = "iios:execution:monitoring:lifecycle:factory"


# ── Monitoring lifecycle states ───────────────────────────────────────────────

class MonitoringState(str, Enum):
    """All valid lifecycle states for an execution monitoring session."""
    CREATED      = "CREATED"
    INITIALIZING = "INITIALIZING"
    STARTING     = "STARTING"
    ACTIVE       = "ACTIVE"
    PAUSED       = "PAUSED"
    RESUMING     = "RESUMING"
    STOPPING     = "STOPPING"
    STOPPED      = "STOPPED"
    FAILED       = "FAILED"
    ARCHIVED     = "ARCHIVED"


# ── Monitoring event types ────────────────────────────────────────────────────

class MonitoringEventType(str, Enum):
    """Domain events emitted by the monitoring lifecycle."""
    MONITORING_CREATED     = "MONITORING_CREATED"
    MONITORING_STARTED     = "MONITORING_STARTED"
    MONITORING_PAUSED      = "MONITORING_PAUSED"
    MONITORING_RESUMED     = "MONITORING_RESUMED"
    MONITORING_STOPPED     = "MONITORING_STOPPED"
    MONITORING_FAILED      = "MONITORING_FAILED"
    MONITORING_ARCHIVED    = "MONITORING_ARCHIVED"
    MONITORING_INITIALIZED = "MONITORING_INITIALIZED"


# ── State machine ─────────────────────────────────────────────────────────────

VALID_TRANSITIONS: dict = {
    MonitoringState.CREATED: frozenset({
        MonitoringState.INITIALIZING,
        MonitoringState.FAILED,
        MonitoringState.ARCHIVED,
    }),
    MonitoringState.INITIALIZING: frozenset({
        MonitoringState.STARTING,
        MonitoringState.FAILED,
        MonitoringState.ARCHIVED,
    }),
    MonitoringState.STARTING: frozenset({
        MonitoringState.ACTIVE,
        MonitoringState.FAILED,
        MonitoringState.ARCHIVED,
    }),
    MonitoringState.ACTIVE: frozenset({
        MonitoringState.PAUSED,
        MonitoringState.STOPPING,
        MonitoringState.FAILED,
    }),
    MonitoringState.PAUSED: frozenset({
        MonitoringState.RESUMING,
        MonitoringState.STOPPING,
        MonitoringState.FAILED,
    }),
    MonitoringState.RESUMING: frozenset({
        MonitoringState.ACTIVE,
        MonitoringState.STOPPING,
        MonitoringState.FAILED,
    }),
    MonitoringState.STOPPING: frozenset({
        MonitoringState.STOPPED,
        MonitoringState.FAILED,
    }),
    MonitoringState.STOPPED: frozenset({
        MonitoringState.ARCHIVED,
    }),
    MonitoringState.FAILED: frozenset({
        MonitoringState.ARCHIVED,
    }),
    MonitoringState.ARCHIVED: frozenset(),
}

# ── State classification sets ─────────────────────────────────────────────────

TERMINAL_STATES: frozenset = frozenset({
    MonitoringState.STOPPED,
    MonitoringState.FAILED,
    MonitoringState.ARCHIVED,
})

ACTIVE_STATES: frozenset = frozenset({
    MonitoringState.INITIALIZING,
    MonitoringState.STARTING,
    MonitoringState.ACTIVE,
    MonitoringState.PAUSED,
    MonitoringState.RESUMING,
    MonitoringState.STOPPING,
})

RUNNING_STATES: frozenset = frozenset({
    MonitoringState.ACTIVE,
    MonitoringState.PAUSED,
    MonitoringState.RESUMING,
})

FAILURE_STATES: frozenset = frozenset({
    MonitoringState.FAILED,
})

SUCCESS_STATES: frozenset = frozenset({
    MonitoringState.STOPPED,
    MonitoringState.ARCHIVED,
})

ENDED_STATES: frozenset = frozenset({
    MonitoringState.STOPPED,
    MonitoringState.FAILED,
    MonitoringState.ARCHIVED,
})
