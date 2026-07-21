"""
iios.decision.integration
==========================
Decision Integration Subsystem — C9 Decision Intelligence, Phase 1, Module 6.

:class:`DecisionIntegrationEngine` is the ONLY public entry point into the
Decision Intelligence subsystem.  All external modules MUST communicate
through :class:`DecisionIntegrationEngine`.

This package:
  - DOES     integrate M1-M5 into one institutional service
  - DOES     expose a clean public API (submit, validate, health, …)
  - DOES     publish M5 :class:`~iios.decision.snapshot.DecisionSnapshot`
  - DOES NOT duplicate policy evaluation
  - DOES NOT duplicate optimization logic
  - DOES NOT execute trades
  - DOES NOT expose internal M1-M4 objects

Primary entry point: :class:`DecisionIntegrationEngine`
Request type:        :class:`DecisionIntegrationRequest`
Response type:       :class:`DecisionIntegrationResponse`
"""

# -- Constants ----------------------------------------------------------------
from .constants import (
    ACTOR_ENGINE,
    ACTOR_INTEGRATION,
    ACTOR_MANAGER,
    ACTOR_COMPONENT,
    ACTOR_VALIDATOR,
    ACTOR_HEALTH,
    ACTOR_OPERATOR,
    ACTOR_SYSTEM,
    DEFAULT_DEADLINE_S,
    DEFAULT_MAX_EVENTS,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_IN_FLIGHT,
    EMA_ALPHA,
    INTEGRATION_SYSTEM_ID,
    SCHEMA_VERSION,
    SOURCE_M1,
    SOURCE_M2,
    SOURCE_M3,
    SOURCE_M4,
    SOURCE_M5,
    THROUGHPUT_WINDOW_S,
    VERSION,
    ComponentHealth,
    ComponentType,
    IntegrationEventType,
    IntegrationPhase,
    IntegrationStatus,
    IntegrationValidationCode,
    OverallHealth,
)

# -- Exceptions ---------------------------------------------------------------
from .exceptions import (
    DecisionIntegrationError,
    IntegrationNotRunningError,
    IntegrationRequestError,
    IntegrationValidationError,
    ComponentNotFoundError,
    ComponentNotReadyError,
    IntegrationTimeoutError,
    IntegrationWorkflowError,
    DuplicateIntegrationError,
    IntegrationConfigurationError,
)

# -- Value objects -------------------------------------------------------------
from .decision_integration_request  import DecisionIntegrationRequest
from .decision_integration_response import DecisionIntegrationResponse
from .decision_integration_snapshot import DecisionIntegrationSnapshot
from .decision_integration_context  import DecisionIntegrationContext

# -- Validation ---------------------------------------------------------------
from .decision_integration_validation import (
    DecisionIntegrationValidator,
    IntegrationValidationCheckResult,
    IntegrationValidationResult,
)

# -- Health & Status ----------------------------------------------------------
from .decision_integration_health import (
    ComponentHealthRecord,
    DecisionIntegrationHealth,
    DecisionIntegrationHealthMonitor,
)
from .decision_integration_status import (
    DecisionIntegrationStatus,
    DecisionIntegrationStatusMonitor,
)

# -- Statistics ---------------------------------------------------------------
from .decision_integration_statistics import DecisionIntegrationStatistics

# -- History ------------------------------------------------------------------
from .decision_integration_history import DecisionIntegrationHistory

# -- Events -------------------------------------------------------------------
from .decision_integration_events import (
    DecisionIntegrationEvent,
    make_integration_initialized,
    make_integration_started,
    make_integration_stopped,
    make_integration_restarted,
    make_request_submitted,
    make_request_completed,
    make_request_failed,
    make_snapshot_published,
    make_health_changed,
)

# -- Registry -----------------------------------------------------------------
from .decision_integration_registry import DecisionIntegrationRegistry

# -- Component registry & factory ---------------------------------------------
from .decision_component_registry import DecisionComponentRegistry
from .decision_component_factory  import DecisionComponentFactory

# -- Manager ------------------------------------------------------------------
from .decision_integration_manager import DecisionIntegrationManager

# -- Primary public interface -------------------------------------------------
from .decision_integration_engine import DecisionIntegrationEngine

__all__ = [
    # Primary interface
    "DecisionIntegrationEngine",
    # Request / Response / Snapshot
    "DecisionIntegrationRequest",
    "DecisionIntegrationResponse",
    "DecisionIntegrationSnapshot",
    "DecisionIntegrationContext",
    # Validation
    "DecisionIntegrationValidator",
    "IntegrationValidationCheckResult",
    "IntegrationValidationResult",
    # Health & Status
    "ComponentHealthRecord",
    "DecisionIntegrationHealth",
    "DecisionIntegrationHealthMonitor",
    "DecisionIntegrationStatus",
    "DecisionIntegrationStatusMonitor",
    # Statistics
    "DecisionIntegrationStatistics",
    # History
    "DecisionIntegrationHistory",
    # Events
    "DecisionIntegrationEvent",
    "make_integration_initialized",
    "make_integration_started",
    "make_integration_stopped",
    "make_integration_restarted",
    "make_request_submitted",
    "make_request_completed",
    "make_request_failed",
    "make_snapshot_published",
    "make_health_changed",
    # Registry
    "DecisionIntegrationRegistry",
    # Components
    "DecisionComponentRegistry",
    "DecisionComponentFactory",
    # Manager
    "DecisionIntegrationManager",
    # Constants
    "INTEGRATION_SYSTEM_ID",
    "VERSION",
    "SCHEMA_VERSION",
    "SOURCE_M1",
    "SOURCE_M2",
    "SOURCE_M3",
    "SOURCE_M4",
    "SOURCE_M5",
    "ComponentType",
    "ComponentHealth",
    "IntegrationStatus",
    "IntegrationPhase",
    "IntegrationEventType",
    "IntegrationValidationCode",
    "OverallHealth",
    # Exceptions
    "DecisionIntegrationError",
    "IntegrationNotRunningError",
    "IntegrationRequestError",
    "IntegrationValidationError",
    "ComponentNotFoundError",
    "ComponentNotReadyError",
    "IntegrationTimeoutError",
    "IntegrationWorkflowError",
    "DuplicateIntegrationError",
    "IntegrationConfigurationError",
]
