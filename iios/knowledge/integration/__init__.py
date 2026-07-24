"""
__init__.py — iios.knowledge.integration
-----------------------------------------
Public API for the Institutional Knowledge Integration module (C14 M6).

This is the ONLY public entry point for the Enterprise Knowledge Intelligence
subsystem.  External components MUST NOT directly access M1–M5.
All interactions MUST occur through KnowledgeIntegrationEngine.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

# ---- Constants & Enums -------------------------------------------------
from .constants import (
    ACTOR_INTEGRATION,
    ACTOR_MANAGER,
    ACTOR_SYSTEM,
    BUILD_VERSION,
    COMPONENT_ENGINE,
    COMPONENT_GOVERNANCE,
    COMPONENT_INTELLIGENCE,
    COMPONENT_LIFECYCLE,
    COMPONENT_SNAPSHOT,
    DEFAULT_MAX_CONCURRENT,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_REQUESTS,
    DEFAULT_TIMEOUT_MS,
    FRAMEWORK_VERSION,
    INTEGRATION_SYSTEM_ID,
    SCHEMA_VERSION,
    VERSION,
    ComponentStatus,
    IntegrationEventType,
    IntegrationPhase,
    IntegrationRequestType,
    IntegrationState,
    IntegrationValidationCode,
)

# ---- Exceptions --------------------------------------------------------
from .exceptions import (
    IntegrationCapacityError,
    IntegrationComponentError,
    IntegrationExecutionError,
    IntegrationRequestError,
    IntegrationSnapshotError,
    IntegrationStateError,
    IntegrationTimeoutError,
    IntegrationValidationError,
    KnowledgeIntegrationError,
)

# ---- Request / Response -----------------------------------------------
from .knowledge_integration_context import (
    KnowledgeArtifactContext,
    KnowledgeIntegrationContext,
)
from .knowledge_integration_request import KnowledgeIntegrationRequest
from .knowledge_integration_response import KnowledgeIntegrationResponse

# ---- Domain objects ----------------------------------------------------
from .knowledge_integration_snapshot import KnowledgeIntegrationSnapshot
from .knowledge_integration_health import (
    ComponentHealth,
    KnowledgeHealthSummary,
    KnowledgeIntegrationHealth,
)
from .knowledge_integration_status import (
    KnowledgeIntegrationStatus,
    KnowledgeIntegrationStatusTracker,
)
from .knowledge_integration_statistics import (
    KnowledgeIntegrationStatistics,
    KnowledgeStatistics,
)

# ---- Events ------------------------------------------------------------
from .knowledge_integration_events import IntegrationEvent, IntegrationEventBus

# ---- Validation --------------------------------------------------------
from .knowledge_integration_validation import (
    IntegrationValidationReport,
    IntegrationValidationResult,
    KnowledgeIntegrationValidation,
)

# ---- History & Registry -----------------------------------------------
from .knowledge_integration_history import KnowledgeIntegrationHistory
from .knowledge_integration_registry import KnowledgeIntegrationRegistry

# ---- Component layer --------------------------------------------------
from .knowledge_component_registry import KnowledgeComponentRegistry
from .knowledge_component_factory import KnowledgeComponentFactory

# ---- Manager ----------------------------------------------------------
from .knowledge_integration_manager import KnowledgeIntegrationManager

# ---- Primary entry point (export last) --------------------------------
from .knowledge_integration_engine import KnowledgeIntegrationEngine

__all__ = [
    # System identifiers
    "INTEGRATION_SYSTEM_ID", "VERSION", "SCHEMA_VERSION",
    "FRAMEWORK_VERSION", "BUILD_VERSION",
    "ACTOR_INTEGRATION", "ACTOR_MANAGER", "ACTOR_SYSTEM",
    "DEFAULT_MAX_HISTORY", "DEFAULT_MAX_REQUESTS",
    "DEFAULT_TIMEOUT_MS", "DEFAULT_MAX_CONCURRENT",
    "COMPONENT_LIFECYCLE", "COMPONENT_ENGINE",
    "COMPONENT_GOVERNANCE", "COMPONENT_INTELLIGENCE", "COMPONENT_SNAPSHOT",
    # Enums
    "IntegrationState", "IntegrationEventType", "IntegrationPhase",
    "IntegrationRequestType", "IntegrationValidationCode", "ComponentStatus",
    # Exceptions
    "KnowledgeIntegrationError", "IntegrationRequestError",
    "IntegrationValidationError", "IntegrationExecutionError",
    "IntegrationComponentError", "IntegrationTimeoutError",
    "IntegrationStateError", "IntegrationCapacityError",
    "IntegrationSnapshotError",
    # Context
    "KnowledgeIntegrationContext", "KnowledgeArtifactContext",
    # Request / Response
    "KnowledgeIntegrationRequest", "KnowledgeIntegrationResponse",
    # Domain objects
    "KnowledgeIntegrationSnapshot",
    "ComponentHealth", "KnowledgeHealthSummary", "KnowledgeIntegrationHealth",
    "KnowledgeIntegrationStatus", "KnowledgeIntegrationStatusTracker",
    "KnowledgeStatistics", "KnowledgeIntegrationStatistics",
    # Events
    "IntegrationEvent", "IntegrationEventBus",
    # Validation
    "IntegrationValidationResult", "IntegrationValidationReport",
    "KnowledgeIntegrationValidation",
    # History & Registry
    "KnowledgeIntegrationHistory", "KnowledgeIntegrationRegistry",
    # Component layer
    "KnowledgeComponentRegistry", "KnowledgeComponentFactory",
    # Manager
    "KnowledgeIntegrationManager",
    # Primary engine
    "KnowledgeIntegrationEngine",
]
