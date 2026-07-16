"""iios/execution/brokers/exceptions.py
==================================================
Exception hierarchy for the IIOS Broker Abstraction Layer.

All exceptions inherit from IIOSError.

Error Codes
-----------
BR-000  BrokerAbstractionError          — base
BR-001  BrokerRegistrationError         — registration failure
BR-002  BrokerNotFoundError             — broker_id not in registry
BR-003  DuplicateBrokerError            — duplicate broker_id
BR-004  BrokerCapacityError             — registry full
BR-005  BrokerNotConnectedError         — operation requires connection
BR-006  BrokerConnectionError           — connect/disconnect failure
BR-007  BrokerValidationError           — request / response validation failed
BR-008  BrokerCapabilityError           — capability not supported
BR-009  BrokerRequestError              — malformed request
BR-010  BrokerResponseError             — unexpected response
BR-011  BrokerHealthError               — health check failure
BR-012  BrokerNotRunningError           — manager/registry not started
BR-013  BrokerFactoryError              — factory cannot build broker

C6 Execution Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from iios.common.errors.exceptions import IIOSError


class BrokerAbstractionError(IIOSError):
    """Base for all Broker Abstraction Layer errors."""
    DEFAULT_CODE = "BR-000"


class BrokerRegistrationError(BrokerAbstractionError):
    """Broker registration failed."""
    DEFAULT_CODE = "BR-001"


class BrokerNotFoundError(BrokerAbstractionError):
    """No broker registered under the requested broker_id."""
    DEFAULT_CODE = "BR-002"

    def __init__(
        self,
        broker_id: str,
        *,
        code:           str = "BR-002",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            f"Broker not found: '{broker_id}'",
            code=code,
            context=context,
            correlation_id=correlation_id,
        )
        self.broker_id = broker_id


class DuplicateBrokerError(BrokerAbstractionError):
    """A broker with this ID is already registered."""
    DEFAULT_CODE = "BR-003"

    def __init__(
        self,
        broker_id: str,
        *,
        code:           str = "BR-003",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            f"Broker already registered: '{broker_id}'",
            code=code,
            context=context,
            correlation_id=correlation_id,
        )
        self.broker_id = broker_id


class BrokerCapacityError(BrokerAbstractionError):
    """Registry has reached maximum broker capacity."""
    DEFAULT_CODE = "BR-004"


class BrokerNotConnectedError(BrokerAbstractionError):
    """Operation requires an active connection."""
    DEFAULT_CODE = "BR-005"

    def __init__(
        self,
        broker_id: str,
        *,
        code:           str = "BR-005",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            f"Broker not connected: '{broker_id}'",
            code=code,
            context=context,
            correlation_id=correlation_id,
        )
        self.broker_id = broker_id


class BrokerConnectionError(BrokerAbstractionError):
    """Connect or disconnect operation failed."""
    DEFAULT_CODE = "BR-006"


class BrokerValidationError(BrokerAbstractionError):
    """Request or response validation failed."""
    DEFAULT_CODE = "BR-007"

    def __init__(
        self,
        message:        str,
        *,
        code:           str = "BR-007",
        errors:         tuple[str, ...] = (),
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(message, code=code, context=context,
                         correlation_id=correlation_id)
        self.errors = errors


class BrokerCapabilityError(BrokerAbstractionError):
    """Requested capability is not supported by this broker."""
    DEFAULT_CODE = "BR-008"

    def __init__(
        self,
        broker_id:  str,
        capability: str,
        *,
        code:           str = "BR-008",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            f"Broker '{broker_id}' does not support capability '{capability}'",
            code=code,
            context=context,
            correlation_id=correlation_id,
        )
        self.broker_id  = broker_id
        self.capability = capability


class BrokerRequestError(BrokerAbstractionError):
    """Malformed or incomplete broker request."""
    DEFAULT_CODE = "BR-009"


class BrokerResponseError(BrokerAbstractionError):
    """Unexpected or invalid broker response."""
    DEFAULT_CODE = "BR-010"


class BrokerHealthError(BrokerAbstractionError):
    """Health check encountered an error."""
    DEFAULT_CODE = "BR-011"


class BrokerNotRunningError(BrokerAbstractionError):
    """Manager or registry was not started before use."""
    DEFAULT_CODE = "BR-012"


class BrokerFactoryError(BrokerAbstractionError):
    """Factory could not construct the requested broker."""
    DEFAULT_CODE = "BR-013"
