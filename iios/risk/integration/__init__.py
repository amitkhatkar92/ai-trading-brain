"""
iios.risk.integration — C11 Risk Intelligence, Module 6
=========================================================
Enterprise façade for the complete Risk Intelligence subsystem.

All downstream callers MUST communicate through RiskIntegrationEngine.
RiskSnapshot (M5) is the ONLY published artefact.

Public API
----------
Engine (entry point)
    RiskIntegrationEngine

Request / Response
    RiskIntegrationRequest
    RiskIntegrationResponse
    RiskIntegrationContext

Validation
    RiskIntegrationValidator
    IntegrationValidationResult
    IntegrationValidationCheck

Events
    RiskIntegrationEvent
    make_integration_started
    make_request_received
    make_risk_validated
    make_snapshot_published
    make_risk_completed
    make_risk_failed
    make_integration_stopped

Observability
    RiskIntegrationSnapshot
    RiskIntegrationStatus
    RiskIntegrationStatistics
    RiskIntegrationHealthReport
    RiskIntegrationHealth
    RiskIntegrationHistory

Registry / Factory
    RiskComponentRegistry
    RiskComponentFactory
    RiskIntegrationRegistry

Manager (internal workflow coordinator — not for direct use)
    RiskIntegrationManager

Constants & Enums
    INTEGRATION_SYSTEM_ID, VERSION, SCHEMA_VERSION
    RequestType, IntegrationStatus, ComponentStatus,
    HealthStatus, IntegrationEventType, IntegrationValidationCode
    COMPONENT_LIFECYCLE, COMPONENT_ENGINE, COMPONENT_POLICIES,
    COMPONENT_ASSESSMENT, COMPONENT_SNAPSHOT
    REQUIRED_COMPONENTS
    DEFAULT_MAX_REQUESTS, DEFAULT_MAX_HISTORY

Exceptions
    RiskIntegrationError (base)
    RiskIntegrationNotRunningError
    RiskIntegrationRequestError
    RiskIntegrationValidationError
    RiskIntegrationComponentError
    RiskIntegrationSnapshotError
    RiskIntegrationWorkflowError
    RiskIntegrationCapacityError
    RiskIntegrationTimeoutError
    RiskIntegrationConfigurationError
"""
from __future__ import annotations

# ── Constants & Enums ─────────────────────────────────────────────────────────
from .constants import (
    ACTOR_INTEGRATION_ENGINE,
    ACTOR_INTEGRATION_MANAGER,
    ACTOR_OPERATOR,
    ACTOR_SYSTEM,
    COMPONENT_ASSESSMENT,
    COMPONENT_ENGINE,
    COMPONENT_LIFECYCLE,
    COMPONENT_POLICIES,
    COMPONENT_SNAPSHOT,
    COMPONENT_REGISTRY_ID,
    DEFAULT_INIT_TIMEOUT_S,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_REQUESTS,
    DEFAULT_REQUEST_TIMEOUT_S,
    FACTORY_SYSTEM_ID,
    HEALTH_SYSTEM_ID,
    INTEGRATION_SYSTEM_ID,
    MANAGER_SYSTEM_ID,
    REGISTRY_SYSTEM_ID,
    REQUIRED_COMPONENTS,
    SCHEMA_VERSION,
    VERSION,
    ComponentStatus,
    HealthStatus,
    IntegrationEventType,
    IntegrationStatus,
    IntegrationValidationCode,
    RequestType,
)

# ── Exceptions ────────────────────────────────────────────────────────────────
from .exceptions import (
    RiskIntegrationCapacityError,
    RiskIntegrationComponentError,
    RiskIntegrationConfigurationError,
    RiskIntegrationError,
    RiskIntegrationNotRunningError,
    RiskIntegrationRequestError,
    RiskIntegrationSnapshotError,
    RiskIntegrationTimeoutError,
    RiskIntegrationValidationError,
    RiskIntegrationWorkflowError,
)

# ── Request / Response / Context ──────────────────────────────────────────────
from .risk_integration_context import RiskIntegrationContext
from .risk_integration_request import RiskIntegrationRequest
from .risk_integration_response import RiskIntegrationResponse

# ── Events ────────────────────────────────────────────────────────────────────
from .risk_integration_events import (
    RiskIntegrationEvent,
    make_integration_started,
    make_integration_stopped,
    make_request_received,
    make_risk_completed,
    make_risk_failed,
    make_risk_validated,
    make_snapshot_published,
)

# ── Validation ────────────────────────────────────────────────────────────────
from .risk_integration_validation import (
    IntegrationValidationCheck,
    IntegrationValidationResult,
    RiskIntegrationValidator,
)

# ── Component Registry & Factory ──────────────────────────────────────────────
from .risk_component_registry import RiskComponentRegistry
from .risk_component_factory import RiskComponentFactory

# ── Request/Response Registry ─────────────────────────────────────────────────
from .risk_integration_registry import RiskIntegrationRegistry

# ── Statistics ────────────────────────────────────────────────────────────────
from .risk_integration_statistics import RiskIntegrationStatistics

# ── History ───────────────────────────────────────────────────────────────────
from .risk_integration_history import RiskIntegrationHistory

# ── Snapshot ─────────────────────────────────────────────────────────────────
from .risk_integration_snapshot import RiskIntegrationSnapshot

# ── Status ───────────────────────────────────────────────────────────────────
from .risk_integration_status import RiskIntegrationStatus

# ── Health ───────────────────────────────────────────────────────────────────
from .risk_integration_health import RiskIntegrationHealth, RiskIntegrationHealthReport

# ── Manager (internal) ───────────────────────────────────────────────────────
from .risk_integration_manager import RiskIntegrationManager

# ── Primary Entry Point ───────────────────────────────────────────────────────
from .risk_integration_engine import RiskIntegrationEngine

__all__ = [
    # Engine
    "RiskIntegrationEngine",
    # Request / Response / Context
    "RiskIntegrationRequest",
    "RiskIntegrationResponse",
    "RiskIntegrationContext",
    # Events
    "RiskIntegrationEvent",
    "make_integration_started",
    "make_integration_stopped",
    "make_request_received",
    "make_risk_completed",
    "make_risk_failed",
    "make_risk_validated",
    "make_snapshot_published",
    # Validation
    "IntegrationValidationCheck",
    "IntegrationValidationResult",
    "RiskIntegrationValidator",
    # Component Registry & Factory
    "RiskComponentRegistry",
    "RiskComponentFactory",
    # Request/Response Registry
    "RiskIntegrationRegistry",
    # Statistics
    "RiskIntegrationStatistics",
    # History
    "RiskIntegrationHistory",
    # Snapshot (integration layer)
    "RiskIntegrationSnapshot",
    # Status
    "RiskIntegrationStatus",
    # Health
    "RiskIntegrationHealth",
    "RiskIntegrationHealthReport",
    # Manager (internal)
    "RiskIntegrationManager",
    # Constants
    "INTEGRATION_SYSTEM_ID",
    "MANAGER_SYSTEM_ID",
    "REGISTRY_SYSTEM_ID",
    "VERSION",
    "SCHEMA_VERSION",
    "COMPONENT_LIFECYCLE",
    "COMPONENT_ENGINE",
    "COMPONENT_POLICIES",
    "COMPONENT_ASSESSMENT",
    "COMPONENT_SNAPSHOT",
    "REQUIRED_COMPONENTS",
    "DEFAULT_MAX_REQUESTS",
    "DEFAULT_MAX_HISTORY",
    "DEFAULT_REQUEST_TIMEOUT_S",
    "DEFAULT_INIT_TIMEOUT_S",
    "ACTOR_INTEGRATION_ENGINE",
    "ACTOR_INTEGRATION_MANAGER",
    # Enums
    "RequestType",
    "IntegrationStatus",
    "ComponentStatus",
    "HealthStatus",
    "IntegrationEventType",
    "IntegrationValidationCode",
    # Exceptions
    "RiskIntegrationError",
    "RiskIntegrationNotRunningError",
    "RiskIntegrationRequestError",
    "RiskIntegrationValidationError",
    "RiskIntegrationComponentError",
    "RiskIntegrationSnapshotError",
    "RiskIntegrationWorkflowError",
    "RiskIntegrationCapacityError",
    "RiskIntegrationTimeoutError",
    "RiskIntegrationConfigurationError",
]
