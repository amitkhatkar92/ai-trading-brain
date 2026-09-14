"""enterprise_ai_platform/execution/oms/integration/__init__.py
==================================================
Public API for the IIOS OMS Integration layer (M6).

THE ONLY PUBLIC ENTRY POINT TO THE OMS IS OMSIntegrationEngine.

C6 Execution Intelligence — Phase 2, Module 6
"""
from enterprise_ai_platform.execution.oms.integration.constants import (
    DEFAULT_MAX_EVENTS,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_SNAPSHOTS,
    ENGINE_SYSTEM_ID,
    FACTORY_SYSTEM_ID,
    MANAGER_SYSTEM_ID,
    OMS_INTEGRATION_SYSTEM_ID,
    REGISTRY_SYSTEM_ID,
    REQUIRED_COMPONENT_COUNT,
    REQUIRED_COMPONENTS,
    TERMINAL_OMS_STATES,
    VALIDATOR_SYSTEM_ID,
    VERSION,
    ComponentType,
    IntegrationEventType,
    IntegrationQueryType,
    OMSState,
    ValidationCode,
)
from enterprise_ai_platform.execution.oms.integration.exceptions import (
    ComponentRegistrationError,
    OMSComponentMissingError,
    OMSComponentNotRunningError,
    OMSInitializationError,
    OMSIntegrationError,
    OMSNotInitializedError,
    OMSQueryError,
    OMSRegistryCapacityError,
    OMSSnapshotError,
    OMSStateError,
    OMSValidationError,
)
from enterprise_ai_platform.execution.oms.integration.oms_component_status import ComponentStatus
from enterprise_ai_platform.execution.oms.integration.oms_component_health import ComponentHealth
from enterprise_ai_platform.execution.oms.integration.oms_integration_context import IntegrationContext
from enterprise_ai_platform.execution.oms.integration.oms_integration_request import IntegrationRequest
from enterprise_ai_platform.execution.oms.integration.oms_integration_response import IntegrationResponse
from enterprise_ai_platform.execution.oms.integration.oms_integration_statistics import IntegrationStatistics
from enterprise_ai_platform.execution.oms.integration.oms_integration_events import (
    OMSEvent,
    make_component_failed,
    make_component_registered,
    make_oms_initialized,
    make_oms_started,
    make_oms_stopped,
    make_oms_validated,
    make_snapshot_published,
)
from enterprise_ai_platform.execution.oms.integration.oms_integration_history import (
    HistoryEntry,
    IntegrationHistory,
)
from enterprise_ai_platform.execution.oms.integration.oms_integration_snapshot import OMSSnapshot
from enterprise_ai_platform.execution.oms.integration.oms_integration_validation import (
    OMSValidator,
    ValidationReport,
)
from enterprise_ai_platform.execution.oms.integration.oms_component_registry import OMSComponentRegistry
from enterprise_ai_platform.execution.oms.integration.oms_component_factory import OMSComponentFactory
from enterprise_ai_platform.execution.oms.integration.oms_integration_manager import OMSIntegrationManager
from enterprise_ai_platform.execution.oms.integration.oms_integration_engine import OMSIntegrationEngine

__all__ = [
    # Constants
    "OMS_INTEGRATION_SYSTEM_ID",
    "ENGINE_SYSTEM_ID",
    "MANAGER_SYSTEM_ID",
    "REGISTRY_SYSTEM_ID",
    "FACTORY_SYSTEM_ID",
    "VALIDATOR_SYSTEM_ID",
    "VERSION",
    "REQUIRED_COMPONENT_COUNT",
    "REQUIRED_COMPONENTS",
    "TERMINAL_OMS_STATES",
    "DEFAULT_MAX_EVENTS",
    "DEFAULT_MAX_HISTORY",
    "DEFAULT_MAX_SNAPSHOTS",
    # Enums
    "OMSState",
    "ComponentType",
    "IntegrationEventType",
    "IntegrationQueryType",
    "ValidationCode",
    # Exceptions
    "OMSIntegrationError",
    "OMSNotInitializedError",
    "OMSComponentMissingError",
    "OMSComponentNotRunningError",
    "OMSValidationError",
    "OMSSnapshotError",
    "OMSQueryError",
    "OMSStateError",
    "OMSRegistryCapacityError",
    "ComponentRegistrationError",
    "OMSInitializationError",
    # Data objects
    "ComponentStatus",
    "ComponentHealth",
    "IntegrationContext",
    "IntegrationRequest",
    "IntegrationResponse",
    "IntegrationStatistics",
    "OMSEvent",
    "HistoryEntry",
    "IntegrationHistory",
    "OMSSnapshot",
    "ValidationReport",
    # Event factories
    "make_oms_initialized",
    "make_oms_started",
    "make_oms_stopped",
    "make_oms_validated",
    "make_snapshot_published",
    "make_component_registered",
    "make_component_failed",
    # Components / Services
    "OMSComponentRegistry",
    "OMSComponentFactory",
    "OMSValidator",
    "OMSIntegrationManager",
    # Primary entry point
    "OMSIntegrationEngine",
]
