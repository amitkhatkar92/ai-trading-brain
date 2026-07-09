"""iios/execution/brokers/__init__.py"""
from __future__ import annotations

from iios.execution.brokers.broker_constants import (
    AuthMethod,
    BrokerCapabilityType,
    BrokerEnvironment,
    BrokerStatus,
    ConnectionStatus,
    RetryPolicy,
)
from iios.execution.brokers.broker_context import (
    BrokerContextState,
    broker_operation_context,
)
from iios.execution.brokers.broker_exceptions import (
    AdapterLoadFailedError,
    BrokerAlreadyExistsError,
    BrokerAuthenticationError,
    BrokerCapabilityError,
    BrokerConnectionError,
    BrokerError,
    BrokerFrameworkError,
    BrokerManagerError,
    BrokerNotFoundError,
    CapabilityNotSupportedError,
    CircuitOpenError,
    InvalidAdapterError,
)
from iios.execution.brokers.broker_factory import BrokerFactory
from iios.execution.brokers.broker_manager import (
    BrokerManager,
    get_broker_manager,
    reset_broker_manager,
)
from iios.execution.brokers.broker_registry import (
    BrokerRegistry,
    get_broker_registry,
    reset_broker_registry,
)
from iios.execution.brokers.core.base_broker_adapter import (
    BaseBrokerAdapter,
    BrokerAdapterConfig,
)
from iios.execution.brokers.core.broker_capability import (
    BrokerCapability,
    BrokerCapabilitySet,
)
from iios.execution.brokers.core.broker_connection import BrokerConnection
from iios.execution.brokers.core.broker_request import BrokerRequest
from iios.execution.brokers.core.broker_response import BrokerResponse
from iios.execution.brokers.core.broker_session import BrokerSession

__all__ = [
    # Constants
    "AuthMethod",
    "BrokerCapabilityType",
    "BrokerEnvironment",
    "BrokerStatus",
    "ConnectionStatus",
    "RetryPolicy",
    # Context
    "BrokerContextState",
    "broker_operation_context",
    # Exceptions
    "AdapterLoadFailedError",
    "BrokerAlreadyExistsError",
    "BrokerAuthenticationError",
    "BrokerCapabilityError",
    "BrokerConnectionError",
    "BrokerError",
    "BrokerFrameworkError",
    "BrokerManagerError",
    "BrokerNotFoundError",
    "CapabilityNotSupportedError",
    "CircuitOpenError",
    "InvalidAdapterError",
    # Core models
    "BaseBrokerAdapter",
    "BrokerAdapterConfig",
    "BrokerCapability",
    "BrokerCapabilitySet",
    "BrokerConnection",
    "BrokerRequest",
    "BrokerResponse",
    "BrokerSession",
    # Orchestration
    "BrokerFactory",
    "BrokerManager",
    "BrokerRegistry",
    "get_broker_manager",
    "reset_broker_manager",
    "get_broker_registry",
    "reset_broker_registry",
]
