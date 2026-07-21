"""
exceptions.py — iios.portfolio.lifecycle
==========================================
Exception hierarchy for the Institutional Portfolio Lifecycle subsystem.

Error-code prefix: PL (Portfolio Lifecycle).

C10 Portfolio Intelligence — Phase 1, Module 1
"""
from __future__ import annotations

from iios.common.errors.exceptions import IIOSError

from .constants import PortfolioState


class PortfolioLifecycleError(IIOSError):
    """
    Base error for the Institutional Portfolio Lifecycle subsystem (PL-000).

    All portfolio lifecycle exceptions derive from this class.
    """
    error_code: str = "PL-000"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message, code=code or self.error_code)


class PortfolioSessionNotFoundError(PortfolioLifecycleError):
    """Raised when a session_id lookup fails in the registry (PL-001)."""
    error_code = "PL-001"

    def __init__(self, session_id: str = "") -> None:
        detail = f" (session_id={session_id!r})" if session_id else ""
        super().__init__(
            f"Portfolio session not found{detail}",
            code=self.error_code,
        )
        self.session_id = session_id


class PortfolioInvalidTransitionError(PortfolioLifecycleError):
    """
    Raised when an attempted state transition is not permitted by the
    institutional state machine (PL-002).
    """
    error_code = "PL-002"

    def __init__(
        self,
        from_state: PortfolioState | str = "",
        to_state:   PortfolioState | str = "",
        session_id: str = "",
    ) -> None:
        from_v = from_state.value if isinstance(from_state, PortfolioState) else str(from_state)
        to_v   = to_state.value   if isinstance(to_state,   PortfolioState) else str(to_state)
        sid    = f", session_id={session_id!r}" if session_id else ""
        super().__init__(
            f"Invalid transition: {from_v!r} → {to_v!r}{sid}",
            code=self.error_code,
        )
        self.from_state = from_state
        self.to_state   = to_state
        self.session_id = session_id


class PortfolioSessionTerminatedError(PortfolioLifecycleError):
    """
    Raised when an operation is attempted on a session in a terminal
    (COMPLETED / FAILED / ARCHIVED) or immutable (ARCHIVED) state (PL-003).
    """
    error_code = "PL-003"

    def __init__(self, session_id: str = "", state: str = "") -> None:
        st = f" (state={state!r})" if state else ""
        super().__init__(
            f"Portfolio session has terminated{st}",
            code=self.error_code,
        )
        self.session_id = session_id


class PortfolioLifecycleNotRunningError(PortfolioLifecycleError):
    """
    Raised when an operation requires the lifecycle to be running
    but it is stopped (PL-004).
    """
    error_code = "PL-004"

    def __init__(self, message: str = "Portfolio lifecycle is not running") -> None:
        super().__init__(message, code=self.error_code)


class PortfolioCapacityExceededError(PortfolioLifecycleError):
    """
    Raised when the active-session limit has been reached (PL-005).
    """
    error_code = "PL-005"

    def __init__(self, limit: int = 0) -> None:
        msg = f"Active portfolio session capacity exceeded (limit={limit})"
        super().__init__(msg, code=self.error_code)
        self.limit = limit


class PortfolioValidationError(PortfolioLifecycleError):
    """
    Raised when lifecycle validation checks fail (PL-006).
    """
    error_code = "PL-006"

    def __init__(self, message: str, failed_checks: tuple = ()) -> None:
        super().__init__(message, code=self.error_code)
        self.failed_checks: tuple = tuple(failed_checks)


class PortfolioHistoryError(PortfolioLifecycleError):
    """
    Raised when the lifecycle history is inconsistent (PL-007).
    """
    error_code = "PL-007"


class PortfolioRegistryError(PortfolioLifecycleError):
    """
    Raised on registry-level errors (duplicate, capacity) (PL-008).
    """
    error_code = "PL-008"


class PortfolioConfigurationError(PortfolioLifecycleError):
    """
    Raised when the lifecycle subsystem is misconfigured (PL-009).
    """
    error_code = "PL-009"
