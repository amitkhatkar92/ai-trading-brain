"""iios/execution/positions/integration/exceptions.py
==================================================
Exception hierarchy for the IIOS Position Integration module.

Error codes: PI6-000 through PI6-009

C6 Execution Intelligence — Phase 3, Module 6
"""
from __future__ import annotations

from iios.common.errors.exceptions import IIOSError


class PositionIntegrationError(IIOSError):
    """PI6-000 — Base error for the Position Integration module."""

    def __init__(self, message: str, *, code: str = "PI6-000", context=None, correlation_id: str = "") -> None:
        super().__init__(message, code=code, context=context, correlation_id=correlation_id)


class PositionIntegrationNotRunningError(PositionIntegrationError):
    """
    PI6-001 — Operation attempted while the integration engine is not running.
    """

    def __init__(self) -> None:
        super().__init__(
            "PositionIntegrationEngine is not running",
            code="PI6-001",
        )


class PositionIntegrationInitError(PositionIntegrationError):
    """
    PI6-002 — Integration engine failed to initialize.

    Parameters
    ----------
    reason
        Human-readable reason for the initialization failure.
    """

    def __init__(self, reason: str) -> None:
        super().__init__(
            f"Integration initialization failed: {reason}",
            code="PI6-002",
        )
        self.reason = reason


class ComponentRegistrationError(PositionIntegrationError):
    """
    PI6-003 — A component could not be registered.

    Parameters
    ----------
    component_name
        The component that failed to register.
    """

    def __init__(self, component_name: str) -> None:
        super().__init__(
            f"Component registration failed: {component_name!r}",
            code="PI6-003",
        )
        self.component_name = component_name


class ComponentNotFoundError(PositionIntegrationError):
    """
    PI6-004 — A required component is not registered.

    Parameters
    ----------
    component_name
        The component that was requested but not found.
    """

    def __init__(self, component_name: str) -> None:
        super().__init__(
            f"Component not found: {component_name!r}",
            code="PI6-004",
        )
        self.component_name = component_name


class ComponentHealthError(PositionIntegrationError):
    """
    PI6-005 — A component health check failed critically.

    Parameters
    ----------
    component_name
        The component whose health check failed.
    """

    def __init__(self, component_name: str) -> None:
        super().__init__(
            f"Component health check failed: {component_name!r}",
            code="PI6-005",
        )
        self.component_name = component_name


class IntegrationValidationError(PositionIntegrationError):
    """
    PI6-006 — Subsystem validation failed.

    Parameters
    ----------
    message
        Validation failure description.
    errors
        Tuple of individual validation error messages.
    """

    def __init__(self, message: str, *, errors: tuple = ()) -> None:
        super().__init__(message, code="PI6-006")
        self.errors: tuple = errors


class IntegrationSnapshotError(PositionIntegrationError):
    """PI6-007 — Failed to produce an integration snapshot."""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="PI6-007")


class IntegrationRequestError(PositionIntegrationError):
    """PI6-008 — Malformed or invalid integration request."""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="PI6-008")


class IntegrationOperationError(PositionIntegrationError):
    """
    PI6-009 — A coordinated integration operation failed.

    Parameters
    ----------
    operation
        The operation type that failed.
    position_id
        Position involved (if applicable).
    """

    def __init__(self, message: str, *, operation: str = "", position_id: str = "") -> None:
        super().__init__(message, code="PI6-009")
        self.operation   = operation
        self.position_id = position_id
