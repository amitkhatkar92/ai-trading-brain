"""
constants.py — iios.supervisor.integration
-------------------------------------------
Enumerations, named constants, and defaults for the AI Supervisor Integration.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 6
"""
from __future__ import annotations

from enum import Enum

# ---------------------------------------------------------------------------
# Version / identity
# ---------------------------------------------------------------------------

VERSION                  = "1.0.0"
INTEGRATION_SYSTEM_ID    = "iios.supervisor.integration"
ACTOR_SYSTEM             = "system"
ACTOR_OPERATOR           = "operator"

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

DEFAULT_MAX_HISTORY       = 500
DEFAULT_MAX_REQUESTS      = 10_000
DEFAULT_MAX_SESSIONS      = 1_000

# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class IntegrationStatus(str, Enum):
    """Operational status of the AI Supervisor Integration engine."""
    IDLE         = "idle"
    INITIALIZING = "initializing"
    RUNNING      = "running"
    STOPPING     = "stopping"
    STOPPED      = "stopped"
    FAILED       = "failed"
    DEGRADED     = "degraded"


class IntegrationEventType(str, Enum):
    """Domain event types emitted by the integration layer."""
    INTEGRATION_INITIALIZED = "integration.initialized"
    INTEGRATION_STARTED     = "integration.started"
    INTEGRATION_VALIDATED   = "integration.validated"
    INTEGRATION_EXECUTED    = "integration.executed"
    SNAPSHOT_PUBLISHED      = "integration.snapshot_published"
    INTEGRATION_COMPLETED   = "integration.completed"
    INTEGRATION_FAILED      = "integration.failed"
    INTEGRATION_STOPPED     = "integration.stopped"


class IntegrationValidationCode(str, Enum):
    """Identifiers for the 7 integration validation checks."""
    INTEGRATION_CONSISTENCY = "integration_consistency"
    COMPONENT_AVAILABILITY  = "component_availability"
    WORKFLOW_CONSISTENCY    = "workflow_consistency"
    LIFECYCLE_INTEGRITY     = "lifecycle_integrity"
    GOVERNANCE_INTEGRITY    = "governance_integrity"
    SNAPSHOT_INTEGRITY      = "snapshot_integrity"
    RESPONSE_COMPLETENESS   = "response_completeness"


class ComponentType(str, Enum):
    """The five component categories managed by the integration layer."""
    LIFECYCLE  = "lifecycle"   # M1 — SupervisorLifecycle
    ENGINE     = "engine"      # M2 — SupervisorEngine
    POLICY     = "policy"      # M3 — AIGovernancePolicyEngine
    GOVERNANCE = "governance"  # M4 — AutonomousGovernanceEngine
    SNAPSHOT   = "snapshot"    # M5 — SupervisorSnapshotFactory


class WorkflowPhase(str, Enum):
    """Phases of the integration workflow pipeline."""
    RECEIVE          = "receive"
    VALIDATE         = "validate"
    LIFECYCLE        = "lifecycle"
    ENGINE           = "engine"
    POLICY           = "policy"
    GOVERNANCE       = "governance"
    SNAPSHOT         = "snapshot"
    VALIDATE_SNAPSHOT = "validate_snapshot"
    COMPLETE         = "complete"


class IntegrationMode(str, Enum):
    """Execution mode for an integration request."""
    FULL              = "full"
    GOVERNANCE_ONLY   = "governance_only"
    SNAPSHOT_ONLY     = "snapshot_only"
    HEALTH_ONLY       = "health_only"


class IntegrationHealthStatus(str, Enum):
    """Overall health status of the integration layer."""
    HEALTHY   = "healthy"
    DEGRADED  = "degraded"
    CRITICAL  = "critical"
    UNKNOWN   = "unknown"
