"""
iios/execution/recovery/integration/__init__.py
================================================
Public API for the Execution Recovery Integration subsystem.

Primary entry point: ExecutionRecoveryIntegrationEngine

C7 Execution Recovery & Resilience — Phase 1, Module 6
"""
from __future__ import annotations

# ── Primary entry point ───────────────────────────────────────────────────────
from .execution_recovery_integration_engine import ExecutionRecoveryIntegrationEngine  # noqa: F401

# ── Constants ─────────────────────────────────────────────────────────────────
from .constants import (  # noqa: F401
    SYSTEM_ID,
    ENGINE_ID,
    MANAGER_ID,
    REGISTRY_ID,
    FACTORY_ID,
    VERSION,
    SCHEMA_VERSION,
    DEFAULT_MAX_ACTIVE_REQUESTS,
    DEFAULT_MAX_HISTORY,
    ACTOR_INTEGRATION,
    ACTOR_SYSTEM,
    COMP_ENGINE,
    COMP_POLICY,
    COMP_FAILOVER,
    COMP_SNAPSHOT,
    IntegrationStatus,
    ComponentStatus,
    IntegrationHealth,
    IntegrationEventType,
)

# ── Exceptions ────────────────────────────────────────────────────────────────
from .exceptions import (  # noqa: F401
    IntegrationError,
    IntegrationNotRunningError,
    IntegrationValidationError,
    IntegrationRequestError,
    IntegrationSessionError,
    IntegrationComponentError,
    IntegrationHealthError,
    IntegrationSnapshotError,
    IntegrationHistoryError,
    IntegrationDuplicateError,
)

# ── Value objects ─────────────────────────────────────────────────────────────
from .recovery_integration_context import (  # noqa: F401
    IntegrationContext,
    make_integration_context,
)
from .recovery_integration_request import (  # noqa: F401
    IntegrationRequest,
    make_integration_request,
)
from .recovery_integration_response import (  # noqa: F401
    IntegrationResponse,
    make_integration_response,
)
from .recovery_integration_snapshot import (  # noqa: F401
    IntegrationSnapshot,
    make_integration_snapshot,
)
from .recovery_integration_events import (  # noqa: F401
    IntegrationEvent,
    make_recovery_initialized,
    make_recovery_started,
    make_recovery_completed,
    make_recovery_stopped,
    make_recovery_restarted,
    make_recovery_validated,
    make_recovery_health_changed,
    make_recovery_snapshot_published,
)

# ── Services / supporting classes ─────────────────────────────────────────────
from .recovery_integration_statistics import IntegrationStatistics  # noqa: F401
from .recovery_integration_history import IntegrationHistory  # noqa: F401
from .recovery_integration_registry import IntegrationRegistry  # noqa: F401
from .recovery_integration_validation import (  # noqa: F401
    IntegrationValidationResult,
    IntegrationValidator,
)
from .recovery_integration_health import (  # noqa: F401
    ComponentHealthReport,
    IntegrationHealthMonitor,
)
from .recovery_integration_status import (  # noqa: F401
    IntegrationStatusReport,
    make_status_report,
)

# ── Component wiring ──────────────────────────────────────────────────────────
from .recovery_component_registry import RecoveryComponentRegistry  # noqa: F401
from .recovery_component_factory import (  # noqa: F401
    FailoverEngineAdapter,
    RecoveryComponentFactory,
)
from .recovery_integration_manager import RecoveryIntegrationManager  # noqa: F401

__all__ = [
    # Primary
    "ExecutionRecoveryIntegrationEngine",
    # Constants
    "SYSTEM_ID", "ENGINE_ID", "MANAGER_ID", "REGISTRY_ID", "FACTORY_ID",
    "VERSION", "SCHEMA_VERSION", "DEFAULT_MAX_ACTIVE_REQUESTS", "DEFAULT_MAX_HISTORY",
    "ACTOR_INTEGRATION", "ACTOR_SYSTEM",
    "COMP_ENGINE", "COMP_POLICY", "COMP_FAILOVER", "COMP_SNAPSHOT",
    "IntegrationStatus", "ComponentStatus", "IntegrationHealth", "IntegrationEventType",
    # Exceptions
    "IntegrationError", "IntegrationNotRunningError", "IntegrationValidationError",
    "IntegrationRequestError", "IntegrationSessionError", "IntegrationComponentError",
    "IntegrationHealthError", "IntegrationSnapshotError", "IntegrationHistoryError",
    "IntegrationDuplicateError",
    # Value objects
    "IntegrationContext", "make_integration_context",
    "IntegrationRequest", "make_integration_request",
    "IntegrationResponse", "make_integration_response",
    "IntegrationSnapshot", "make_integration_snapshot",
    "IntegrationEvent",
    "make_recovery_initialized", "make_recovery_started", "make_recovery_completed",
    "make_recovery_stopped", "make_recovery_restarted", "make_recovery_validated",
    "make_recovery_health_changed", "make_recovery_snapshot_published",
    # Services
    "IntegrationStatistics", "IntegrationHistory", "IntegrationRegistry",
    "IntegrationValidationResult", "IntegrationValidator",
    "ComponentHealthReport", "IntegrationHealthMonitor",
    "IntegrationStatusReport", "make_status_report",
    # Wiring
    "RecoveryComponentRegistry", "FailoverEngineAdapter", "RecoveryComponentFactory",
    "RecoveryIntegrationManager",
]
