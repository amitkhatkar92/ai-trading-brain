"""iios/execution/recovery/lifecycle/exceptions.py
==================================================
Exception hierarchy for C7 Execution Recovery Lifecycle.

Error codes: RC-000 … RC-007

C7 Execution Recovery & Resilience — Phase 1, Module 1
"""
from __future__ import annotations

from typing import Sequence

from iios.common.errors.exceptions import IIOSError


class RecoveryError(IIOSError):
    """Base class for all Recovery Lifecycle errors.  Code: RC-000."""

    error_code: str = "RC-000"

    def __init__(self, message: str = "Recovery error.") -> None:
        super().__init__(message, code=self.error_code)


class RecoveryNotRunningError(RecoveryError):
    """RecoveryLifecycle engine is not running.  Code: RC-001."""

    error_code = "RC-001"

    def __init__(self) -> None:
        super().__init__(
            "RecoveryLifecycle is not running. Call start() before using the API."
        )


class RecoveryAlreadyRunningError(RecoveryError):
    """RecoveryLifecycle engine is already running.  Code: RC-002."""

    error_code = "RC-002"

    def __init__(self) -> None:
        super().__init__("RecoveryLifecycle is already running.")


class RecoverySessionNotFoundError(RecoveryError):
    """A recovery session with the given ID was not found.  Code: RC-003."""

    error_code = "RC-003"

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        super().__init__(f"Recovery session not found: {session_id!r}")


class RecoveryInvalidTransitionError(RecoveryError):
    """A state transition was rejected by the state machine.  Code: RC-004."""

    error_code = "RC-004"

    def __init__(self, from_state: str, to_state: str, session_id: str = "") -> None:
        self.from_state = from_state
        self.to_state   = to_state
        self.session_id = session_id
        msg = (
            f"Invalid transition from '{from_state}' to '{to_state}'"
            + (f" for session {session_id!r}" if session_id else "")
        )
        super().__init__(msg)


class RecoveryValidationError(RecoveryError):
    """Context or session validation failed.  Code: RC-005."""

    error_code = "RC-005"

    def __init__(
        self,
        message: str = "Recovery validation failed.",
        *,
        errors: Sequence[str] = (),
    ) -> None:
        self.errors: tuple[str, ...] = tuple(errors)
        full = f"{message}: {'; '.join(errors)}" if errors else message
        super().__init__(full)


class RecoverySessionAlreadyExistsError(RecoveryError):
    """A session with the given ID already exists in the registry.  Code: RC-006."""

    error_code = "RC-006"

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        super().__init__(f"Recovery session already exists: {session_id!r}")


class RecoveryHistoryError(RecoveryError):
    """History operation failed.  Code: RC-007."""

    error_code = "RC-007"

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"Recovery history error: {reason}")


class RecoverySessionTerminalError(RecoveryError):
    """A transition was attempted on a terminal session.  Code: RC-008."""

    error_code = "RC-008"

    def __init__(self, session_id: str, state: str) -> None:
        self.session_id = session_id
        self.state      = state
        super().__init__(
            f"Recovery session {session_id!r} is in terminal state '{state}' — "
            "no further transitions are allowed."
        )
