"""
exceptions.py — iios.supervisor.integration
---------------------------------------------
Typed exception hierarchy for the AI Supervisor Integration.

Error code prefix: SIN (Supervisor INtegration)

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 6
"""
from __future__ import annotations

from iios.common.errors.exceptions import IIOSError


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------


class SupervisorIntegrationError(IIOSError):
    """Base for all AI Supervisor Integration errors."""
    error_code = "SIN-000"

    def __init__(self, message: str = "", code: str | None = None) -> None:
        super().__init__(message, code=code or self.error_code)


# ---------------------------------------------------------------------------
# Specific errors
# ---------------------------------------------------------------------------


class SupervisorIntegrationNotRunningError(SupervisorIntegrationError):
    """Raised when a method requires the integration engine to be running."""
    error_code = "SIN-001"

    def __init__(self, message: str = "AI Supervisor Integration is not running") -> None:
        super().__init__(message)


class SupervisorIntegrationValidationError(SupervisorIntegrationError):
    """Raised when an integration request fails structural validation."""
    error_code = "SIN-002"


class SupervisorIntegrationWorkflowError(SupervisorIntegrationError):
    """Raised when the integration workflow pipeline encounters a fatal error."""
    error_code = "SIN-003"


class SupervisorIntegrationComponentError(SupervisorIntegrationError):
    """Raised when a required M1-M5 component is unavailable or fails."""
    error_code = "SIN-004"

    def __init__(
        self,
        message: str = "",
        component: str = "",
        code: str | None = None,
    ) -> None:
        super().__init__(message, code=code)
        self.component = component


class SupervisorIntegrationCapacityError(SupervisorIntegrationError):
    """Raised when the integration registry exceeds its capacity limit."""
    error_code = "SIN-005"

    def __init__(
        self,
        message: str = "",
        limit: int = 0,
        code: str | None = None,
    ) -> None:
        super().__init__(message, code=code)
        self.limit = limit


class SupervisorIntegrationRegistryError(SupervisorIntegrationError):
    """Raised when the integration registry operation fails."""
    error_code = "SIN-006"


class SupervisorIntegrationTimeoutError(SupervisorIntegrationError):
    """Raised when an integration workflow step exceeds its time budget."""
    error_code = "SIN-007"
