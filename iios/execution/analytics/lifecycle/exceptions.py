"""
iios/execution/analytics/lifecycle/exceptions.py
================================================
Exception hierarchy for C8 Execution Analytics Lifecycle.

Error codes: AL-000 … AL-007

C8 Execution Analytics & Intelligence — Phase 1, Module 1
"""
from __future__ import annotations

from typing import Sequence

from iios.common.errors.exceptions import IIOSError


class AnalyticsError(IIOSError):
    """Base class for all Analytics Lifecycle errors.  Code: AL-000."""

    error_code: str = "AL-000"

    def __init__(self, message: str = "Analytics lifecycle error.") -> None:
        super().__init__(message, code=self.error_code)


class AnalyticsNotRunningError(AnalyticsError):
    """AnalyticsLifecycle engine is not running.  Code: AL-001."""

    error_code = "AL-001"

    def __init__(self) -> None:
        super().__init__(
            "AnalyticsLifecycle is not running. Call start() before using the API."
        )


class AnalyticsSessionNotFoundError(AnalyticsError):
    """An analytics session with the given ID was not found.  Code: AL-002."""

    error_code = "AL-002"

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        super().__init__(f"Analytics session not found: {session_id!r}")


class AnalyticsInvalidTransitionError(AnalyticsError):
    """A state transition was rejected by the state machine.  Code: AL-003."""

    error_code = "AL-003"

    def __init__(
        self,
        from_state: str,
        to_state:   str,
        session_id: str = "",
    ) -> None:
        self.from_state = from_state
        self.to_state   = to_state
        self.session_id = session_id
        msg = (
            f"Invalid transition from '{from_state}' to '{to_state}'"
            + (f" for session {session_id!r}" if session_id else "")
        )
        super().__init__(msg)


class AnalyticsValidationError(AnalyticsError):
    """Context or session validation failed.  Code: AL-004."""

    error_code = "AL-004"

    def __init__(
        self,
        message: str = "Analytics validation failed.",
        *,
        errors: Sequence[str] = (),
    ) -> None:
        self.errors: tuple[str, ...] = tuple(errors)
        full = f"{message}: {'; '.join(errors)}" if errors else message
        super().__init__(full)


class AnalyticsSessionAlreadyExistsError(AnalyticsError):
    """A session with the given ID already exists in the registry.  Code: AL-005."""

    error_code = "AL-005"

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        super().__init__(f"Analytics session already exists: {session_id!r}")


class AnalyticsSessionTerminalError(AnalyticsError):
    """Attempted to transition a terminal session.  Code: AL-006."""

    error_code = "AL-006"

    def __init__(self, session_id: str, state: str) -> None:
        self.session_id = session_id
        self.state = state
        super().__init__(
            f"Analytics session {session_id!r} is in terminal state {state!r}."
        )


class AnalyticsHistoryError(AnalyticsError):
    """History operation failed.  Code: AL-007."""

    error_code = "AL-007"
