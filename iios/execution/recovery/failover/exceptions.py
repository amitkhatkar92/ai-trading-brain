"""
iios/execution/recovery/failover/exceptions.py
==============================================
Exception hierarchy for the Execution Failover Framework.

Error codes: FO-000 … FO-009

C7 Execution Recovery & Resilience — Phase 1, Module 4
"""
from __future__ import annotations

from iios.common.errors.exceptions import IIOSError


class FailoverError(IIOSError):
    """Base exception for the Failover Framework."""
    error_code = "FO-000"
    def __init__(self, message: str = "Failover error", *,
                 context=None, correlation_id: str = "") -> None:
        super().__init__(message, code=self.error_code,
                         context=context, correlation_id=correlation_id)


class FailoverNotRunningError(FailoverError):
    """Raised when an operation requires the failover engine to be running."""
    error_code = "FO-001"
    def __init__(self) -> None:
        super().__init__("Failover engine is not running")


class FailoverValidationError(FailoverError):
    """Raised when a failover request or plan fails validation."""
    error_code = "FO-002"
    def __init__(self, message: str, *, errors: tuple = ()) -> None:
        super().__init__(message)
        self.errors = errors


class FailoverExecutionError(FailoverError):
    """Raised when failover execution encounters an unrecoverable error."""
    error_code = "FO-003"
    def __init__(self, message: str, *, action: str = "") -> None:
        super().__init__(message)
        self.action = action


class FailoverVerificationError(FailoverError):
    """Raised when post-failover verification cannot be completed."""
    error_code = "FO-004"
    def __init__(self, message: str, *, check_name: str = "") -> None:
        super().__init__(message)
        self.check_name = check_name


class FailoverPlanNotFoundError(FailoverError):
    """Raised when no plan is found for the requested failover type/action."""
    error_code = "FO-005"
    def __init__(self, action: str) -> None:
        super().__init__(f"No failover plan found for action: {action!r}")
        self.action = action


class FailoverResourceUnavailableError(FailoverError):
    """Raised when required resources are unavailable for failover."""
    error_code = "FO-006"
    def __init__(self, resource: str) -> None:
        super().__init__(f"Failover resource unavailable: {resource!r}")
        self.resource = resource


class FailoverTimeoutError(FailoverError):
    """Raised when failover execution exceeds the configured time limit."""
    error_code = "FO-007"
    def __init__(self, timeout_ms: float) -> None:
        super().__init__(f"Failover execution timed out after {timeout_ms:.0f}ms")
        self.timeout_ms = timeout_ms


class FailoverRegistryError(FailoverError):
    """Raised by the failover session registry."""
    error_code = "FO-008"
    def __init__(self, message: str) -> None:
        super().__init__(message)


class FailoverStrategyNotFoundError(FailoverError):
    """Raised when a failover strategy (plan) cannot be found in the registry."""
    error_code = "FO-009"
    def __init__(self, key: str) -> None:
        super().__init__(f"Failover strategy not found: {key!r}")
        self.key = key
