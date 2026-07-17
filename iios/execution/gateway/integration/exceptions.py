"""iios/execution/gateway/integration/exceptions.py
==================================================
Exception hierarchy for the Execution Gateway Integration Layer.

Error code prefix: GI

C6 Execution Intelligence — Phase 5, Module 6
"""
from __future__ import annotations

from iios.common.errors.exceptions import IIOSError


class GatewayIntegrationError(IIOSError):
    """Base exception for all Integration layer errors.  GI-000."""

    error_code = "GI-000"

    def __init__(self, message: str = "Gateway integration error.") -> None:
        super().__init__(message)


class IntegrationNotRunningError(GatewayIntegrationError):
    """Operation requires RUNNING state.  GI-001."""

    error_code = "GI-001"

    def __init__(self) -> None:
        super().__init__(
            "Gateway integration engine is not running. "
            "Call start() before submitting requests."
        )


class IntegrationRequestValidationError(GatewayIntegrationError):
    """Integration request or context failed validation.  GI-002."""

    error_code = "GI-002"

    def __init__(
        self,
        message: str = "Integration request validation failed.",
        errors: tuple = (),
    ) -> None:
        super().__init__(message)
        self.errors = errors


class IntegrationRequestNotFoundError(GatewayIntegrationError):
    """No request with the given ID exists.  GI-003."""

    error_code = "GI-003"

    def __init__(self, request_id: str) -> None:
        super().__init__(f"Integration request '{request_id}' not found.")
        self.request_id = request_id


class ComponentNotRegisteredError(GatewayIntegrationError):
    """Required gateway component is not registered.  GI-004."""

    error_code = "GI-004"

    def __init__(self, component_type: str) -> None:
        super().__init__(
            f"Gateway component '{component_type}' is not registered. "
            "Call initialize() before start()."
        )
        self.component_type = component_type


class ComponentNotHealthyError(GatewayIntegrationError):
    """Required gateway component is not in a healthy state.  GI-005."""

    error_code = "GI-005"

    def __init__(self, component_type: str, detail: str = "") -> None:
        msg = f"Gateway component '{component_type}' is not healthy."
        if detail:
            msg = f"{msg} {detail}"
        super().__init__(msg)
        self.component_type = component_type


class IntegrationCapacityError(GatewayIntegrationError):
    """Integration registry is at maximum capacity.  GI-006."""

    error_code = "GI-006"

    def __init__(self, max_count: int) -> None:
        super().__init__(
            f"Integration registry is at capacity ({max_count} requests). "
            "Archive older requests before submitting new ones."
        )
        self.max_count = max_count


class IntegrationWorkflowError(GatewayIntegrationError):
    """A workflow step failed unexpectedly.  GI-007."""

    error_code = "GI-007"

    def __init__(self, step: str, reason: str = "") -> None:
        msg = f"Integration workflow failed at step '{step}'."
        if reason:
            msg = f"{msg} Reason: {reason}"
        super().__init__(msg)
        self.step = step
        self.reason = reason


class SubsystemNotInitializedError(GatewayIntegrationError):
    """Subsystem has not been initialized.  GI-008."""

    error_code = "GI-008"

    def __init__(self) -> None:
        super().__init__(
            "Gateway integration subsystem is not initialized. "
            "Call initialize() first."
        )
