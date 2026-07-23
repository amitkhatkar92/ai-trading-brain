"""
exceptions.py — iios.market.integration
=========================================
Exception hierarchy for the Market Integration subsystem.

Error-code prefix: MI (Market Integration).

C12 Market Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

from iios.common.errors.exceptions import IIOSError


class MarketIntegrationError(IIOSError):
    """Base exception for the Market Integration subsystem (MI-000)."""
    error_code: str = "MI-000"

    def __init__(self, message: str = "", *, code: str | None = None) -> None:
        super().__init__(
            message or "Market integration error",
            code=code or self.error_code,
        )


class MarketIntegrationNotRunningError(MarketIntegrationError):
    """Integration engine has not been started (MI-001)."""
    error_code = "MI-001"

    def __init__(self, message: str = "") -> None:
        super().__init__(
            message or "MarketIntegrationEngine is not running",
            code=self.error_code,
        )


class MarketIntegrationRequestError(MarketIntegrationError):
    """Invalid or malformed integration request (MI-002)."""
    error_code = "MI-002"

    def __init__(self, message: str = "", *, request_id: str = "") -> None:
        self.request_id = request_id
        detail = f" (request_id={request_id!r})" if request_id else ""
        super().__init__(
            f"Integration request error{detail}: {message}",
            code=self.error_code,
        )


class MarketIntegrationValidationError(MarketIntegrationError):
    """Request fails integration-level validation (MI-003)."""
    error_code = "MI-003"

    def __init__(
        self,
        message: str = "",
        *,
        request_id: str = "",
        failed_checks: tuple = (),
    ) -> None:
        self.request_id    = request_id
        self.failed_checks = failed_checks
        detail = f" (request_id={request_id!r})" if request_id else ""
        super().__init__(
            f"Integration validation failed{detail}: {message}",
            code=self.error_code,
        )


class MarketIntegrationNotFoundError(MarketIntegrationError):
    """Integration record not found (MI-004)."""
    error_code = "MI-004"

    def __init__(self, integration_id: str = "") -> None:
        self.integration_id = integration_id
        super().__init__(
            f"Integration record not found: {integration_id!r}",
            code=self.error_code,
        )


class MarketIntegrationSubsystemError(MarketIntegrationError):
    """A downstream subsystem raised an error (MI-005)."""
    error_code = "MI-005"

    def __init__(
        self,
        message: str = "",
        *,
        subsystem: str = "",
        cause: str = "",
    ) -> None:
        self.subsystem = subsystem
        self.cause     = cause
        parts = [message or "Subsystem error"]
        if subsystem:
            parts.append(f"subsystem={subsystem!r}")
        if cause:
            parts.append(f"cause={cause!r}")
        super().__init__("; ".join(parts), code=self.error_code)


class MarketIntegrationCapacityError(MarketIntegrationError):
    """Registry or queue capacity exceeded (MI-006)."""
    error_code = "MI-006"

    def __init__(self, limit: int = 0) -> None:
        self.limit = limit
        super().__init__(
            f"Integration capacity exceeded (limit={limit})",
            code=self.error_code,
        )


class MarketIntegrationConfigurationError(MarketIntegrationError):
    """Integration component misconfiguration (MI-007)."""
    error_code = "MI-007"

    def __init__(self, message: str = "") -> None:
        super().__init__(
            message or "Integration configuration error",
            code=self.error_code,
        )


class MarketIntegrationSnapshotError(MarketIntegrationError):
    """Error building or publishing MarketSnapshot (MI-008)."""
    error_code = "MI-008"

    def __init__(self, message: str = "", *, snapshot_id: str = "") -> None:
        self.snapshot_id = snapshot_id
        detail = f" (snapshot_id={snapshot_id!r})" if snapshot_id else ""
        super().__init__(
            f"Integration snapshot error{detail}: {message}",
            code=self.error_code,
        )


class MarketIntegrationHistoryError(MarketIntegrationError):
    """Error accessing integration history (MI-009)."""
    error_code = "MI-009"

    def __init__(self, message: str = "") -> None:
        super().__init__(
            message or "Integration history error",
            code=self.error_code,
        )
