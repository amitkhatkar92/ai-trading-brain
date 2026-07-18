"""
iios/execution/recovery/integration/constants.py
================================================
Constants and enumerations for the Execution Recovery Integration (C7 M6).

C7 Execution Recovery & Resilience — Phase 1, Module 6
"""
from __future__ import annotations

from enum import Enum

# ── System identifiers ────────────────────────────────────────────────────────

SYSTEM_ID   = "iios:execution:recovery:integration"
ENGINE_ID   = "iios:execution:recovery:integration:engine"
MANAGER_ID  = "iios:execution:recovery:integration:manager"
REGISTRY_ID = "iios:execution:recovery:integration:registry"
FACTORY_ID  = "iios:execution:recovery:integration:factory"

# ── Versioning ────────────────────────────────────────────────────────────────

VERSION        = "1.0.0"
SCHEMA_VERSION = "1.0"

# ── Default limits ────────────────────────────────────────────────────────────

DEFAULT_MAX_ACTIVE_REQUESTS = 200
DEFAULT_MAX_HISTORY         = 2_000

# ── Actor identifiers ─────────────────────────────────────────────────────────

ACTOR_INTEGRATION = "iios:execution:recovery:integration"
ACTOR_SYSTEM      = "iios:system"
ACTOR_OPERATOR    = "operator"

# ── Component names (for health / status reports) ─────────────────────────────

COMP_ENGINE   = "recovery_engine"       # M2
COMP_POLICY   = "policy_engine"         # M3
COMP_FAILOVER = "failover_engine"       # M4
COMP_SNAPSHOT = "snapshot_store"        # M5


# ── Integration status ────────────────────────────────────────────────────────

class IntegrationStatus(str, Enum):
    """High-level operational status of the integration engine."""

    IDLE      = "idle"
    ACTIVE    = "active"
    DEGRADED  = "degraded"
    UNHEALTHY = "unhealthy"
    STOPPED   = "stopped"
    UNKNOWN   = "unknown"


# ── Component status ──────────────────────────────────────────────────────────

class ComponentStatus(str, Enum):
    """Status of a single wired component."""

    RUNNING  = "running"
    STOPPED  = "stopped"
    DEGRADED = "degraded"
    ERROR    = "error"
    UNKNOWN  = "unknown"


# ── Integration health ────────────────────────────────────────────────────────

class IntegrationHealth(str, Enum):
    """Overall health of the integration subsystem."""

    HEALTHY   = "healthy"
    DEGRADED  = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN   = "unknown"


# ── Integration event types ───────────────────────────────────────────────────

class IntegrationEventType(str, Enum):
    """All event types emitted by the Integration subsystem."""

    RECOVERY_INITIALIZED     = "recovery_initialized"
    RECOVERY_STARTED         = "recovery_started"
    RECOVERY_COMPLETED       = "recovery_completed"
    RECOVERY_STOPPED         = "recovery_stopped"
    RECOVERY_RESTARTED       = "recovery_restarted"
    RECOVERY_VALIDATED       = "recovery_validated"
    RECOVERY_HEALTH_CHANGED  = "recovery_health_changed"
    RECOVERY_SNAPSHOT_PUBLISHED = "recovery_snapshot_published"
