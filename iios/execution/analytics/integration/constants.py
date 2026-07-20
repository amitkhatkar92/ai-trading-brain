"""
constants.py — iios.execution.analytics.integration
====================================================
Enumerations, identifiers, and numeric defaults for the
Execution Analytics Integration subsystem.

No logic.  All values are domain constants.
"""
from __future__ import annotations

from enum import Enum

# ---------------------------------------------------------------------------
# System identifiers
# ---------------------------------------------------------------------------
INTEGRATION_SYSTEM_ID: str = "iios.execution.analytics.integration"
MANAGER_SYSTEM_ID: str     = "iios.execution.analytics.integration.manager"
REGISTRY_SYSTEM_ID: str    = "iios.execution.analytics.integration.registry"
COMPONENT_REG_ID: str      = "iios.execution.analytics.integration.components"
FACTORY_SYSTEM_ID: str     = "iios.execution.analytics.integration.factory"
VALIDATOR_SYSTEM_ID: str   = "iios.execution.analytics.integration.validation"
HEALTH_SYSTEM_ID: str      = "iios.execution.analytics.integration.health"

# ---------------------------------------------------------------------------
# Actor identifiers (used in audit logs)
# ---------------------------------------------------------------------------
ACTOR_INTEGRATION: str  = "integration_engine"
ACTOR_MANAGER: str      = "integration_manager"
ACTOR_REGISTRY: str     = "integration_registry"
ACTOR_FACTORY: str      = "integration_factory"
ACTOR_SYSTEM: str       = "integration_system"

# ---------------------------------------------------------------------------
# Version
# ---------------------------------------------------------------------------
INTEGRATION_VERSION: str       = "1.0.0"
INTEGRATION_SCHEMA_VERSION: str = "1.0"

# ---------------------------------------------------------------------------
# Numeric defaults
# ---------------------------------------------------------------------------
DEFAULT_MAX_HISTORY: int        = 500
DEFAULT_MAX_REGISTRY: int       = 200
DEFAULT_MAX_SNAPSHOTS: int      = 100
DEFAULT_COMPONENT_TIMEOUT_S: float = 10.0
DEFAULT_PRIORITY: int           = 5


# ---------------------------------------------------------------------------
# ComponentType — identifies each upstream analytics component
# ---------------------------------------------------------------------------
class ComponentType(str, Enum):
    """Identifies each M1-M5 analytics component managed by the integration."""
    LIFECYCLE   = "lifecycle"     # M1 — AnalyticsLifecycle
    ENGINE      = "engine"        # M2 — ExecutionAnalyticsEngine
    PERFORMANCE = "performance"   # M3 — PerformanceAnalyticsEngine
    PREDICTIVE  = "predictive"    # M4 — PredictiveIntelligenceEngine
    SNAPSHOT    = "snapshot"      # M5 — AnalyticsSnapshotFactory / AnalyticsSnapshotStore


# ---------------------------------------------------------------------------
# IntegrationStatus — overall subsystem status
# ---------------------------------------------------------------------------
class IntegrationStatus(str, Enum):
    """Lifecycle / operational status of the integration subsystem."""
    INITIALIZING = "initializing"
    READY        = "ready"
    RUNNING      = "running"
    DEGRADED     = "degraded"
    STOPPING     = "stopping"
    STOPPED      = "stopped"
    ERROR        = "error"


# ---------------------------------------------------------------------------
# IntegrationResponseStatus — outcome of a single request
# ---------------------------------------------------------------------------
class IntegrationResponseStatus(str, Enum):
    """Per-request outcome status."""
    SUCCESS  = "success"
    PARTIAL  = "partial"   # completed but some components degraded
    FAILED   = "failed"
    REJECTED = "rejected"


# ---------------------------------------------------------------------------
# IntegrationHealthLevel — per-component and overall health
# ---------------------------------------------------------------------------
class IntegrationHealthLevel(str, Enum):
    """Health classification used per-component and for overall health."""
    HEALTHY     = "healthy"
    DEGRADED    = "degraded"
    CRITICAL    = "critical"
    UNKNOWN     = "unknown"
    NOT_STARTED = "not_started"


# ---------------------------------------------------------------------------
# IntegrationEventType — event types emitted by the integration subsystem
# ---------------------------------------------------------------------------
class IntegrationEventType(str, Enum):
    """The eight integration-layer event types."""
    ANALYTICS_INITIALIZED       = "analytics_initialized"
    ANALYTICS_STARTED           = "analytics_started"
    ANALYTICS_COMPLETED         = "analytics_completed"
    ANALYTICS_STOPPED           = "analytics_stopped"
    ANALYTICS_RESTARTED         = "analytics_restarted"
    ANALYTICS_VALIDATED         = "analytics_validated"
    ANALYTICS_HEALTH_CHANGED    = "analytics_health_changed"
    ANALYTICS_SNAPSHOT_PUBLISHED = "analytics_snapshot_published"


# ---------------------------------------------------------------------------
# IntegrationValidationCode — validation check identifiers
# ---------------------------------------------------------------------------
class IntegrationValidationCode(str, Enum):
    """Identifiers for each of the seven validation checks."""
    LIFECYCLE_CONSISTENCY   = "lifecycle_consistency"
    ENGINE_CONSISTENCY      = "engine_consistency"
    PERFORMANCE_CONSISTENCY = "performance_consistency"
    PREDICTION_CONSISTENCY  = "prediction_consistency"
    SNAPSHOT_CONSISTENCY    = "snapshot_consistency"
    INTEGRATION_CONSISTENCY = "integration_consistency"
    SUBSYSTEM_READINESS     = "subsystem_readiness"
