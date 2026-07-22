"""
__init__.py — iios.portfolio.integration
=========================================
Public API for the Portfolio Integration subsystem.

PortfolioIntegrationEngine is the ONLY public entry point into the
Portfolio Intelligence subsystem.  All external modules MUST communicate
through PortfolioIntegrationEngine.

C10 Portfolio Intelligence — Phase 1, Module 6
"""
from .constants import (
    INTEGRATION_SYSTEM_ID,
    VERSION,
    ACTOR_INTEGRATION,
    ACTOR_MANAGER,
    ACTOR_VALIDATOR,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_REQUESTS,
    DEFAULT_MAX_SESSIONS,
    IntegrationState,
    IntegrationServiceType,
    WorkflowStage,
    ResponseStatus,
    ComponentType,
    IntegrationEventType,
    IntegrationValidationCode,
    IntegrationHealth,
    CREATION_SERVICES,
    READONLY_SERVICES,
)
from .exceptions import (
    PortfolioIntegrationError,
    IntegrationNotReadyError,
    IntegrationRequestError,
    IntegrationValidationError,
    IntegrationWorkflowError,
    IntegrationComponentError,
    IntegrationSnapshotError,
    IntegrationHistoryError,
    IntegrationCapacityError,
    IntegrationTimeoutError,
)
from .portfolio_integration_context import IntegrationContext
from .portfolio_integration_request import PortfolioIntegrationRequest
from .portfolio_integration_response import PortfolioIntegrationResponse
from .portfolio_integration_events import (
    IntegrationEvent,
    make_portfolio_initialized,
    make_portfolio_started,
    make_portfolio_completed,
    make_portfolio_stopped,
    make_portfolio_restarted,
    make_portfolio_validated,
    make_portfolio_health_changed,
    make_snapshot_published,
)
from .portfolio_integration_validation import (
    IntegrationValidationCheckResult,
    IntegrationValidationResult,
    PortfolioIntegrationValidator,
)
from .portfolio_integration_statistics import PortfolioIntegrationStatistics
from .portfolio_integration_status import (
    IntegrationComponentStatus,
    PortfolioIntegrationStatus,
)
from .portfolio_integration_health import PortfolioIntegrationHealth
from .portfolio_integration_history import PortfolioIntegrationHistory
from .portfolio_integration_registry import PortfolioIntegrationRegistry
from .portfolio_integration_snapshot import PortfolioIntegrationSnapshot
from .portfolio_component_registry import PortfolioComponentRegistry
from .portfolio_component_factory import PortfolioComponentFactory
from .portfolio_integration_manager import PortfolioIntegrationManager
from .portfolio_integration_engine import PortfolioIntegrationEngine   # PRIMARY INTERFACE

__all__ = [
    # constants
    "INTEGRATION_SYSTEM_ID",
    "VERSION",
    "ACTOR_INTEGRATION",
    "ACTOR_MANAGER",
    "ACTOR_VALIDATOR",
    "DEFAULT_MAX_HISTORY",
    "DEFAULT_MAX_REQUESTS",
    "DEFAULT_MAX_SESSIONS",
    "IntegrationState",
    "IntegrationServiceType",
    "WorkflowStage",
    "ResponseStatus",
    "ComponentType",
    "IntegrationEventType",
    "IntegrationValidationCode",
    "IntegrationHealth",
    "CREATION_SERVICES",
    "READONLY_SERVICES",
    # exceptions
    "PortfolioIntegrationError",
    "IntegrationNotReadyError",
    "IntegrationRequestError",
    "IntegrationValidationError",
    "IntegrationWorkflowError",
    "IntegrationComponentError",
    "IntegrationSnapshotError",
    "IntegrationHistoryError",
    "IntegrationCapacityError",
    "IntegrationTimeoutError",
    # context
    "IntegrationContext",
    # request / response
    "PortfolioIntegrationRequest",
    "PortfolioIntegrationResponse",
    # events
    "IntegrationEvent",
    "make_portfolio_initialized",
    "make_portfolio_started",
    "make_portfolio_completed",
    "make_portfolio_stopped",
    "make_portfolio_restarted",
    "make_portfolio_validated",
    "make_portfolio_health_changed",
    "make_snapshot_published",
    # validation
    "IntegrationValidationCheckResult",
    "IntegrationValidationResult",
    "PortfolioIntegrationValidator",
    # infrastructure
    "PortfolioIntegrationStatistics",
    "IntegrationComponentStatus",
    "PortfolioIntegrationStatus",
    "PortfolioIntegrationHealth",
    "PortfolioIntegrationHistory",
    "PortfolioIntegrationRegistry",
    "PortfolioIntegrationSnapshot",
    # component management
    "PortfolioComponentRegistry",
    "PortfolioComponentFactory",
    # coordination
    "PortfolioIntegrationManager",
    # PRIMARY INTERFACE
    "PortfolioIntegrationEngine",
]
