"""
constants.py — iios.decision.integration
=========================================
Shared constants, identifiers, and enumerations for the Decision Integration
subsystem (C9 M6).

C9 Decision Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

from enum import Enum, IntEnum

# ---------------------------------------------------------------------------
# System identity
# ---------------------------------------------------------------------------

INTEGRATION_SYSTEM_ID: str = "iios:decision:integration"
VERSION:               str = "1.0.0"
SCHEMA_VERSION:        str = "1.0"

# ---------------------------------------------------------------------------
# Source system identifiers (for cross-module references)
# ---------------------------------------------------------------------------

SOURCE_M1: str = "iios:decision:lifecycle"
SOURCE_M2: str = "iios:decision:engine"
SOURCE_M3: str = "iios:decision:policies"
SOURCE_M4: str = "iios:decision:optimization"
SOURCE_M5: str = "iios:decision:snapshot"

# ---------------------------------------------------------------------------
# Actor identifiers
# ---------------------------------------------------------------------------

ACTOR_INTEGRATION: str = "integration"
ACTOR_ENGINE:      str = "integration_engine"
ACTOR_MANAGER:     str = "integration_manager"
ACTOR_COMPONENT:   str = "component_registry"
ACTOR_VALIDATOR:   str = "integration_validator"
ACTOR_HEALTH:      str = "health_monitor"
ACTOR_OPERATOR:    str = "operator"
ACTOR_SYSTEM:      str = "system"

# ---------------------------------------------------------------------------
# Default capacity / timing
# ---------------------------------------------------------------------------

DEFAULT_MAX_IN_FLIGHT:     int   = 1_000    # simultaneous requests
DEFAULT_MAX_HISTORY:       int   = 5_000    # completed requests kept in memory
DEFAULT_MAX_EVENTS:        int   = 10_000   # integration events in history
DEFAULT_DEADLINE_S:        float = 30.0     # per-request timeout (seconds)
DEFAULT_HEALTH_INTERVAL_S: float = 60.0     # health-check polling interval
EMA_ALPHA:                 float = 0.1      # EMA weight for latency smoothing
THROUGHPUT_WINDOW_S:       float = 60.0     # window for throughput calculation

# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class IntegrationStatus(str, Enum):
    """Outcome status of a single integration request."""
    PENDING  = "pending"
    RUNNING  = "running"
    SUCCESS  = "success"
    FAILED   = "failed"
    TIMEOUT  = "timeout"
    PARTIAL  = "partial"


class ComponentType(str, Enum):
    """Identifiers for each integrated decision subsystem component."""
    LIFECYCLE             = "lifecycle"
    ENGINE                = "engine"
    POLICY_FRAMEWORK      = "policy_framework"
    OPTIMIZATION_FRAMEWORK = "optimization_framework"
    SNAPSHOT              = "snapshot"


class IntegrationPhase(str, Enum):
    """Phases of the integration workflow."""
    IDLE         = "idle"
    VALIDATING   = "validating"
    INITIALIZING = "initializing"
    LIFECYCLE    = "lifecycle"
    ENGINE       = "engine"
    POLICY       = "policy"
    OPTIMIZATION = "optimization"
    SNAPSHOT     = "snapshot"
    COMPLETING   = "completing"


class IntegrationEventType(str, Enum):
    """Types of events emitted by the integration engine."""
    INITIALIZED             = "initialized"
    STARTED                 = "started"
    STOPPED                 = "stopped"
    RESTARTED               = "restarted"
    REQUEST_SUBMITTED       = "request_submitted"
    REQUEST_COMPLETED       = "request_completed"
    REQUEST_FAILED          = "request_failed"
    SNAPSHOT_PUBLISHED      = "snapshot_published"
    HEALTH_CHANGED          = "health_changed"


class IntegrationValidationCode(str, Enum):
    """Validation check identifiers for integration requests."""
    REQUEST_CONSISTENCY    = "request_consistency"
    CONTEXT_CONSISTENCY    = "context_consistency"
    COMPONENT_READINESS    = "component_readiness"
    SUBSYSTEM_CONSISTENCY  = "subsystem_consistency"
    WORKFLOW_CONSISTENCY   = "workflow_consistency"
    DEADLINE_CONSISTENCY   = "deadline_consistency"


class ComponentHealth(str, Enum):
    """Health level of an individual integrated component."""
    HEALTHY     = "healthy"
    DEGRADED    = "degraded"
    CRITICAL    = "critical"
    UNKNOWN     = "unknown"
    UNAVAILABLE = "unavailable"


class OverallHealth(str, Enum):
    """Aggregate health of the entire integration subsystem."""
    HEALTHY     = "healthy"
    DEGRADED    = "degraded"
    CRITICAL    = "critical"
    UNAVAILABLE = "unavailable"
