"""
exceptions.py — iios.portfolio.integration
===========================================
Exception hierarchy for the Portfolio Integration subsystem.

Error-code prefix: PI (Portfolio Integration)

C10 Portfolio Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

from iios.common.errors.exceptions import IIOSError


class PortfolioIntegrationError(IIOSError):
    """Base error for the Portfolio Integration subsystem."""
    error_code: str = "PI-000"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message, code=code or self.error_code)


class IntegrationNotReadyError(PortfolioIntegrationError):
    """Raised when an operation is requested before the engine is running."""
    error_code = "PI-001"

    def __init__(self, message: str = "Integration engine is not running") -> None:
        super().__init__(message, code=self.error_code)


class IntegrationRequestError(PortfolioIntegrationError):
    """Raised when a request is malformed or missing required fields."""
    error_code = "PI-002"

    def __init__(self, message: str, *, portfolio_id: str = "") -> None:
        self.portfolio_id = portfolio_id
        super().__init__(message, code=self.error_code)


class IntegrationValidationError(PortfolioIntegrationError):
    """Raised when integration validation fails."""
    error_code = "PI-003"

    def __init__(self, message: str, *, failed_checks: tuple = ()) -> None:
        self.failed_checks = failed_checks
        super().__init__(message, code=self.error_code)


class IntegrationWorkflowError(PortfolioIntegrationError):
    """Raised when the integration workflow encounters an unrecoverable error."""
    error_code = "PI-004"

    def __init__(self, message: str, *, stage: str = "") -> None:
        self.stage = stage
        super().__init__(message, code=self.error_code)


class IntegrationComponentError(PortfolioIntegrationError):
    """Raised when a required subsystem component is unavailable or unhealthy."""
    error_code = "PI-005"

    def __init__(self, message: str, *, component: str = "") -> None:
        self.component = component
        super().__init__(message, code=self.error_code)


class IntegrationSnapshotError(PortfolioIntegrationError):
    """Raised when snapshot publication fails during the integration workflow."""
    error_code = "PI-006"

    def __init__(self, message: str, *, portfolio_id: str = "") -> None:
        self.portfolio_id = portfolio_id
        super().__init__(message, code=self.error_code)


class IntegrationHistoryError(PortfolioIntegrationError):
    """Raised when reading or writing integration history fails."""
    error_code = "PI-007"

    def __init__(self, message: str) -> None:
        super().__init__(message, code=self.error_code)


class IntegrationCapacityError(PortfolioIntegrationError):
    """Raised when the integration registry or history is at capacity."""
    error_code = "PI-008"

    def __init__(self, limit: int) -> None:
        self.limit = limit
        super().__init__(
            f"Integration capacity exceeded (limit={limit})", code=self.error_code
        )


class IntegrationTimeoutError(PortfolioIntegrationError):
    """Raised when an integration workflow step exceeds its time budget."""
    error_code = "PI-009"

    def __init__(self, message: str, *, timeout_s: float = 0.0) -> None:
        self.timeout_s = timeout_s
        super().__init__(message, code=self.error_code)
