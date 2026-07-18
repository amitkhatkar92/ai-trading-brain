"""iios/execution/monitoring/integration/constants.py
==================================================
Constants, enumerations, and identifiers for the Execution Monitoring
Integration subsystem.

C6 Execution Intelligence — Phase 6, Module 6
"""
from __future__ import annotations

from enum import Enum

# ── System identifiers ────────────────────────────────────────────────────────

ENGINE_SYSTEM_ID   = "iios:execution:monitoring:integration:engine"
MANAGER_SYSTEM_ID  = "iios:execution:monitoring:integration:manager"
REGISTRY_SYSTEM_ID = "iios:execution:monitoring:integration:registry"
FACTORY_SYSTEM_ID  = "iios:execution:monitoring:integration:factory"

VERSION        = "1.0.0"
SCHEMA_VERSION = "1.0"

# ── Defaults ──────────────────────────────────────────────────────────────────

DEFAULT_MAX_REQUESTS = 10_000
DEFAULT_MAX_HISTORY  = 1_000
DEFAULT_MAX_SESSIONS = 5_000

# ── Actor labels ──────────────────────────────────────────────────────────────

ACTOR_INTEGRATION = "iios:execution:monitoring:integration"
ACTOR_ENGINE      = "iios:execution:monitoring:integration:engine"
ACTOR_MANAGER     = "iios:execution:monitoring:integration:manager"
ACTOR_SYSTEM      = "iios:system"


# ── Integration lifecycle states ──────────────────────────────────────────────

class IntegrationState(str, Enum):
    """Runtime state of the integration subsystem."""
    STOPPED  = "stopped"
    STARTING = "starting"
    RUNNING  = "running"
    DEGRADED = "degraded"
    STOPPING = "stopping"
    FAILED   = "failed"


# ── Component types ───────────────────────────────────────────────────────────

class ComponentType(str, Enum):
    """Registered sub-components of the integration engine."""
    LIFECYCLE      = "lifecycle"
    METRICS_ENGINE = "metrics_engine"
    ALERT_MANAGER  = "alert_manager"
    INTEGRATION    = "integration"


# ── Health status ─────────────────────────────────────────────────────────────

class HealthStatus(str, Enum):
    """Health of a component or the overall integration."""
    HEALTHY   = "healthy"
    DEGRADED  = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN   = "unknown"


# ── Domain event types ────────────────────────────────────────────────────────

class IntegrationEventType(str, Enum):
    """Domain events emitted by the integration engine."""
    MONITORING_INITIALIZED        = "monitoring_initialized"
    MONITORING_STARTED            = "monitoring_started"
    MONITORING_COMPLETED          = "monitoring_completed"
    MONITORING_STOPPED            = "monitoring_stopped"
    MONITORING_RESTARTED          = "monitoring_restarted"
    MONITORING_VALIDATED          = "monitoring_validated"
    MONITORING_HEALTH_CHANGED     = "monitoring_health_changed"
    MONITORING_SNAPSHOT_PUBLISHED = "monitoring_snapshot_published"


# ── Derived sets ──────────────────────────────────────────────────────────────

RUNNING_INTEGRATION_STATES: frozenset[IntegrationState] = frozenset(
    {IntegrationState.RUNNING, IntegrationState.DEGRADED}
)
TERMINAL_INTEGRATION_STATES: frozenset[IntegrationState] = frozenset(
    {IntegrationState.STOPPED, IntegrationState.FAILED}
)

HEALTHY_COMPONENT_STATUSES: frozenset[HealthStatus] = frozenset(
    {HealthStatus.HEALTHY}
)
UNHEALTHY_COMPONENT_STATUSES: frozenset[HealthStatus] = frozenset(
    {HealthStatus.UNHEALTHY, HealthStatus.UNKNOWN}
)
