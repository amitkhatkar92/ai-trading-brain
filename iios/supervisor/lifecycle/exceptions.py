"""
exceptions.py — iios.supervisor.lifecycle
===========================================
Exception hierarchy for the Institutional AI Supervisor Lifecycle subsystem.

Error-code prefix: SL (Supervisor Lifecycle).

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 1
"""
from __future__ import annotations

from iios.common.errors.exceptions import IIOSError

from .constants import SupervisorState


class SupervisorLifecycleError(IIOSError):
    """
    Base error for the AI Supervisor Lifecycle subsystem (SL-000).

    All supervisor lifecycle exceptions derive from this class.
    """
    error_code: str = "SL-000"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message, code=code or self.error_code)


class SupervisorSessionNotFoundError(SupervisorLifecycleError):
    """Raised when a session_id lookup fails in the registry (SL-001)."""
    error_code = "SL-001"

    def __init__(self, session_id: str = "") -> None:
        detail = f" (session_id={session_id!r})" if session_id else ""
        super().__init__(
            f"Supervisor session not found{detail}",
            code=self.error_code,
        )
        self.session_id = session_id


class SupervisorInvalidTransitionError(SupervisorLifecycleError):
    """
    Raised when an attempted state transition is not permitted by the
    institutional supervisor state machine (SL-002).
    """
    error_code = "SL-002"

    def __init__(
        self,
        from_state: SupervisorState | str = "",
        to_state:   SupervisorState | str = "",
        session_id: str = "",
    ) -> None:
        from_v = from_state.value if isinstance(from_state, SupervisorState) else str(from_state)
        to_v   = to_state.value   if isinstance(to_state,   SupervisorState) else str(to_state)
        sid    = f", session_id={session_id!r}" if session_id else ""
        super().__init__(
            f"Invalid transition: {from_v!r} \u2192 {to_v!r}{sid}",
            code=self.error_code,
        )
        self.from_state = from_state
        self.to_state   = to_state
        self.session_id = session_id


class SupervisorSessionTerminatedError(SupervisorLifecycleError):
    """
    Raised when an operation is attempted on a session in an immutable
    (ARCHIVED) state (SL-003).
    """
    error_code = "SL-003"

    def __init__(self, session_id: str = "", state: str = "") -> None:
        st = f" (state={state!r})" if state else ""
        super().__init__(
            f"Supervisor session has terminated{st}",
            code=self.error_code,
        )
        self.session_id = session_id


class SupervisorLifecycleNotRunningError(SupervisorLifecycleError):
    """
    Raised when a lifecycle operation is attempted while the engine is
    not in RUNNING state (SL-004).
    """
    error_code = "SL-004"

    def __init__(self, message: str = "SupervisorLifecycle is not running") -> None:
        super().__init__(message, code=self.error_code)


class SupervisorCapacityExceededError(SupervisorLifecycleError):
    """
    Raised when the active-session limit or archive limit is breached (SL-005).
    """
    error_code = "SL-005"

    def __init__(self, limit: int = 0) -> None:
        super().__init__(
            f"Supervisor session capacity exceeded (limit={limit})",
            code=self.error_code,
        )
        self.limit = limit


class SupervisorValidationError(SupervisorLifecycleError):
    """Raised when a supervisor session fails structural validation (SL-006)."""
    error_code = "SL-006"

    def __init__(self, message: str = "Supervisor validation failed") -> None:
        super().__init__(message, code=self.error_code)


class SupervisorHistoryError(SupervisorLifecycleError):
    """Raised on history access/integrity failures (SL-007)."""
    error_code = "SL-007"

    def __init__(self, message: str = "Supervisor history error") -> None:
        super().__init__(message, code=self.error_code)


class SupervisorRegistryError(SupervisorLifecycleError):
    """Raised on registry constraint violations (SL-008)."""
    error_code = "SL-008"

    def __init__(self, message: str = "Supervisor registry error") -> None:
        super().__init__(message, code=self.error_code)


class SupervisorConfigurationError(SupervisorLifecycleError):
    """Raised when the lifecycle is misconfigured (SL-009)."""
    error_code = "SL-009"

    def __init__(self, message: str = "Supervisor configuration error") -> None:
        super().__init__(message, code=self.error_code)
