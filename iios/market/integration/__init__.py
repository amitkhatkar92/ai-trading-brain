"""
iios.market.integration — Market Integration subsystem
========================================================
C12 Market Intelligence — Phase 1, Module 6

Market Integration is the ONLY public interface for the complete Market
Intelligence subsystem.  External components MUST communicate exclusively
through :class:`MarketIntegrationEngine`.

:class:`~iios.market.snapshot.MarketSnapshot` is the ONLY published artefact.
No internal Market Intelligence component may be accessed directly.

Quick-start
-----------
::

    from iios.market.integration import MarketIntegrationEngine, MarketIntegrationRequest

    engine = MarketIntegrationEngine()
    engine.initialize(exchange="NSE")
    engine.start()

    response = engine.submit(MarketIntegrationRequest.market_overview("NSE"))
    snapshot = engine.get_market_snapshot("NSE")
    status   = engine.status()
    health   = engine.health()
    stats    = engine.statistics()

    engine.stop()

Public API — summary
--------------------
Engine (primary interface)
    MarketIntegrationEngine

Requests
    MarketIntegrationRequest
    MarketIntegrationContext

Responses
    MarketIntegrationResponse
    MarketIntegrationSnapshot
    MarketIntegrationStatus

Validation
    MarketIntegrationValidation
    MarketIntegrationValidationResult
    IntegrationCheckResult

Infrastructure
    MarketIntegrationRegistry
    MarketIntegrationStatistics
    MarketIntegrationHistory
    MarketIntegrationHealth

Components
    MarketComponentRegistry
    MarketComponentFactory

Events
    MarketIntegrationEvent
    market_integration_started_event
    market_request_received_event
    market_validated_event
    market_snapshot_published_event
    market_completed_event
    market_failed_event
    market_integration_stopped_event

Exceptions
    MarketIntegrationError
    MarketIntegrationNotRunningError
    MarketIntegrationRequestError
    MarketIntegrationValidationError
    MarketIntegrationNotFoundError
    MarketIntegrationSubsystemError
    MarketIntegrationCapacityError
    MarketIntegrationConfigurationError
    MarketIntegrationSnapshotError
    MarketIntegrationHistoryError

Enumerations
    IntegrationRequestType
    IntegrationStatus
    IntegrationEventType
    IntegrationValidationCode
    IntegrationPriority
    ComponentStatus
"""
from __future__ import annotations

# Primary interface
from .market_integration_engine import MarketIntegrationEngine

# Requests
from .market_integration_context import MarketIntegrationContext
from .market_integration_request import MarketIntegrationRequest

# Responses
from .market_integration_response import MarketIntegrationResponse
from .market_integration_snapshot import MarketIntegrationSnapshot
from .market_integration_status import MarketIntegrationStatus

# Validation
from .market_integration_validation import (
    IntegrationCheckResult,
    MarketIntegrationValidation,
    MarketIntegrationValidationResult,
)

# Infrastructure
from .market_integration_health import MarketIntegrationHealth
from .market_integration_history import MarketIntegrationHistory
from .market_integration_registry import MarketIntegrationRegistry
from .market_integration_statistics import MarketIntegrationStatistics

# Components
from .market_component_factory import MarketComponentFactory
from .market_component_registry import MarketComponentRegistry

# Events
from .market_integration_events import (
    MarketIntegrationEvent,
    market_completed_event,
    market_failed_event,
    market_integration_started_event,
    market_integration_stopped_event,
    market_request_received_event,
    market_snapshot_published_event,
    market_validated_event,
)

# Exceptions
from .exceptions import (
    MarketIntegrationCapacityError,
    MarketIntegrationConfigurationError,
    MarketIntegrationError,
    MarketIntegrationHistoryError,
    MarketIntegrationNotFoundError,
    MarketIntegrationNotRunningError,
    MarketIntegrationRequestError,
    MarketIntegrationSnapshotError,
    MarketIntegrationSubsystemError,
    MarketIntegrationValidationError,
)

# Enumerations & constants
from .constants import (
    INTEGRATION_SYSTEM_ID,
    VERSION,
    ComponentStatus,
    IntegrationEventType,
    IntegrationPriority,
    IntegrationRequestType,
    IntegrationStatus,
    IntegrationValidationCode,
)

__all__ = [
    # Version / IDs
    "VERSION",
    "INTEGRATION_SYSTEM_ID",
    # Primary interface
    "MarketIntegrationEngine",
    # Requests
    "MarketIntegrationRequest",
    "MarketIntegrationContext",
    # Responses
    "MarketIntegrationResponse",
    "MarketIntegrationSnapshot",
    "MarketIntegrationStatus",
    # Validation
    "MarketIntegrationValidation",
    "MarketIntegrationValidationResult",
    "IntegrationCheckResult",
    # Infrastructure
    "MarketIntegrationHealth",
    "MarketIntegrationHistory",
    "MarketIntegrationRegistry",
    "MarketIntegrationStatistics",
    # Components
    "MarketComponentFactory",
    "MarketComponentRegistry",
    # Events
    "MarketIntegrationEvent",
    "market_integration_started_event",
    "market_request_received_event",
    "market_validated_event",
    "market_snapshot_published_event",
    "market_completed_event",
    "market_failed_event",
    "market_integration_stopped_event",
    # Exceptions
    "MarketIntegrationError",
    "MarketIntegrationNotRunningError",
    "MarketIntegrationRequestError",
    "MarketIntegrationValidationError",
    "MarketIntegrationNotFoundError",
    "MarketIntegrationSubsystemError",
    "MarketIntegrationCapacityError",
    "MarketIntegrationConfigurationError",
    "MarketIntegrationSnapshotError",
    "MarketIntegrationHistoryError",
    # Enumerations
    "IntegrationRequestType",
    "IntegrationStatus",
    "IntegrationEventType",
    "IntegrationValidationCode",
    "IntegrationPriority",
    "ComponentStatus",
]
