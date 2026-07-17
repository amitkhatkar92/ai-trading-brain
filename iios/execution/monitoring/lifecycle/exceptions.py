"""iios/execution/monitoring/lifecycle/exceptions.py
==================================================
Exception hierarchy for the Execution Monitoring Lifecycle.

Error code prefix: ML

C6 Execution Intelligence — Phase 6, Module 1
"""
from __future__ import annotations

from iios.common.errors.exceptions import IIOSError


class MonitoringLifecycleError(IIOSError):
    """Base exception for all monitoring lifecycle errors.  ML-000."""

    error_code = "ML-000"

    def __init__(self, message: str = "Monitoring lifecycle error.") -> None:
        super().__init__(message)


class MonitoringLifecycleNotRunningError(MonitoringLifecycleError):
    """Lifecycle engine is not running.  ML-001."""

    error_code = "ML-001"

    def __init__(self) -> None:
        super().__init__(
            "Monitoring lifecycle is not running. "
            "Call start() before performing lifecycle operations."
        )


class MonitoringSessionNotFoundError(MonitoringLifecycleError):
    """No session with the given ID exists.  ML-002."""

    error_code = "ML-002"

    def __init__(self, session_id: str) -> None:
        super().__init__(f"Monitoring session '{session_id}' not found.")
        self.session_id = session_id


class InvalidMonitoringTransitionError(MonitoringLifecycleError):
    """Requested state transition is not permitted.  ML-003."""

    error_code = "ML-003"

    def __init__(
        self, session_id: str, from_state: str, to_state: str
    ) -> None:
        super().__init__(
            f"Invalid monitoring transition for session '{session_id}': "
            f"{from_state} → {to_state}."
        )
        self.session_id = session_id
        self.from_state = from_state
        self.to_state   = to_state


class MonitoringSessionAlreadyExistsError(MonitoringLifecycleError):
    """A session with the same ID is already registered.  ML-004."""

    error_code = "ML-004"

    def __init__(self, session_id: str) -> None:
        super().__init__(
            f"Monitoring session '{session_id}' is already registered."
        )
        self.session_id = session_id


class MonitoringRegistryCapacityError(MonitoringLifecycleError):
    """Registry is at maximum capacity.  ML-005."""

    error_code = "ML-005"

    def __init__(self, max_count: int) -> None:
        super().__init__(
            f"Monitoring registry is at capacity ({max_count} sessions)."
        )
        self.max_count = max_count


class MonitoringValidationError(MonitoringLifecycleError):
    """Session context or transition failed validation.  ML-006."""

    error_code = "ML-006"

    def __init__(
        self,
        message: str = "Monitoring validation failed.",
        errors: tuple = (),
    ) -> None:
        super().__init__(message)
        self.errors = errors


class MonitoringSessionTerminalError(MonitoringLifecycleError):
    """Session is in a terminal state and cannot be transitioned.  ML-007."""

    error_code = "ML-007"

    def __init__(self, session_id: str, state: str) -> None:
        super().__init__(
            f"Monitoring session '{session_id}' is in terminal state '{state}'."
        )
        self.session_id = session_id
        self.state      = state
