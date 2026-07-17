"""iios/execution/monitoring/metrics/exceptions.py
==================================================
Exception hierarchy for the Execution Metrics Framework.

Error code prefix: MF

C6 Execution Intelligence — Phase 6, Module 3
"""
from __future__ import annotations

from iios.common.errors.exceptions import IIOSError


class MetricsFrameworkError(IIOSError):
    """Base exception for all metrics framework errors.  MF-000."""

    error_code = "MF-000"

    def __init__(self, message: str = "Metrics framework error.") -> None:
        super().__init__(message)


class MetricsEngineNotRunningError(MetricsFrameworkError):
    """Metrics engine is not running.  MF-001."""

    error_code = "MF-001"

    def __init__(self) -> None:
        super().__init__(
            "Metrics engine is not running. "
            "Call start() before performing metrics operations."
        )


class MetricSeriesNotFoundError(MetricsFrameworkError):
    """No metric series with the given ID exists.  MF-002."""

    error_code = "MF-002"

    def __init__(self, series_id: str) -> None:
        super().__init__(f"Metric series '{series_id}' not found.")
        self.series_id = series_id


class MetricCalculationError(MetricsFrameworkError):
    """A metric calculation failed.  MF-003."""

    error_code = "MF-003"

    def __init__(
        self,
        metric_type: str = "",
        reason: str = "",
    ) -> None:
        msg = f"Metric calculation failed for '{metric_type}'"
        if reason:
            msg += f": {reason}"
        super().__init__(msg + ".")
        self.metric_type = metric_type
        self.reason      = reason


class MetricAggregationError(MetricsFrameworkError):
    """A metric aggregation failed.  MF-004."""

    error_code = "MF-004"

    def __init__(
        self,
        window: str = "",
        reason: str = "",
    ) -> None:
        msg = f"Metric aggregation failed for window '{window}'"
        if reason:
            msg += f": {reason}"
        super().__init__(msg + ".")
        self.window = window
        self.reason = reason


class MetricsRegistryCapacityError(MetricsFrameworkError):
    """Registry is at maximum capacity.  MF-005."""

    error_code = "MF-005"

    def __init__(self, max_count: int) -> None:
        super().__init__(
            f"Metrics registry is at capacity ({max_count} series)."
        )
        self.max_count = max_count


class MetricsValidationError(MetricsFrameworkError):
    """Request or context failed validation.  MF-006."""

    error_code = "MF-006"

    def __init__(
        self,
        message: str = "Metrics validation failed.",
        errors: tuple = (),
    ) -> None:
        super().__init__(message)
        self.errors = errors


class MetricsSnapshotError(MetricsFrameworkError):
    """Snapshot creation failed.  MF-007."""

    error_code = "MF-007"

    def __init__(self, reason: str = "") -> None:
        msg = "Snapshot creation failed"
        if reason:
            msg += f": {reason}"
        super().__init__(msg + ".")
        self.reason = reason


class InsufficientDataError(MetricsFrameworkError):
    """Insufficient data points for the requested computation.  MF-008."""

    error_code = "MF-008"

    def __init__(self, required: int = 0, available: int = 0) -> None:
        super().__init__(
            f"Insufficient data: required {required} points, have {available}."
        )
        self.required  = required
        self.available = available
