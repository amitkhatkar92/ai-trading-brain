"""iios/execution/monitoring/integration/exceptions.py
==================================================
Exception hierarchy for the Execution Monitoring Integration subsystem.

Error codes: II-000 … II-009

C6 Execution Intelligence — Phase 6, Module 6
"""
from __future__ import annotations

from typing import Sequence

from iios.common.errors.exceptions import IIOSError


class IntegrationError(IIOSError):
    """Base class for all Integration subsystem errors.  Code: II-000."""

    error_code: str = "II-000"

    def __init__(self, message: str = "Integration error") -> None:
        super().__init__(message, code=self.error_code)


class IntegrationNotRunningError(IntegrationError):
    """Engine is not in RUNNING or DEGRADED state.  Code: II-001."""

    error_code = "II-001"

    def __init__(self) -> None:
        super().__init__(
            "ExecutionMonitoringIntegrationEngine is not running. "
            "Call start() before using the API."
        )


class IntegrationAlreadyRunningError(IntegrationError):
    """Engine is already running.  Code: II-002."""

    error_code = "II-002"

    def __init__(self) -> None:
        super().__init__(
            "ExecutionMonitoringIntegrationEngine is already running."
        )


class IntegrationRequestNotFoundError(IntegrationError):
    """A request with the given ID was not found.  Code: II-003."""

    error_code = "II-003"

    def __init__(self, request_id: str) -> None:
        self.request_id = request_id
        super().__init__(f"Integration request not found: {request_id!r}")


class IntegrationSessionNotFoundError(IntegrationError):
    """A session with the given ID was not found.  Code: II-004."""

    error_code = "II-004"

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        super().__init__(f"Integration session not found: {session_id!r}")


class IntegrationValidationError(IntegrationError):
    """Context or request validation failed.  Code: II-005."""

    error_code = "II-005"

    def __init__(
        self,
        message: str = "Validation failed",
        *,
        errors: Sequence[str] = (),
    ) -> None:
        self.errors: tuple[str, ...] = tuple(errors)
        full = f"{message}: {'; '.join(errors)}" if errors else message
        super().__init__(full)


class IntegrationComponentError(IntegrationError):
    """A sub-component raised an unexpected error.  Code: II-006."""

    error_code = "II-006"

    def __init__(self, component: str, reason: str) -> None:
        self.component = component
        self.reason    = reason
        super().__init__(f"Component '{component}' error: {reason}")


class IntegrationSnapshotError(IntegrationError):
    """Snapshot creation failed.  Code: II-007."""

    error_code = "II-007"

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"Integration snapshot error: {reason}")


class IntegrationWorkflowError(IntegrationError):
    """Workflow execution failed mid-flight.  Code: II-008."""

    error_code = "II-008"

    def __init__(self, step: str, reason: str) -> None:
        self.step   = step
        self.reason = reason
        super().__init__(f"Workflow step '{step}' failed: {reason}")


class IntegrationHealthError(IntegrationError):
    """Health check could not be completed.  Code: II-009."""

    error_code = "II-009"

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"Health check error: {reason}")
