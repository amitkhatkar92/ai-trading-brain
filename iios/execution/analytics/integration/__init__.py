"""
iios.execution.analytics.integration
=====================================
Execution Analytics Integration subsystem — C8 M6.

Public API
----------
The ONLY public entry point is :class:`ExecutionAnalyticsIntegration`.

    >>> from iios.execution.analytics.integration import (
    ...     ExecutionAnalyticsIntegration,
    ...     AnalyticsIntegrationRequest,
    ... )
    >>> integration = ExecutionAnalyticsIntegration()
    >>> integration.initialize()
    >>> integration.start()
    >>> req = AnalyticsIntegrationRequest(execution_session_id="exec-001")
    >>> resp = integration.submit(req)
    >>> resp.snapshot           # ExecutionAnalyticsSnapshot
    >>> integration.stop()

Internal components (M1-M5) are never exposed to callers.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# PRIMARY PUBLIC INTERFACE
# ---------------------------------------------------------------------------
from .execution_analytics_integration_engine import ExecutionAnalyticsIntegration

# ---------------------------------------------------------------------------
# Value objects — request / response / snapshot record
# ---------------------------------------------------------------------------
from .analytics_integration_request  import AnalyticsIntegrationRequest
from .analytics_integration_response import AnalyticsIntegrationResponse
from .analytics_integration_snapshot import IntegrationSnapshotRecord
from .analytics_integration_context  import AnalyticsIntegrationContext

# ---------------------------------------------------------------------------
# Observability types
# ---------------------------------------------------------------------------
from .analytics_integration_health import (
    AnalyticsIntegrationHealth,
    ComponentHealth,
    assess_integration_health,
)
from .analytics_integration_status import (
    AnalyticsIntegrationStatus,
    build_integration_status,
)
from .analytics_integration_statistics import AnalyticsIntegrationStatistics
from .analytics_integration_history    import AnalyticsIntegrationHistory

# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------
from .analytics_integration_events import (
    AnalyticsIntegrationEvent,
    make_analytics_initialized,
    make_analytics_started,
    make_analytics_completed,
    make_analytics_stopped,
    make_analytics_restarted,
    make_analytics_validated,
    make_analytics_health_changed,
    make_analytics_snapshot_published,
)

# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
from .analytics_integration_validation import (
    AnalyticsIntegrationValidator,
    IntegrationValidationResult,
    ValidationCheckResult,
)

# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------
from .analytics_integration_registry import (
    AnalyticsIntegrationRegistry,
    RegistryEntry,
    RegistryEntryState,
)

# ---------------------------------------------------------------------------
# Component infrastructure (available for testing / DI)
# ---------------------------------------------------------------------------
from .analytics_component_factory  import AnalyticsComponentFactory
from .analytics_component_registry import AnalyticsComponentRegistry

# ---------------------------------------------------------------------------
# Constants and exceptions (published for test / error handling)
# ---------------------------------------------------------------------------
from .constants import (
    INTEGRATION_SYSTEM_ID,
    INTEGRATION_VERSION,
    ComponentType,
    IntegrationStatus,
    IntegrationResponseStatus,
    IntegrationHealthLevel,
    IntegrationEventType,
    IntegrationValidationCode,
)
from .exceptions import (
    IntegrationError,
    IntegrationNotRunningError,
    IntegrationNotReadyError,
    IntegrationRequestError,
    IntegrationValidationError,
    IntegrationComponentError,
    IntegrationTimeoutError,
    IntegrationAlreadyRunningError,
)

__all__: list[str] = [
    # Primary interface
    "ExecutionAnalyticsIntegration",
    # Value objects
    "AnalyticsIntegrationRequest",
    "AnalyticsIntegrationResponse",
    "IntegrationSnapshotRecord",
    "AnalyticsIntegrationContext",
    # Observability
    "AnalyticsIntegrationHealth",
    "ComponentHealth",
    "assess_integration_health",
    "AnalyticsIntegrationStatus",
    "build_integration_status",
    "AnalyticsIntegrationStatistics",
    "AnalyticsIntegrationHistory",
    # Events
    "AnalyticsIntegrationEvent",
    "make_analytics_initialized",
    "make_analytics_started",
    "make_analytics_completed",
    "make_analytics_stopped",
    "make_analytics_restarted",
    "make_analytics_validated",
    "make_analytics_health_changed",
    "make_analytics_snapshot_published",
    # Validation
    "AnalyticsIntegrationValidator",
    "IntegrationValidationResult",
    "ValidationCheckResult",
    # Registry
    "AnalyticsIntegrationRegistry",
    "RegistryEntry",
    "RegistryEntryState",
    # Component infrastructure
    "AnalyticsComponentFactory",
    "AnalyticsComponentRegistry",
    # Constants
    "INTEGRATION_SYSTEM_ID",
    "INTEGRATION_VERSION",
    "ComponentType",
    "IntegrationStatus",
    "IntegrationResponseStatus",
    "IntegrationHealthLevel",
    "IntegrationEventType",
    "IntegrationValidationCode",
    # Exceptions
    "IntegrationError",
    "IntegrationNotRunningError",
    "IntegrationNotReadyError",
    "IntegrationRequestError",
    "IntegrationValidationError",
    "IntegrationComponentError",
    "IntegrationTimeoutError",
    "IntegrationAlreadyRunningError",
]
