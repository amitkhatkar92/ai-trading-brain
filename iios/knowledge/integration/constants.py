"""
constants.py — iios.knowledge.integration
------------------------------------------
Constants, enums, and system identifiers for the Knowledge Integration module.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

from enum import Enum


# ════════════════════════════════════════════════════════════════════════
# Enums
# ════════════════════════════════════════════════════════════════════════


class IntegrationState(str, Enum):
    """Lifecycle state of the KnowledgeIntegrationEngine."""
    STOPPED      = "stopped"
    INITIALIZING = "initializing"
    STARTING     = "starting"
    RUNNING      = "running"
    STOPPING     = "stopping"
    RESTARTING   = "restarting"
    DEGRADED     = "degraded"
    ERROR        = "error"


class IntegrationEventType(str, Enum):
    """Events emitted by the Knowledge Integration subsystem."""
    INTEGRATION_INITIALIZED = "integration_initialized"
    INTEGRATION_STARTED     = "integration_started"
    INTEGRATION_VALIDATED   = "integration_validated"
    INTEGRATION_EXECUTED    = "integration_executed"
    SNAPSHOT_PUBLISHED      = "snapshot_published"
    INTEGRATION_COMPLETED   = "integration_completed"
    INTEGRATION_FAILED      = "integration_failed"
    INTEGRATION_STOPPED     = "integration_stopped"


class IntegrationPhase(str, Enum):
    """Phases executed during the integration workflow."""
    RECEIVE      = "receive"
    VALIDATE     = "validate"
    LIFECYCLE    = "lifecycle"
    ENGINE       = "engine"
    GOVERNANCE   = "governance"
    INTELLIGENCE = "intelligence"
    SNAPSHOT     = "snapshot"
    VERIFY       = "verify"
    RESPOND      = "respond"


class ComponentStatus(str, Enum):
    """Availability status of an integrated subsystem component."""
    AVAILABLE   = "available"
    UNAVAILABLE = "unavailable"
    DEGRADED    = "degraded"
    UNKNOWN     = "unknown"


class IntegrationValidationCode(str, Enum):
    """Validation check identifiers for integration validation."""
    INTEGRATION_CONSISTENCY = "integration_consistency"
    COMPONENT_AVAILABILITY  = "component_availability"
    WORKFLOW_CONSISTENCY    = "workflow_consistency"
    LIFECYCLE_INTEGRITY     = "lifecycle_integrity"
    KNOWLEDGE_INTEGRITY     = "knowledge_integrity"
    SNAPSHOT_INTEGRITY      = "snapshot_integrity"
    RESPONSE_COMPLETENESS   = "response_completeness"


class IntegrationRequestType(str, Enum):
    """Type of integration request."""
    FULL_INTEGRATION = "full_integration"
    QUERY            = "query"
    SEARCH           = "search"
    RETRIEVE         = "retrieve"
    VALIDATE         = "validate"
    SNAPSHOT         = "snapshot"
    HEALTH           = "health"


# ════════════════════════════════════════════════════════════════════════
# System identifiers
# ════════════════════════════════════════════════════════════════════════

INTEGRATION_SYSTEM_ID = "iios:knowledge:integration"
VERSION               = "1.0.0"
SCHEMA_VERSION        = "1.0"
FRAMEWORK_VERSION     = "1.0.0"
BUILD_VERSION         = "1.0.0-stable"

ACTOR_INTEGRATION = "iios:knowledge:integration"
ACTOR_MANAGER     = "iios:knowledge:integration:manager"
ACTOR_SYSTEM      = "iios:system"

# ════════════════════════════════════════════════════════════════════════
# Operational defaults
# ════════════════════════════════════════════════════════════════════════

DEFAULT_MAX_HISTORY    = 1_000
DEFAULT_MAX_REQUESTS   = 10_000
DEFAULT_TIMEOUT_MS     = 30_000
DEFAULT_MAX_CONCURRENT = 10

# Component names (aligned with M1-M5)
COMPONENT_LIFECYCLE    = "knowledge_lifecycle"
COMPONENT_ENGINE       = "knowledge_engine"
COMPONENT_GOVERNANCE   = "knowledge_governance"
COMPONENT_INTELLIGENCE = "knowledge_intelligence"
COMPONENT_SNAPSHOT     = "knowledge_snapshot"
