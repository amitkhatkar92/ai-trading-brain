"""
constants.py — iios.risk.integration
=======================================
Enumerations, identifiers, and defaults for the Risk Integration layer.

C11 Risk Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

from enum import Enum
from typing import FrozenSet, Tuple

# ---------------------------------------------------------------------------
# System identifiers
# ---------------------------------------------------------------------------
INTEGRATION_SYSTEM_ID: str = "iios:risk:integration"
MANAGER_SYSTEM_ID:     str = "iios:risk:integration:manager"
REGISTRY_SYSTEM_ID:    str = "iios:risk:integration:registry"
COMPONENT_REGISTRY_ID: str = "iios:risk:integration:components"
FACTORY_SYSTEM_ID:     str = "iios:risk:integration:factory"
HEALTH_SYSTEM_ID:      str = "iios:risk:integration:health"

# ---------------------------------------------------------------------------
# Versioning
# ---------------------------------------------------------------------------
VERSION:        str = "1.0.0"
SCHEMA_VERSION: str = "1.0"

# ---------------------------------------------------------------------------
# Actors
# ---------------------------------------------------------------------------
ACTOR_INTEGRATION_ENGINE: str = "iios:risk:integration:engine"
ACTOR_INTEGRATION_MANAGER: str = "iios:risk:integration:manager"
ACTOR_SYSTEM:              str = "iios:system"
ACTOR_OPERATOR:            str = "operator"

# ---------------------------------------------------------------------------
# Subsystem component keys (used in RiskComponentRegistry)
# ---------------------------------------------------------------------------
COMPONENT_LIFECYCLE:   str = "risk_lifecycle"
COMPONENT_ENGINE:      str = "risk_engine"
COMPONENT_POLICIES:    str = "risk_policies"
COMPONENT_ASSESSMENT:  str = "risk_assessment"
COMPONENT_SNAPSHOT:    str = "risk_snapshot"

REQUIRED_COMPONENTS: FrozenSet[str] = frozenset({
    COMPONENT_LIFECYCLE,
    COMPONENT_ENGINE,
    COMPONENT_POLICIES,
    COMPONENT_ASSESSMENT,
    COMPONENT_SNAPSHOT,
})

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
DEFAULT_MAX_REQUESTS:   int   = 50_000
DEFAULT_MAX_HISTORY:    int   = 1_000
DEFAULT_REQUEST_TIMEOUT_S: float = 60.0
DEFAULT_INIT_TIMEOUT_S:    float = 30.0


# ---------------------------------------------------------------------------
# RequestType — 10 supported integration request types
# ---------------------------------------------------------------------------
class RequestType(str, Enum):
    """Classification of supported risk integration requests."""
    PORTFOLIO_RISK_ASSESSMENT  = "portfolio_risk_assessment"
    POSITION_RISK_ASSESSMENT   = "position_risk_assessment"
    ACCOUNT_RISK_ASSESSMENT    = "account_risk_assessment"
    EXPOSURE_REVIEW            = "exposure_review"
    STRESS_TEST                = "stress_test"
    SCENARIO_ANALYSIS          = "scenario_analysis"
    RISK_FORECAST              = "risk_forecast"
    RISK_OPTIMIZATION          = "risk_optimization"
    RISK_HISTORY               = "risk_history"
    RISK_SNAPSHOT              = "risk_snapshot"


# ---------------------------------------------------------------------------
# IntegrationStatus
# ---------------------------------------------------------------------------
class IntegrationStatus(str, Enum):
    """Lifecycle status of an integration request."""
    RECEIVED    = "received"
    VALIDATING  = "validating"
    PROCESSING  = "processing"
    COMPLETED   = "completed"
    FAILED      = "failed"
    CANCELLED   = "cancelled"
    TIMEOUT     = "timeout"


# ---------------------------------------------------------------------------
# ComponentStatus
# ---------------------------------------------------------------------------
class ComponentStatus(str, Enum):
    """Availability status of a registered subsystem component."""
    AVAILABLE    = "available"
    UNAVAILABLE  = "unavailable"
    DEGRADED     = "degraded"
    INITIALIZING = "initializing"
    UNKNOWN      = "unknown"


# ---------------------------------------------------------------------------
# HealthStatus
# ---------------------------------------------------------------------------
class HealthStatus(str, Enum):
    """Overall integration engine health."""
    HEALTHY   = "healthy"
    DEGRADED  = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN   = "unknown"


# ---------------------------------------------------------------------------
# IntegrationEventType — 7 domain events
# ---------------------------------------------------------------------------
class IntegrationEventType(str, Enum):
    """Domain events emitted by the Risk Integration layer."""
    RISK_INTEGRATION_STARTED  = "risk_integration_started"
    RISK_REQUEST_RECEIVED     = "risk_request_received"
    RISK_VALIDATED            = "risk_validated"
    RISK_SNAPSHOT_PUBLISHED   = "risk_snapshot_published"
    RISK_COMPLETED            = "risk_completed"
    RISK_FAILED               = "risk_failed"
    RISK_INTEGRATION_STOPPED  = "risk_integration_stopped"


# ---------------------------------------------------------------------------
# IntegrationValidationCode
# ---------------------------------------------------------------------------
class IntegrationValidationCode(str, Enum):
    """Validation check identifiers for integration requests."""
    API_CONSISTENT          = "api_consistent"
    LIFECYCLE_CONSISTENT    = "lifecycle_consistent"
    SUBSYSTEM_AVAILABLE     = "subsystem_available"
    SNAPSHOT_INTEGRITY      = "snapshot_integrity"
    INPUT_VALID             = "input_valid"
    RESPONSE_VALID          = "response_valid"
