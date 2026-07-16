"""iios/execution/positions/integration/__init__.py
==================================================
Public API for the IIOS Position Integration module.

PositionIntegrationEngine is the ONLY public interface to
the entire Position Management subsystem.

C6 Execution Intelligence — Phase 3, Module 6
"""
from __future__ import annotations

# ── Constants ─────────────────────────────────────────────────────────────────
from .constants import (
    ALL_COMPONENT_NAMES,
    ACTOR_COMPONENT,
    ACTOR_INTEGRATION,
    ACTOR_MANAGER,
    ACTOR_SYSTEM,
    COMPONENT_BOOK,
    COMPONENT_ENGINE,
    COMPONENT_RISK,
    COMPONENT_SNAPSHOT,
    COMPONENT_FACTORY_ID,
    COMPONENT_REGISTRY_ID,
    DEFAULT_MAX_CACHE_ENTRIES,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_POSITIONS,
    INTEGRATION_SYSTEM_ID,
    MANAGER_SYSTEM_ID,
    VALIDATOR_SYSTEM_ID,
    VERSION,
    HealthStatus,
    IntegrationEventType,
    IntegrationOperationType,
)

# ── Exceptions ────────────────────────────────────────────────────────────────
from .exceptions import (
    ComponentHealthError,
    ComponentNotFoundError,
    ComponentRegistrationError,
    IntegrationOperationError,
    IntegrationRequestError,
    IntegrationSnapshotError,
    IntegrationValidationError,
    PositionIntegrationError,
    PositionIntegrationInitError,
    PositionIntegrationNotRunningError,
)

# ── Component status & health ─────────────────────────────────────────────────
from .position_component_status import ComponentStatus
from .position_component_health import (
    ComponentHealthRecord,
    HealthReport,
    make_health_report,
)

# ── Component registry & factory ─────────────────────────────────────────────
from .position_component_registry import ComponentRegistry
from .position_component_factory import ComponentFactory

# ── Context ───────────────────────────────────────────────────────────────────
from .position_integration_context import IntegrationContext, make_integration_context

# ── Requests ──────────────────────────────────────────────────────────────────
from .position_integration_request import (
    BaseIntegrationRequest,
    ArchivePositionIntegrationRequest,
    ClosePositionIntegrationRequest,
    CreatePositionIntegrationRequest,
    PublishSnapshotIntegrationRequest,
    QueryPositionIntegrationRequest,
    SyncPositionIntegrationRequest,
    UpdatePositionIntegrationRequest,
)

# ── Response ──────────────────────────────────────────────────────────────────
from .position_integration_response import (
    IntegrationResponse,
    make_failure_response,
    make_success_response,
)

# ── Snapshots ─────────────────────────────────────────────────────────────────
from .position_integration_snapshot import (
    PositionIntegrationSnapshot,
    make_integration_snapshot,
)

# ── Events ────────────────────────────────────────────────────────────────────
from .position_integration_events import (
    IntegrationEvent,
    make_component_failed_event,
    make_component_registered_event,
    make_snapshot_published_event,
    make_subsystem_initialized_event,
    make_subsystem_started_event,
    make_subsystem_stopped_event,
    make_validation_completed_event,
)

# ── History ───────────────────────────────────────────────────────────────────
from .position_integration_history import IntegrationHistory

# ── Statistics ────────────────────────────────────────────────────────────────
from .position_integration_statistics import IntegrationStatistics

# ── Validation ────────────────────────────────────────────────────────────────
from .position_integration_validation import (
    IntegrationValidationResult,
    IntegrationValidator,
)

# ── Manager ───────────────────────────────────────────────────────────────────
from .position_integration_manager import PositionIntegrationManager

# ── Primary facade ────────────────────────────────────────────────────────────
from .position_integration_engine import PositionIntegrationEngine

__all__ = [
    # ── constants
    "INTEGRATION_SYSTEM_ID",
    "MANAGER_SYSTEM_ID",
    "COMPONENT_REGISTRY_ID",
    "COMPONENT_FACTORY_ID",
    "VALIDATOR_SYSTEM_ID",
    "COMPONENT_ENGINE",
    "COMPONENT_BOOK",
    "COMPONENT_RISK",
    "COMPONENT_SNAPSHOT",
    "ALL_COMPONENT_NAMES",
    "ACTOR_INTEGRATION",
    "ACTOR_MANAGER",
    "ACTOR_COMPONENT",
    "ACTOR_SYSTEM",
    "VERSION",
    "DEFAULT_MAX_POSITIONS",
    "DEFAULT_MAX_HISTORY",
    "DEFAULT_MAX_CACHE_ENTRIES",
    # ── enums
    "HealthStatus",
    "IntegrationEventType",
    "IntegrationOperationType",
    # ── exceptions
    "PositionIntegrationError",
    "PositionIntegrationNotRunningError",
    "PositionIntegrationInitError",
    "ComponentRegistrationError",
    "ComponentNotFoundError",
    "ComponentHealthError",
    "IntegrationValidationError",
    "IntegrationSnapshotError",
    "IntegrationRequestError",
    "IntegrationOperationError",
    # ── component status & health
    "ComponentStatus",
    "ComponentHealthRecord",
    "HealthReport",
    "make_health_report",
    # ── component registry & factory
    "ComponentRegistry",
    "ComponentFactory",
    # ── context
    "IntegrationContext",
    "make_integration_context",
    # ── requests
    "BaseIntegrationRequest",
    "CreatePositionIntegrationRequest",
    "UpdatePositionIntegrationRequest",
    "ClosePositionIntegrationRequest",
    "SyncPositionIntegrationRequest",
    "ArchivePositionIntegrationRequest",
    "QueryPositionIntegrationRequest",
    "PublishSnapshotIntegrationRequest",
    # ── response
    "IntegrationResponse",
    "make_success_response",
    "make_failure_response",
    # ── snapshots
    "PositionIntegrationSnapshot",
    "make_integration_snapshot",
    # ── events
    "IntegrationEvent",
    "make_subsystem_initialized_event",
    "make_subsystem_started_event",
    "make_subsystem_stopped_event",
    "make_snapshot_published_event",
    "make_validation_completed_event",
    "make_component_registered_event",
    "make_component_failed_event",
    # ── history
    "IntegrationHistory",
    # ── statistics
    "IntegrationStatistics",
    # ── validation
    "IntegrationValidationResult",
    "IntegrationValidator",
    # ── manager
    "PositionIntegrationManager",
    # ── primary facade
    "PositionIntegrationEngine",
]
