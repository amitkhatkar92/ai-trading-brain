"""
constants.py — iios.portfolio.integration
==========================================
Enumerations, state machines, identifiers, and defaults for the
Portfolio Integration subsystem.

C10 Portfolio Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

from enum import Enum, IntEnum
from typing import Dict, FrozenSet

# ---------------------------------------------------------------------------
# System identifiers
# ---------------------------------------------------------------------------
INTEGRATION_SYSTEM_ID: str  = "iios:portfolio:integration"
ACTOR_INTEGRATION:     str  = "iios:portfolio:integration:engine"
ACTOR_MANAGER:         str  = "iios:portfolio:integration:manager"
ACTOR_VALIDATOR:       str  = "iios:portfolio:integration:validator"
VERSION:               str  = "1.0.0"

# ---------------------------------------------------------------------------
# Default limits
# ---------------------------------------------------------------------------
DEFAULT_MAX_HISTORY:  int = 1_000
DEFAULT_MAX_REQUESTS: int = 10_000
DEFAULT_MAX_SESSIONS: int = 5_000


# ---------------------------------------------------------------------------
# IntegrationState — lifecycle state of the integration engine
# ---------------------------------------------------------------------------
class IntegrationState(str, Enum):
    """Lifecycle state of the PortfolioIntegrationEngine itself."""
    PENDING      = "pending"
    INITIALIZING = "initializing"
    RUNNING      = "running"
    STOPPING     = "stopping"
    STOPPED      = "stopped"
    ERROR        = "error"


# ---------------------------------------------------------------------------
# IntegrationServiceType — nine supported portfolio services
# ---------------------------------------------------------------------------
class IntegrationServiceType(str, Enum):
    """Classification of the service requested via submit()."""
    PORTFOLIO_CREATION       = "portfolio_creation"
    PORTFOLIO_UPDATE         = "portfolio_update"
    PORTFOLIO_VALIDATION     = "portfolio_validation"
    PORTFOLIO_REVIEW         = "portfolio_review"
    PORTFOLIO_OPTIMIZATION   = "portfolio_optimization"
    PORTFOLIO_REBALANCING    = "portfolio_rebalancing"
    PORTFOLIO_SYNCHRONIZATION = "portfolio_synchronization"
    PORTFOLIO_QUERY          = "portfolio_query"
    PORTFOLIO_REPORTING      = "portfolio_reporting"


# ---------------------------------------------------------------------------
# WorkflowStage — stages within the integration workflow
# ---------------------------------------------------------------------------
class WorkflowStage(str, Enum):
    REQUEST_RECEIVED        = "request_received"
    CONTEXT_VALIDATED       = "context_validated"
    SESSION_INITIALIZED     = "session_initialized"
    LIFECYCLE_COORDINATED   = "lifecycle_coordinated"
    ENGINE_INVOKED          = "engine_invoked"
    POLICY_COORDINATED      = "policy_coordinated"
    OPTIMIZATION_COORDINATED = "optimization_coordinated"
    SNAPSHOT_PUBLISHED      = "snapshot_published"
    COMPLETED               = "completed"
    FAILED                  = "failed"


# ---------------------------------------------------------------------------
# ResponseStatus
# ---------------------------------------------------------------------------
class ResponseStatus(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"


# ---------------------------------------------------------------------------
# ComponentType — the five integrated subsystems
# ---------------------------------------------------------------------------
class ComponentType(str, Enum):
    LIFECYCLE    = "lifecycle"
    ENGINE       = "engine"
    POLICY       = "policy"
    OPTIMIZATION = "optimization"
    SNAPSHOT     = "snapshot"


# ---------------------------------------------------------------------------
# IntegrationEventType — eight lifecycle events
# ---------------------------------------------------------------------------
class IntegrationEventType(str, Enum):
    PORTFOLIO_INITIALIZED       = "portfolio_initialized"
    PORTFOLIO_STARTED           = "portfolio_started"
    PORTFOLIO_COMPLETED         = "portfolio_completed"
    PORTFOLIO_STOPPED           = "portfolio_stopped"
    PORTFOLIO_RESTARTED         = "portfolio_restarted"
    PORTFOLIO_VALIDATED         = "portfolio_validated"
    PORTFOLIO_HEALTH_CHANGED    = "portfolio_health_changed"
    PORTFOLIO_SNAPSHOT_PUBLISHED = "portfolio_snapshot_published"


# ---------------------------------------------------------------------------
# IntegrationValidationCode — seven validation checks
# ---------------------------------------------------------------------------
class IntegrationValidationCode(str, Enum):
    LIFECYCLE_CONSISTENCY    = "lifecycle_consistency"
    ENGINE_CONSISTENCY       = "engine_consistency"
    POLICY_CONSISTENCY       = "policy_consistency"
    OPTIMIZATION_CONSISTENCY = "optimization_consistency"
    SNAPSHOT_CONSISTENCY     = "snapshot_consistency"
    INTEGRATION_CONSISTENCY  = "integration_consistency"
    SUBSYSTEM_READINESS      = "subsystem_readiness"


# ---------------------------------------------------------------------------
# IntegrationHealth
# ---------------------------------------------------------------------------
class IntegrationHealth(str, Enum):
    HEALTHY  = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    UNKNOWN  = "unknown"


# ---------------------------------------------------------------------------
# Service-type → workflow flag sets
# ---------------------------------------------------------------------------
#: Service types that require a new lifecycle session.
CREATION_SERVICES: FrozenSet[IntegrationServiceType] = frozenset({
    IntegrationServiceType.PORTFOLIO_CREATION,
    IntegrationServiceType.PORTFOLIO_UPDATE,
    IntegrationServiceType.PORTFOLIO_REBALANCING,
    IntegrationServiceType.PORTFOLIO_SYNCHRONIZATION,
    IntegrationServiceType.PORTFOLIO_OPTIMIZATION,
})

#: Service types that are read-only (no state mutation).
READONLY_SERVICES: FrozenSet[IntegrationServiceType] = frozenset({
    IntegrationServiceType.PORTFOLIO_QUERY,
    IntegrationServiceType.PORTFOLIO_REVIEW,
    IntegrationServiceType.PORTFOLIO_REPORTING,
    IntegrationServiceType.PORTFOLIO_VALIDATION,
})
