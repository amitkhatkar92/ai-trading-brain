"""iios/execution/gateway/brokers/__init__.py
==================================================
Public API for the IIOS Broker Abstraction Layer.

C6 Execution Intelligence — Phase 5, Module 3

Primary entry point
-------------------
    from iios.execution.gateway.brokers import BrokerManager
    from iios.execution.gateway.brokers import BrokerInterface

    manager = BrokerManager()
    manager.start()

    manager.register_broker(my_broker, config)
    resp = manager.connect("my-broker-id")
    resp = manager.authenticate("my-broker-id")
    resp = manager.place_order("my-broker-id", order_request)

    manager.stop()
"""

# ── Primary manager ───────────────────────────────────────────────────────────
from .broker_manager import BrokerManager

# ── Interface ─────────────────────────────────────────────────────────────────
from .broker_interface import BrokerInterface

# ── Registry ──────────────────────────────────────────────────────────────────
from .broker_registry import BrokerRegistry

# ── Constants ─────────────────────────────────────────────────────────────────
from .constants import (
    BROKER_SYSTEM_ID,
    BROKER_MANAGER_SYSTEM_ID,
    BROKER_REGISTRY_SYSTEM_ID,
    VERSION,
    BrokerStatus,
    BrokerCapability,
    BrokerEventType,
    RequestType,
    ResponseStatus,
    OrderSide,
    OrderType,
    ProductType,
    AssetClass,
    ACTIVE_BROKER_STATUSES,
    TERMINAL_BROKER_STATUSES,
    READY_BROKER_STATUSES,
    TERMINAL_RESPONSE_STATUSES,
    RETRYABLE_RESPONSE_STATUSES,
    DEFAULT_MAX_BROKERS,
    DEFAULT_MAX_HISTORY,
    DEFAULT_HEARTBEAT_INTERVAL_SECS,
    DEFAULT_RECONNECT_DELAY_SECS,
    DEFAULT_MAX_RECONNECT_ATTEMPTS,
    DEFAULT_CONNECTION_TIMEOUT_SECS,
    DEFAULT_AUTH_TIMEOUT_SECS,
    DEFAULT_REQUEST_TIMEOUT_SECS,
    DEFAULT_SESSION_TIMEOUT_SECS,
    DEFAULT_MAX_RETRIES,
)

# ── Exceptions ────────────────────────────────────────────────────────────────
from .exceptions import (
    BrokerAbstractionError,
    BrokerNotRegisteredError,
    BrokerAlreadyRegisteredError,
    BrokerNotConnectedError,
    BrokerAuthenticationError,
    BrokerSessionExpiredError,
    BrokerCapabilityNotSupportedError,
    BrokerValidationError,
    BrokerConfigurationError,
    BrokerConnectionError,
    BrokerRegistryCapacityError,
    BrokerHealthError,
    BrokerRequestError,
    BrokerManagerNotRunningError,
    DuplicateBrokerError,
)

# ── Capabilities ──────────────────────────────────────────────────────────────
from .broker_capabilities import (
    BrokerCapabilities,
    ALL_CAPABILITIES,
    make_capabilities,
    make_capabilities_from_iterable,
    find_brokers_by_capability,
)

# ── Configuration ─────────────────────────────────────────────────────────────
from .broker_configuration import BrokerConfiguration

# ── Connection ────────────────────────────────────────────────────────────────
from .broker_connection import BrokerConnection, ConnectionPool

# ── Session ───────────────────────────────────────────────────────────────────
from .broker_session import BrokerSession, BrokerSessionManager

# ── Requests ──────────────────────────────────────────────────────────────────
from .broker_request import (
    BrokerRequest,
    OrderRequest,
    ModifyOrderRequest,
    CancelOrderRequest,
    PositionRequest,
    FundsRequest,
    MarginRequest,
    StatusRequest,
    make_order_request,
    make_modify_order_request,
    make_cancel_order_request,
    make_position_request,
    make_funds_request,
    make_margin_request,
    make_status_request,
)

# ── Response ──────────────────────────────────────────────────────────────────
from .broker_response import (
    BrokerResponse,
    make_success_response,
    make_failure_response,
    make_error_response,
    make_retryable_error_response,
    make_auth_failure_response,
    make_network_failure_response,
    make_rate_limit_response,
)

# ── Health ────────────────────────────────────────────────────────────────────
from .broker_health import BrokerHealthRecord, BrokerHealthMonitor, make_health_record

# ── Statistics ────────────────────────────────────────────────────────────────
from .broker_statistics import BrokerStatistics, BrokerStatisticsStore

# ── History ───────────────────────────────────────────────────────────────────
from .broker_history import BrokerHistory

# ── Events ────────────────────────────────────────────────────────────────────
from .broker_events import (
    BrokerEvent,
    make_broker_registered_event,
    make_broker_connected_event,
    make_broker_disconnected_event,
    make_authentication_succeeded_event,
    make_authentication_failed_event,
    make_session_expired_event,
    make_reconnect_started_event,
    make_reconnect_succeeded_event,
    make_health_changed_event,
)

# ── Validation ────────────────────────────────────────────────────────────────
from .broker_validation import BrokerValidationResult, BrokerValidator

# ── Factory ───────────────────────────────────────────────────────────────────
from .broker_factory import BrokerFactory


__all__ = [
    # Manager
    "BrokerManager",
    # Interface
    "BrokerInterface",
    # Registry
    "BrokerRegistry",
    # Constants
    "BROKER_SYSTEM_ID",
    "BROKER_MANAGER_SYSTEM_ID",
    "BROKER_REGISTRY_SYSTEM_ID",
    "VERSION",
    "BrokerStatus",
    "BrokerCapability",
    "BrokerEventType",
    "RequestType",
    "ResponseStatus",
    "OrderSide",
    "OrderType",
    "ProductType",
    "AssetClass",
    "ACTIVE_BROKER_STATUSES",
    "TERMINAL_BROKER_STATUSES",
    "READY_BROKER_STATUSES",
    "TERMINAL_RESPONSE_STATUSES",
    "RETRYABLE_RESPONSE_STATUSES",
    "DEFAULT_MAX_BROKERS",
    "DEFAULT_MAX_HISTORY",
    "DEFAULT_HEARTBEAT_INTERVAL_SECS",
    "DEFAULT_RECONNECT_DELAY_SECS",
    "DEFAULT_MAX_RECONNECT_ATTEMPTS",
    "DEFAULT_CONNECTION_TIMEOUT_SECS",
    "DEFAULT_AUTH_TIMEOUT_SECS",
    "DEFAULT_REQUEST_TIMEOUT_SECS",
    "DEFAULT_SESSION_TIMEOUT_SECS",
    "DEFAULT_MAX_RETRIES",
    # Exceptions
    "BrokerAbstractionError",
    "BrokerNotRegisteredError",
    "BrokerAlreadyRegisteredError",
    "BrokerNotConnectedError",
    "BrokerAuthenticationError",
    "BrokerSessionExpiredError",
    "BrokerCapabilityNotSupportedError",
    "BrokerValidationError",
    "BrokerConfigurationError",
    "BrokerConnectionError",
    "BrokerRegistryCapacityError",
    "BrokerHealthError",
    "BrokerRequestError",
    "BrokerManagerNotRunningError",
    "DuplicateBrokerError",
    # Capabilities
    "BrokerCapabilities",
    "ALL_CAPABILITIES",
    "make_capabilities",
    "make_capabilities_from_iterable",
    "find_brokers_by_capability",
    # Configuration
    "BrokerConfiguration",
    # Connection
    "BrokerConnection",
    "ConnectionPool",
    # Session
    "BrokerSession",
    "BrokerSessionManager",
    # Requests
    "BrokerRequest",
    "OrderRequest",
    "ModifyOrderRequest",
    "CancelOrderRequest",
    "PositionRequest",
    "FundsRequest",
    "MarginRequest",
    "StatusRequest",
    "make_order_request",
    "make_modify_order_request",
    "make_cancel_order_request",
    "make_position_request",
    "make_funds_request",
    "make_margin_request",
    "make_status_request",
    # Response
    "BrokerResponse",
    "make_success_response",
    "make_failure_response",
    "make_error_response",
    "make_retryable_error_response",
    "make_auth_failure_response",
    "make_network_failure_response",
    "make_rate_limit_response",
    # Health
    "BrokerHealthRecord",
    "BrokerHealthMonitor",
    "make_health_record",
    # Statistics
    "BrokerStatistics",
    "BrokerStatisticsStore",
    # History
    "BrokerHistory",
    # Events
    "BrokerEvent",
    "make_broker_registered_event",
    "make_broker_connected_event",
    "make_broker_disconnected_event",
    "make_authentication_succeeded_event",
    "make_authentication_failed_event",
    "make_session_expired_event",
    "make_reconnect_started_event",
    "make_reconnect_succeeded_event",
    "make_health_changed_event",
    # Validation
    "BrokerValidationResult",
    "BrokerValidator",
    # Factory
    "BrokerFactory",
]
