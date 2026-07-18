"""
iios/execution/analytics/engine/exceptions.py
=============================================
Exception hierarchy for the C8 Execution Analytics Engine.

Error codes: AE-000 … AE-009

C8 Execution Analytics & Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

from typing import Sequence

from iios.common.errors.exceptions import IIOSError


class AnalyticsEngineError(IIOSError):
    """Base class for all Analytics Engine errors.  Code: AE-000."""

    error_code: str = "AE-000"

    def __init__(self, message: str = "Analytics engine error.") -> None:
        super().__init__(message, code=self.error_code)


class AnalyticsEngineNotRunningError(AnalyticsEngineError):
    """Engine is not running.  Code: AE-001."""

    error_code = "AE-001"

    def __init__(self) -> None:
        super().__init__(
            "ExecutionAnalyticsEngine is not running. Call start() before using the API."
        )


class AnalyticsEngineAlreadyRunningError(AnalyticsEngineError):
    """Engine is already running.  Code: AE-002."""

    error_code = "AE-002"

    def __init__(self) -> None:
        super().__init__("ExecutionAnalyticsEngine is already running.")


class AnalyticsRequestNotFoundError(AnalyticsEngineError):
    """A request with the given ID was not found.  Code: AE-003."""

    error_code = "AE-003"

    def __init__(self, request_id: str) -> None:
        self.request_id = request_id
        super().__init__(f"Analytics request not found: {request_id!r}")


class AnalyticsRequestValidationError(AnalyticsEngineError):
    """Request validation failed.  Code: AE-004."""

    error_code = "AE-004"

    def __init__(
        self,
        message: str = "Analytics request validation failed.",
        *,
        errors: Sequence[str] = (),
    ) -> None:
        self.errors: tuple[str, ...] = tuple(errors)
        full = f"{message}: {'; '.join(errors)}" if errors else message
        super().__init__(full)


class AnalyticsPipelineError(AnalyticsEngineError):
    """Pipeline coordination error.  Code: AE-005."""

    error_code = "AE-005"

    def __init__(
        self,
        message:     str = "Analytics pipeline error.",
        pipeline_id: str = "",
    ) -> None:
        self.pipeline_id = pipeline_id
        super().__init__(message)


class AnalyticsSessionManagerError(AnalyticsEngineError):
    """Session manager error.  Code: AE-006."""

    error_code = "AE-006"

    def __init__(self, message: str = "Analytics session manager error.") -> None:
        super().__init__(message)


class AnalyticsDispatchError(AnalyticsEngineError):
    """Dispatch error.  Code: AE-007."""

    error_code = "AE-007"

    def __init__(
        self,
        message:     str = "Analytics dispatch error.",
        pipeline_id: str = "",
    ) -> None:
        self.pipeline_id = pipeline_id
        super().__init__(message)


class AnalyticsSchedulerError(AnalyticsEngineError):
    """Scheduler error.  Code: AE-008."""

    error_code = "AE-008"

    def __init__(self, message: str = "Analytics scheduler error.") -> None:
        super().__init__(message)


class AnalyticsPublishError(AnalyticsEngineError):
    """Snapshot publish error.  Code: AE-009."""

    error_code = "AE-009"

    def __init__(self, message: str = "Analytics publish error.") -> None:
        super().__init__(message)
