"""
iios.supervisor.integration — AI Supervisor Integration
========================================================

PRIMARY PUBLIC INTERFACE for the entire AI Supervisor & Autonomous Governance
subsystem.  All external callers MUST use :class:`SupervisorIntegrationEngine`
as the sole entry point.

External components MUST NOT directly import from:
  - ``iios.supervisor.lifecycle``  (M1)
  - ``iios.supervisor.engine``     (M2)
  - ``iios.supervisor.policies``   (M3)
  - ``iios.supervisor.governance`` (M4)
  - ``iios.supervisor.snapshot``   (M5)
"""

# ---------------------------------------------------------------------------
# Constants & enumerations
# ---------------------------------------------------------------------------
from .constants import (
    ACTOR_OPERATOR,
    ACTOR_SYSTEM,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_REQUESTS,
    DEFAULT_MAX_SESSIONS,
    INTEGRATION_SYSTEM_ID,
    VERSION,
    ComponentType,
    IntegrationEventType,
    IntegrationHealthStatus,
    IntegrationMode,
    IntegrationStatus,
    IntegrationValidationCode,
    WorkflowPhase,
)

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------
from .exceptions import (
    SupervisorIntegrationCapacityError,
    SupervisorIntegrationComponentError,
    SupervisorIntegrationError,
    SupervisorIntegrationNotRunningError,
    SupervisorIntegrationRegistryError,
    SupervisorIntegrationTimeoutError,
    SupervisorIntegrationValidationError,
    SupervisorIntegrationWorkflowError,
)

# ---------------------------------------------------------------------------
# Context & request
# ---------------------------------------------------------------------------
from .supervisor_integration_context import SupervisorIntegrationContext
from .supervisor_integration_request import SupervisorIntegrationRequest

# ---------------------------------------------------------------------------
# Response & summaries
# ---------------------------------------------------------------------------
from .supervisor_integration_response import (
    EnterpriseAssessment,
    IntegrationGovernanceSummary,
    PlatformHealthSummary,
    SupervisorIntegrationResponse,
)

# ---------------------------------------------------------------------------
# Snapshot wrapper
# ---------------------------------------------------------------------------
from .supervisor_integration_snapshot import SupervisorIntegrationSnapshot

# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
from .supervisor_integration_validation import (
    IntegrationValidationCheckResult,
    SupervisorIntegrationValidationResult,
    SupervisorIntegrationValidator,
)

# ---------------------------------------------------------------------------
# Health & status reporters
# ---------------------------------------------------------------------------
from .supervisor_integration_health import SupervisorIntegrationHealth
from .supervisor_integration_status import SupervisorIntegrationStatus

# ---------------------------------------------------------------------------
# Statistics & history
# ---------------------------------------------------------------------------
from .supervisor_integration_statistics import SupervisorIntegrationStatistics
from .supervisor_integration_history import SupervisorIntegrationHistory

# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------
from .supervisor_integration_events import (
    SupervisorIntegrationEvent,
    make_integration_completed_event,
    make_integration_executed_event,
    make_integration_failed_event,
    make_integration_initialized_event,
    make_integration_started_event,
    make_integration_stopped_event,
    make_integration_validated_event,
    make_snapshot_published_event,
)

# ---------------------------------------------------------------------------
# Integration request registry
# ---------------------------------------------------------------------------
from .supervisor_integration_registry import SupervisorIntegrationRegistry

# ---------------------------------------------------------------------------
# Component registry & factory
# ---------------------------------------------------------------------------
from .supervisor_component_registry import SupervisorComponentRegistry
from .supervisor_component_factory import SupervisorComponentFactory

# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------
from .supervisor_integration_manager import SupervisorIntegrationManager

# ---------------------------------------------------------------------------
# PRIMARY ENGINE — sole public entry point
# ---------------------------------------------------------------------------
from .supervisor_integration_engine import SupervisorIntegrationEngine


__all__ = [
    # Constants
    "ACTOR_OPERATOR",
    "ACTOR_SYSTEM",
    "DEFAULT_MAX_HISTORY",
    "DEFAULT_MAX_REQUESTS",
    "DEFAULT_MAX_SESSIONS",
    "INTEGRATION_SYSTEM_ID",
    "VERSION",
    "ComponentType",
    "IntegrationEventType",
    "IntegrationHealthStatus",
    "IntegrationMode",
    "IntegrationStatus",
    "IntegrationValidationCode",
    "WorkflowPhase",
    # Exceptions
    "SupervisorIntegrationError",
    "SupervisorIntegrationNotRunningError",
    "SupervisorIntegrationValidationError",
    "SupervisorIntegrationWorkflowError",
    "SupervisorIntegrationComponentError",
    "SupervisorIntegrationCapacityError",
    "SupervisorIntegrationRegistryError",
    "SupervisorIntegrationTimeoutError",
    # Context & request
    "SupervisorIntegrationContext",
    "SupervisorIntegrationRequest",
    # Response & summaries
    "PlatformHealthSummary",
    "IntegrationGovernanceSummary",
    "EnterpriseAssessment",
    "SupervisorIntegrationResponse",
    # Snapshot wrapper
    "SupervisorIntegrationSnapshot",
    # Validation
    "IntegrationValidationCheckResult",
    "SupervisorIntegrationValidationResult",
    "SupervisorIntegrationValidator",
    # Health & status
    "SupervisorIntegrationHealth",
    "SupervisorIntegrationStatus",
    # Statistics & history
    "SupervisorIntegrationStatistics",
    "SupervisorIntegrationHistory",
    # Events
    "SupervisorIntegrationEvent",
    "make_integration_initialized_event",
    "make_integration_started_event",
    "make_integration_validated_event",
    "make_integration_executed_event",
    "make_snapshot_published_event",
    "make_integration_completed_event",
    "make_integration_failed_event",
    "make_integration_stopped_event",
    # Registries
    "SupervisorIntegrationRegistry",
    "SupervisorComponentRegistry",
    "SupervisorComponentFactory",
    # Manager
    "SupervisorIntegrationManager",
    # Primary engine
    "SupervisorIntegrationEngine",
]
