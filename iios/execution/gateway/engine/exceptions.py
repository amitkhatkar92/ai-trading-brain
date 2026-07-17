"""iios/execution/gateway/engine/exceptions.py
==================================================
Exception hierarchy for the IIOS Execution Gateway Engine.

Error code prefix: EGE

C6 Execution Intelligence — Phase 5, Module 2
"""
from __future__ import annotations

from iios.common.errors.exceptions import IIOSError


class ExecutionGatewayEngineError(IIOSError):
    """Base exception for all Execution Gateway Engine errors.  EGE-000."""

    error_code = "EGE-000"

    def __init__(self, message: str = "Execution gateway engine error.") -> None:
        super().__init__(message)


class GatewayEngineNotRunningError(ExecutionGatewayEngineError):
    """Engine is not in RUNNING state.  EGE-001."""

    error_code = "EGE-001"

    def __init__(self) -> None:
        super().__init__(
            "Execution gateway engine is not running. "
            "Call start() before submitting requests."
        )


class GatewayRequestSubmissionError(ExecutionGatewayEngineError):
    """A request could not be submitted to the engine.  EGE-002."""

    error_code = "EGE-002"

    def __init__(self, reason: str = "") -> None:
        msg = "Gateway request submission failed."
        if reason:
            msg = f"Gateway request submission failed: {reason}"
        super().__init__(msg)
        self.reason = reason


class GatewayDispatchError(ExecutionGatewayEngineError):
    """Dispatch to broker abstraction failed.  EGE-003."""

    error_code = "EGE-003"

    def __init__(self, request_id: str, reason: str = "") -> None:
        msg = f"Gateway dispatch failed for request '{request_id}'."
        if reason:
            msg = f"Gateway dispatch failed for request '{request_id}': {reason}"
        super().__init__(msg)
        self.request_id = request_id
        self.reason = reason


class GatewayQueueFullError(ExecutionGatewayEngineError):
    """A queue has reached its maximum capacity.  EGE-004."""

    error_code = "EGE-004"

    def __init__(self, queue_type: str, max_size: int) -> None:
        super().__init__(
            f"Gateway {queue_type} queue is full (max_size={max_size}). "
            "Reduce load or increase queue capacity."
        )
        self.queue_type = queue_type
        self.max_size = max_size


class GatewaySessionNotFoundError(ExecutionGatewayEngineError):
    """A session with the given ID was not found.  EGE-005."""

    error_code = "EGE-005"

    def __init__(self, session_id: str) -> None:
        super().__init__(f"Gateway session not found: '{session_id}'.")
        self.session_id = session_id


class GatewaySessionExpiredError(ExecutionGatewayEngineError):
    """A session has expired and can no longer accept requests.  EGE-006."""

    error_code = "EGE-006"

    def __init__(self, session_id: str) -> None:
        super().__init__(f"Gateway session has expired: '{session_id}'.")
        self.session_id = session_id


class GatewayValidationFailedError(ExecutionGatewayEngineError):
    """Request or context validation failed.  EGE-007."""

    error_code = "EGE-007"

    def __init__(self, message: str = "", errors: tuple[str, ...] = ()) -> None:
        full = message or "Gateway validation failed."
        if errors:
            full = f"{full} Errors: {'; '.join(errors)}"
        super().__init__(full)
        self.validation_errors = errors


class GatewayEngineRequestNotFoundError(ExecutionGatewayEngineError):
    """An engine request with the given ID was not found.  EGE-008."""

    error_code = "EGE-008"

    def __init__(self, request_id: str) -> None:
        super().__init__(f"Engine gateway request not found: '{request_id}'.")
        self.request_id = request_id


class DuplicateEngineRequestError(ExecutionGatewayEngineError):
    """A request with the given ID is already registered.  EGE-009."""

    error_code = "EGE-009"

    def __init__(self, request_id: str) -> None:
        super().__init__(
            f"Duplicate engine gateway request: '{request_id}' is already registered."
        )
        self.request_id = request_id


class GatewayRegistryCapacityError(ExecutionGatewayEngineError):
    """The engine registry is at maximum capacity.  EGE-010."""

    error_code = "EGE-010"

    def __init__(self, max_capacity: int) -> None:
        super().__init__(
            f"Engine registry is at capacity (max={max_capacity}). "
            "Archive completed requests to free capacity."
        )
        self.max_capacity = max_capacity
