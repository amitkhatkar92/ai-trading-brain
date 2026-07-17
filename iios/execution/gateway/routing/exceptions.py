"""iios/execution/gateway/routing/exceptions.py
==================================================
Exception hierarchy for the IIOS Routing Framework.

Error code prefix: RF

C6 Execution Intelligence — Phase 5, Module 4
"""
from __future__ import annotations

from iios.common.errors.exceptions import IIOSError


class RoutingFrameworkError(IIOSError):
    """Base exception for all Routing Framework errors.  RF-000."""

    error_code = "RF-000"

    def __init__(self, message: str = "Routing framework error.") -> None:
        super().__init__(message)


class RoutingEngineNotRunningError(RoutingFrameworkError):
    """RoutingEngine is not in RUNNING state.  RF-001."""

    error_code = "RF-001"

    def __init__(self) -> None:
        super().__init__(
            "RoutingEngine is not running. "
            "Call start() before submitting routing requests."
        )


class RoutingRequestError(RoutingFrameworkError):
    """A routing request is invalid or could not be processed.  RF-002."""

    error_code = "RF-002"

    def __init__(self, reason: str = "") -> None:
        msg = "Routing request error."
        if reason:
            msg = f"Routing request error: {reason}"
        super().__init__(msg)
        self.reason = reason


class RoutingPolicyNotFoundError(RoutingFrameworkError):
    """No policy with the given ID is registered.  RF-003."""

    error_code = "RF-003"

    def __init__(self, policy_id: str) -> None:
        super().__init__(
            f"Routing policy '{policy_id}' is not registered."
        )
        self.policy_id = policy_id


class NoBrokersAvailableError(RoutingFrameworkError):
    """No broker candidates are available for routing.  RF-004."""

    error_code = "RF-004"

    def __init__(self, reason: str = "") -> None:
        msg = "No broker candidates are available for routing."
        if reason:
            msg = f"No broker candidates available: {reason}"
        super().__init__(msg)
        self.reason = reason


class RoutingValidationError(RoutingFrameworkError):
    """Routing validation failed.  RF-005."""

    error_code = "RF-005"

    def __init__(self, message: str, errors: tuple[str, ...] = ()) -> None:
        super().__init__(message)
        self.errors = errors


class PolicyAlreadyRegisteredError(RoutingFrameworkError):
    """A policy with the same ID is already registered.  RF-006."""

    error_code = "RF-006"

    def __init__(self, policy_id: str) -> None:
        super().__init__(
            f"Routing policy '{policy_id}' is already registered."
        )
        self.policy_id = policy_id


class CandidateNotFoundError(RoutingFrameworkError):
    """No candidate with the given broker_id is registered.  RF-007."""

    error_code = "RF-007"

    def __init__(self, broker_id: str) -> None:
        super().__init__(
            f"Routing candidate for broker '{broker_id}' is not registered."
        )
        self.broker_id = broker_id


class CandidateAlreadyRegisteredError(RoutingFrameworkError):
    """A candidate with the same broker_id is already registered.  RF-008."""

    error_code = "RF-008"

    def __init__(self, broker_id: str) -> None:
        super().__init__(
            f"Routing candidate for broker '{broker_id}' is already registered."
        )
        self.broker_id = broker_id


class RoutingPolicyError(RoutingFrameworkError):
    """A routing policy raised an error during evaluation.  RF-009."""

    error_code = "RF-009"

    def __init__(self, policy_id: str, reason: str = "") -> None:
        msg = f"Routing policy '{policy_id}' failed during evaluation."
        if reason:
            msg = f"Routing policy '{policy_id}' failed: {reason}"
        super().__init__(msg)
        self.policy_id = policy_id
        self.reason    = reason


class RoutingRegistryCapacityError(RoutingFrameworkError):
    """The routing registry has reached maximum capacity.  RF-010."""

    error_code = "RF-010"

    def __init__(self, resource: str, max_count: int) -> None:
        super().__init__(
            f"Routing registry '{resource}' is at capacity (max={max_count})."
        )
        self.resource  = resource
        self.max_count = max_count
