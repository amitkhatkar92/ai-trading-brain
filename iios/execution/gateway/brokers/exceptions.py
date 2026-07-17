"""iios/execution/gateway/brokers/exceptions.py
==================================================
Exception hierarchy for the IIOS Broker Abstraction Layer.

Error code prefix: BAL

C6 Execution Intelligence — Phase 5, Module 3
"""
from __future__ import annotations

from iios.common.errors.exceptions import IIOSError


class BrokerAbstractionError(IIOSError):
    """Base exception for all Broker Abstraction Layer errors.  BAL-000."""

    error_code = "BAL-000"

    def __init__(self, message: str = "Broker abstraction layer error.") -> None:
        super().__init__(message)


class BrokerNotRegisteredError(BrokerAbstractionError):
    """No broker with the given ID is registered.  BAL-001."""

    error_code = "BAL-001"

    def __init__(self, broker_id: str) -> None:
        super().__init__(
            f"Broker '{broker_id}' is not registered. "
            "Call register_broker() before using this broker."
        )
        self.broker_id = broker_id


class BrokerAlreadyRegisteredError(BrokerAbstractionError):
    """A broker with the same ID is already registered.  BAL-002."""

    error_code = "BAL-002"

    def __init__(self, broker_id: str) -> None:
        super().__init__(
            f"Broker '{broker_id}' is already registered. "
            "Remove the existing registration before re-registering."
        )
        self.broker_id = broker_id


class BrokerNotConnectedError(BrokerAbstractionError):
    """Broker is not in a ready state for order operations.  BAL-003."""

    error_code = "BAL-003"

    def __init__(self, broker_id: str, current_status: str = "") -> None:
        status_part = f" (current status: {current_status})" if current_status else ""
        super().__init__(
            f"Broker '{broker_id}' is not connected{status_part}. "
            "Call connect() and authenticate() first."
        )
        self.broker_id      = broker_id
        self.current_status = current_status


class BrokerAuthenticationError(BrokerAbstractionError):
    """Authentication with the broker failed or session is invalid.  BAL-004."""

    error_code = "BAL-004"

    def __init__(self, broker_id: str, reason: str = "") -> None:
        msg = f"Authentication failed for broker '{broker_id}'."
        if reason:
            msg = f"Authentication failed for broker '{broker_id}': {reason}"
        super().__init__(msg)
        self.broker_id = broker_id
        self.reason    = reason


class BrokerSessionExpiredError(BrokerAbstractionError):
    """The broker session has expired and must be refreshed.  BAL-005."""

    error_code = "BAL-005"

    def __init__(self, broker_id: str) -> None:
        super().__init__(
            f"Session for broker '{broker_id}' has expired. "
            "Call refresh_session() to obtain a new session."
        )
        self.broker_id = broker_id


class BrokerCapabilityNotSupportedError(BrokerAbstractionError):
    """The requested capability is not supported by the broker.  BAL-006."""

    error_code = "BAL-006"

    def __init__(self, broker_id: str, capability: str) -> None:
        super().__init__(
            f"Broker '{broker_id}' does not support capability '{capability}'."
        )
        self.broker_id  = broker_id
        self.capability = capability


class BrokerValidationError(BrokerAbstractionError):
    """A broker registration or request failed validation.  BAL-007."""

    error_code = "BAL-007"

    def __init__(self, message: str, errors: tuple[str, ...] = ()) -> None:
        super().__init__(message)
        self.errors = errors


class BrokerConfigurationError(BrokerAbstractionError):
    """Invalid or missing broker configuration.  BAL-008."""

    error_code = "BAL-008"

    def __init__(self, broker_id: str, reason: str = "") -> None:
        msg = f"Invalid configuration for broker '{broker_id}'."
        if reason:
            msg = f"Invalid configuration for broker '{broker_id}': {reason}"
        super().__init__(msg)
        self.broker_id = broker_id
        self.reason    = reason


class BrokerConnectionError(BrokerAbstractionError):
    """A connection operation failed.  BAL-009."""

    error_code = "BAL-009"

    def __init__(self, broker_id: str, reason: str = "") -> None:
        msg = f"Connection error for broker '{broker_id}'."
        if reason:
            msg = f"Connection error for broker '{broker_id}': {reason}"
        super().__init__(msg)
        self.broker_id = broker_id
        self.reason    = reason


class BrokerRegistryCapacityError(BrokerAbstractionError):
    """The broker registry has reached maximum capacity.  BAL-010."""

    error_code = "BAL-010"

    def __init__(self, max_brokers: int) -> None:
        super().__init__(
            f"Broker registry is at capacity (max_brokers={max_brokers}). "
            "Remove an existing broker before registering a new one."
        )
        self.max_brokers = max_brokers


class BrokerHealthError(BrokerAbstractionError):
    """Health check for the broker failed.  BAL-011."""

    error_code = "BAL-011"

    def __init__(self, broker_id: str, reason: str = "") -> None:
        msg = f"Health check failed for broker '{broker_id}'."
        if reason:
            msg = f"Health check failed for broker '{broker_id}': {reason}"
        super().__init__(msg)
        self.broker_id = broker_id
        self.reason    = reason


class BrokerRequestError(BrokerAbstractionError):
    """A broker request could not be constructed or submitted.  BAL-012."""

    error_code = "BAL-012"

    def __init__(self, reason: str = "") -> None:
        msg = "Broker request error."
        if reason:
            msg = f"Broker request error: {reason}"
        super().__init__(msg)
        self.reason = reason


class BrokerManagerNotRunningError(BrokerAbstractionError):
    """BrokerManager is not in RUNNING state.  BAL-013."""

    error_code = "BAL-013"

    def __init__(self) -> None:
        super().__init__(
            "BrokerManager is not running. "
            "Call start() before using broker operations."
        )


class DuplicateBrokerError(BrokerAbstractionError):
    """Duplicate broker registration with conflicting state.  BAL-014."""

    error_code = "BAL-014"

    def __init__(self, broker_id: str) -> None:
        super().__init__(
            f"Duplicate broker registration attempted for '{broker_id}'."
        )
        self.broker_id = broker_id
