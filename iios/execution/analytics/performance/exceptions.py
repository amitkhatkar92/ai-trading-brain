"""
iios/execution/analytics/performance/exceptions.py
==================================================
Exception hierarchy for the C8 Performance Analytics Framework.

Error codes: PA-000 … PA-008

C8 Execution Analytics & Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

from typing import Sequence

from iios.common.errors.exceptions import IIOSError


class PerformanceAnalyticsError(IIOSError):
    """Base class for all Performance Analytics errors.  Code: PA-000."""

    error_code: str = "PA-000"

    def __init__(self, message: str = "Performance analytics error.") -> None:
        super().__init__(message, code=self.error_code)


class PerformanceEngineNotRunningError(PerformanceAnalyticsError):
    """Engine is not running.  Code: PA-001."""

    error_code = "PA-001"

    def __init__(self) -> None:
        super().__init__(
            "PerformanceAnalyticsEngine is not running. Call start() first."
        )


class PerformanceRequestNotFoundError(PerformanceAnalyticsError):
    """Request not found.  Code: PA-002."""

    error_code = "PA-002"

    def __init__(self, request_id: str) -> None:
        self.request_id = request_id
        super().__init__(f"Performance request not found: {request_id!r}")


class PerformanceCalculationError(PerformanceAnalyticsError):
    """KPI calculation failed.  Code: PA-003."""

    error_code = "PA-003"

    def __init__(self, message: str = "KPI calculation failed.", kpi: str = "") -> None:
        self.kpi = kpi
        super().__init__(message)


class PerformanceValidationError(PerformanceAnalyticsError):
    """Validation failed.  Code: PA-004."""

    error_code = "PA-004"

    def __init__(
        self,
        errors: Sequence[str] = (),
        message: str = "Performance validation failed.",
    ) -> None:
        self.errors: tuple[str, ...] = tuple(errors)
        full = f"{message}: {'; '.join(errors)}" if errors else message
        super().__init__(full)


class PerformanceDataInsufficientError(PerformanceAnalyticsError):
    """Insufficient data for analysis.  Code: PA-005."""

    error_code = "PA-005"

    def __init__(self, message: str = "Insufficient data for performance analysis.") -> None:
        super().__init__(message)


class PerformanceBenchmarkError(PerformanceAnalyticsError):
    """Benchmark comparison failed.  Code: PA-006."""

    error_code = "PA-006"

    def __init__(self, message: str = "Benchmark comparison failed.") -> None:
        super().__init__(message)


class PerformanceTrendError(PerformanceAnalyticsError):
    """Trend analysis failed.  Code: PA-007."""

    error_code = "PA-007"

    def __init__(self, message: str = "Trend analysis failed.") -> None:
        super().__init__(message)


class PerformanceAggregationError(PerformanceAnalyticsError):
    """Aggregation failed.  Code: PA-008."""

    error_code = "PA-008"

    def __init__(self, message: str = "Performance aggregation failed.") -> None:
        super().__init__(message)
