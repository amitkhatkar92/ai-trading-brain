"""iios/execution/brokers/__init__.py
==================================================
Public API for the IIOS Broker Abstraction Layer.

C6 Execution Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

# ── Constants and enumerations ────────────────────────────────────────────────
from iios.execution.brokers.constants import (
    BROKER_SYSTEM_ID,
    MANAGER_SYSTEM_ID,
    REGISTRY_SYSTEM_ID,
    FACTORY_SYSTEM_ID,
    VALIDATOR_SYSTEM_ID,
    HEALTH_SYSTEM_ID,
    VERSION,
    ACTOR_SYSTEM,
    ACTOR_BROKER,
    ACTOR_MANAGER,
    ACTOR_REGISTRY,
    ACTOR_FACTORY,
    ACTOR_VALIDATOR,
    ACTOR_USER,
    DEFAULT_MAX_BROKERS,
    DEFAULT_MAX_REQUESTS_HISTORY,
    DEFAULT_HEARTBEAT_INTERVAL,
    DEFAULT_CONNECT_TIMEOUT,
    DEFAULT_REQUEST_TIMEOUT,
    DEFAULT_HEALTH_TIMEOUT,
    MAX_RESPONSE_TIMEOUT,
    BrokerMode,
    BrokerHealthStatus,
    BrokerConnectionState,
    BrokerRequestType,
    BrokerResponseStatus,
    BrokerCapabilityCode,
    TimeInForce,
    Exchange,
    ProductType,
    BrokerValidationCode,
)

# ── Exceptions ────────────────────────────────────────────────────────────────
from iios.execution.brokers.exceptions import (
    BrokerAbstractionError,
    BrokerRegistrationError,
    BrokerNotFoundError,
    DuplicateBrokerError,
    BrokerCapacityError,
    BrokerNotConnectedError,
    BrokerConnectionError,
    BrokerValidationError,
    BrokerCapabilityError,
    BrokerRequestError,
    BrokerResponseError,
    BrokerHealthError,
    BrokerNotRunningError,
    BrokerFactoryError,
)

# ── Metadata and capabilities ─────────────────────────────────────────────────
from iios.execution.brokers.broker_metadata import BrokerMetadata, RateLimitSpec
from iios.execution.brokers.broker_capabilities import (
    BrokerCapabilities,
    capabilities_from_metadata,
)

# ── Requests ──────────────────────────────────────────────────────────────────
from iios.execution.brokers.broker_request import (
    BrokerRequest,
    ConnectionRequest,
    OrderRequest,
    ModifyRequest,
    CancelRequest,
    PositionRequest,
    BalanceRequest,
    HeartbeatRequest,
)

# ── Responses ─────────────────────────────────────────────────────────────────
from iios.execution.brokers.broker_response import (
    BrokerResponse,
    ConnectionResponse,
    OrderResponse,
    ModifyResponse,
    CancelResponse,
    PositionItem,
    PositionResponse,
    BalanceResponse,
    HealthResponse,
)

# ── Interface and base ────────────────────────────────────────────────────────
from iios.execution.brokers.broker_interface import AbstractBrokerInterface
from iios.execution.brokers.broker import AbstractBroker

# ── Context ───────────────────────────────────────────────────────────────────
from iios.execution.brokers.broker_context import (
    BrokerOperationContext,
    make_context,
)

# ── Validation ────────────────────────────────────────────────────────────────
from iios.execution.brokers.broker_validation import (
    BrokerValidator,
    BrokerValidationResult,
)

# ── Events ────────────────────────────────────────────────────────────────────
from iios.execution.brokers.broker_events import (
    BrokerEventType,
    BrokerEvent,
    make_broker_event,
)

# ── Health ────────────────────────────────────────────────────────────────────
from iios.execution.brokers.broker_health import (
    BrokerHealthRecord,
    BrokerHealthMonitor,
)

# ── Statistics ────────────────────────────────────────────────────────────────
from iios.execution.brokers.broker_statistics import (
    BrokerStatistics,
    RegistryStatistics,
)

# ── Registry ─────────────────────────────────────────────────────────────────
from iios.execution.brokers.broker_registry import (
    BrokerRecord,
    BrokerRegistry,
)

# ── Factory ───────────────────────────────────────────────────────────────────
from iios.execution.brokers.broker_factory import BrokerFactory

# ── Manager (primary entry point) ─────────────────────────────────────────────
from iios.execution.brokers.broker_manager import BrokerManager

__all__ = [
    # System IDs
    "BROKER_SYSTEM_ID",
    "MANAGER_SYSTEM_ID",
    "REGISTRY_SYSTEM_ID",
    "FACTORY_SYSTEM_ID",
    "VALIDATOR_SYSTEM_ID",
    "HEALTH_SYSTEM_ID",
    "VERSION",
    # Actor labels
    "ACTOR_SYSTEM",
    "ACTOR_BROKER",
    "ACTOR_MANAGER",
    "ACTOR_REGISTRY",
    "ACTOR_FACTORY",
    "ACTOR_VALIDATOR",
    "ACTOR_USER",
    # Capacity / timing
    "DEFAULT_MAX_BROKERS",
    "DEFAULT_MAX_REQUESTS_HISTORY",
    "DEFAULT_HEARTBEAT_INTERVAL",
    "DEFAULT_CONNECT_TIMEOUT",
    "DEFAULT_REQUEST_TIMEOUT",
    "DEFAULT_HEALTH_TIMEOUT",
    "MAX_RESPONSE_TIMEOUT",
    # Enums
    "BrokerMode",
    "BrokerHealthStatus",
    "BrokerConnectionState",
    "BrokerRequestType",
    "BrokerResponseStatus",
    "BrokerCapabilityCode",
    "TimeInForce",
    "Exchange",
    "ProductType",
    "BrokerValidationCode",
    # Exceptions
    "BrokerAbstractionError",
    "BrokerRegistrationError",
    "BrokerNotFoundError",
    "DuplicateBrokerError",
    "BrokerCapacityError",
    "BrokerNotConnectedError",
    "BrokerConnectionError",
    "BrokerValidationError",
    "BrokerCapabilityError",
    "BrokerRequestError",
    "BrokerResponseError",
    "BrokerHealthError",
    "BrokerNotRunningError",
    "BrokerFactoryError",
    # Metadata / capabilities
    "BrokerMetadata",
    "RateLimitSpec",
    "BrokerCapabilities",
    "capabilities_from_metadata",
    # Requests
    "BrokerRequest",
    "ConnectionRequest",
    "OrderRequest",
    "ModifyRequest",
    "CancelRequest",
    "PositionRequest",
    "BalanceRequest",
    "HeartbeatRequest",
    # Responses
    "BrokerResponse",
    "ConnectionResponse",
    "OrderResponse",
    "ModifyResponse",
    "CancelResponse",
    "PositionItem",
    "PositionResponse",
    "BalanceResponse",
    "HealthResponse",
    # Interface and base
    "AbstractBrokerInterface",
    "AbstractBroker",
    # Context
    "BrokerOperationContext",
    "make_context",
    # Validation
    "BrokerValidator",
    "BrokerValidationResult",
    # Events
    "BrokerEventType",
    "BrokerEvent",
    "make_broker_event",
    # Health
    "BrokerHealthRecord",
    "BrokerHealthMonitor",
    # Statistics
    "BrokerStatistics",
    "RegistryStatistics",
    # Registry
    "BrokerRecord",
    "BrokerRegistry",
    # Factory
    "BrokerFactory",
    # Manager
    "BrokerManager",
]
