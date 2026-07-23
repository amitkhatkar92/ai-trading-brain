"""
exceptions.py — iios.market.analytics
=======================================
Exception hierarchy for the Market Analytics & Intelligence Framework.

Error-code prefix: MA (Market Analytics).

C12 Market Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

from iios.common.errors.exceptions import IIOSError


class MarketAnalyticsError(IIOSError):
    """Base exception for the Market Analytics Framework (MA-000)."""
    error_code: str = "MA-000"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message, code=code or self.error_code)


class MarketAnalyticsEngineNotRunningError(MarketAnalyticsError):
    """Engine operation attempted before start() (MA-001)."""
    error_code = "MA-001"

    def __init__(self, message: str = "") -> None:
        super().__init__(
            message or "Market analytics engine is not running — call start() first",
            code=self.error_code,
        )


class MarketAnalyticsValidationError(MarketAnalyticsError):
    """Request or output fails validation (MA-002)."""
    error_code = "MA-002"

    def __init__(
        self,
        message: str = "",
        *,
        failed_checks: tuple = (),
        analytics_id: str = "",
    ) -> None:
        detail = f" (analytics_id={analytics_id!r})" if analytics_id else ""
        super().__init__(
            f"Market analytics validation failed{detail}: {message}",
            code=self.error_code,
        )
        self.failed_checks = failed_checks
        self.analytics_id = analytics_id


class MarketAnalyticsNotApprovedError(MarketAnalyticsError):
    """Request was not approved by the Market Policy Framework (MA-003)."""
    error_code = "MA-003"

    def __init__(self, analytics_id: str = "") -> None:
        super().__init__(
            f"Market analytics request not policy-approved: {analytics_id!r}",
            code=self.error_code,
        )
        self.analytics_id = analytics_id


class MarketAnalyticsNotFoundError(MarketAnalyticsError):
    """Referenced analytics result not found (MA-004)."""
    error_code = "MA-004"

    def __init__(self, analytics_id: str) -> None:
        super().__init__(
            f"Market analytics result not found: {analytics_id!r}",
            code=self.error_code,
        )
        self.analytics_id = analytics_id


class MarketAnalyticsDataError(MarketAnalyticsError):
    """Insufficient or invalid market data (MA-005)."""
    error_code = "MA-005"

    def __init__(self, message: str = "") -> None:
        super().__init__(
            f"Market analytics data error: {message}",
            code=self.error_code,
        )


class MarketRegimeError(MarketAnalyticsError):
    """Regime detection error (MA-006)."""
    error_code = "MA-006"

    def __init__(self, message: str = "") -> None:
        super().__init__(
            f"Market regime error: {message}",
            code=self.error_code,
        )


class MarketForecastError(MarketAnalyticsError):
    """Forecast generation error (MA-007)."""
    error_code = "MA-007"

    def __init__(self, message: str = "") -> None:
        super().__init__(
            f"Market forecast error: {message}",
            code=self.error_code,
        )


class MarketAnalyticsRegistryError(MarketAnalyticsError):
    """Registry operation error (MA-008)."""
    error_code = "MA-008"

    def __init__(self, message: str = "") -> None:
        super().__init__(
            f"Market analytics registry error: {message}",
            code=self.error_code,
        )


class MarketAnalyticsCapacityError(MarketAnalyticsError):
    """Registry capacity exhausted (MA-009)."""
    error_code = "MA-009"

    def __init__(self, limit: int) -> None:
        super().__init__(
            f"Market analytics registry capacity exceeded (limit={limit})",
            code=self.error_code,
        )
        self.limit = limit
