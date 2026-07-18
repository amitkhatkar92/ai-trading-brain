"""iios/execution/monitoring/integration/__init__.py
==================================================
Public surface for the C6 Phase 6 M6 Execution Monitoring Integration
package.

Import the engine directly:

    from iios.execution.monitoring.integration import (
        ExecutionMonitoringIntegrationEngine,
        make_monitoring_integration_context,
        make_monitoring_integration_request,
    )

C6 Execution Intelligence — Phase 6, Module 6
"""
from __future__ import annotations

# ── Engine (primary entry point) ──────────────────────────────────────────────
from .execution_monitoring_integration_engine import ExecutionMonitoringIntegrationEngine  # noqa: F401

# ── Constants ─────────────────────────────────────────────────────────────────
from .constants import (  # noqa: F401
    ENGINE_SYSTEM_ID,
    MANAGER_SYSTEM_ID,
    REGISTRY_SYSTEM_ID,
    FACTORY_SYSTEM_ID,
    VERSION,
    SCHEMA_VERSION,
    DEFAULT_MAX_REQUESTS,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_SESSIONS,
    ACTOR_INTEGRATION,
    ACTOR_ENGINE,
    ACTOR_MANAGER,
    ACTOR_SYSTEM,
    IntegrationState,
    ComponentType,
    HealthStatus,
    IntegrationEventType,
    RUNNING_INTEGRATION_STATES,
    TERMINAL_INTEGRATION_STATES,
    HEALTHY_COMPONENT_STATUSES,
    UNHEALTHY_COMPONENT_STATUSES,
)

# ── Exceptions ────────────────────────────────────────────────────────────────
from .exceptions import (  # noqa: F401
    IntegrationError,
    IntegrationNotRunningError,
    IntegrationAlreadyRunningError,
    IntegrationRequestNotFoundError,
    IntegrationSessionNotFoundError,
    IntegrationValidationError,
    IntegrationComponentError,
    IntegrationSnapshotError,
    IntegrationWorkflowError,
    IntegrationHealthError,
)

# ── DTOs ──────────────────────────────────────────────────────────────────────
from .monitoring_integration_context import (  # noqa: F401
    MonitoringIntegrationContext,
    make_monitoring_integration_context,
)
from .monitoring_integration_request import (  # noqa: F401
    MonitoringIntegrationRequest,
    make_monitoring_integration_request,
)
from .monitoring_integration_response import (  # noqa: F401
    MonitoringIntegrationResponse,
    make_monitoring_integration_response,
)
from .monitoring_integration_snapshot import (  # noqa: F401
    MonitoringIntegrationSnapshot,
    make_integration_snapshot,
)
from .monitoring_integration_health import (  # noqa: F401
    ComponentHealth,
    IntegrationHealth,
    make_component_health,
    compute_integration_health,
)
from .monitoring_integration_status import IntegrationStatusRecord  # noqa: F401
from .monitoring_integration_statistics import IntegrationStatistics  # noqa: F401
from .monitoring_integration_history import IntegrationHistory  # noqa: F401
from .monitoring_integration_events import (  # noqa: F401
    IntegrationEvent,
    make_monitoring_initialized,
    make_monitoring_started,
    make_monitoring_completed,
    make_monitoring_stopped,
    make_monitoring_restarted,
    make_monitoring_validated,
    make_monitoring_health_changed,
    make_monitoring_snapshot_published,
)
from .monitoring_integration_registry import IntegrationRegistry  # noqa: F401
from .monitoring_integration_validation import (  # noqa: F401
    IntegrationValidationResult,
    IntegrationValidator,
)
from .monitoring_component_registry import ComponentRegistry, ComponentEntry  # noqa: F401
from .monitoring_component_factory import ComponentFactory  # noqa: F401
from .monitoring_integration_manager import MonitoringIntegrationManager  # noqa: F401

__all__ = [
    # Engine
    "ExecutionMonitoringIntegrationEngine",
    # Constants
    "ENGINE_SYSTEM_ID",
    "MANAGER_SYSTEM_ID",
    "REGISTRY_SYSTEM_ID",
    "FACTORY_SYSTEM_ID",
    "VERSION",
    "SCHEMA_VERSION",
    "DEFAULT_MAX_REQUESTS",
    "DEFAULT_MAX_HISTORY",
    "DEFAULT_MAX_SESSIONS",
    "ACTOR_INTEGRATION",
    "ACTOR_ENGINE",
    "ACTOR_MANAGER",
    "ACTOR_SYSTEM",
    "IntegrationState",
    "ComponentType",
    "HealthStatus",
    "IntegrationEventType",
    "RUNNING_INTEGRATION_STATES",
    "TERMINAL_INTEGRATION_STATES",
    "HEALTHY_COMPONENT_STATUSES",
    "UNHEALTHY_COMPONENT_STATUSES",
    # Exceptions
    "IntegrationError",
    "IntegrationNotRunningError",
    "IntegrationAlreadyRunningError",
    "IntegrationRequestNotFoundError",
    "IntegrationSessionNotFoundError",
    "IntegrationValidationError",
    "IntegrationComponentError",
    "IntegrationSnapshotError",
    "IntegrationWorkflowError",
    "IntegrationHealthError",
    # DTOs
    "MonitoringIntegrationContext",
    "make_monitoring_integration_context",
    "MonitoringIntegrationRequest",
    "make_monitoring_integration_request",
    "MonitoringIntegrationResponse",
    "make_monitoring_integration_response",
    "MonitoringIntegrationSnapshot",
    "make_integration_snapshot",
    "ComponentHealth",
    "IntegrationHealth",
    "make_component_health",
    "compute_integration_health",
    "IntegrationStatusRecord",
    "IntegrationStatistics",
    "IntegrationHistory",
    "IntegrationEvent",
    "make_monitoring_initialized",
    "make_monitoring_started",
    "make_monitoring_completed",
    "make_monitoring_stopped",
    "make_monitoring_restarted",
    "make_monitoring_validated",
    "make_monitoring_health_changed",
    "make_monitoring_snapshot_published",
    "IntegrationRegistry",
    "IntegrationValidationResult",
    "IntegrationValidator",
    "ComponentRegistry",
    "ComponentEntry",
    "ComponentFactory",
    "MonitoringIntegrationManager",
]
