"""
exceptions.py — iios.decision.lifecycle
=========================================
Exception hierarchy for the Institutional Decision Lifecycle subsystem.

Error-code prefix: DL (Decision Lifecycle).

C9 Decision Intelligence — Phase 1, Module 1
"""
from __future__ import annotations

from iios.common.errors.exceptions import IIOSError

from .constants import DecisionState


class DecisionLifecycleError(IIOSError):
    """
    Base error for the Institutional Decision Lifecycle subsystem.

    All decision lifecycle exceptions derive from this class so callers can
    catch the entire family with a single ``except DecisionLifecycleError``.
    """
    error_code: str = "DL-000"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message, code=code or self.error_code)


class DecisionSessionNotFoundError(DecisionLifecycleError):
    """
    Raised when a session_id lookup fails in the registry.
    """
    error_code = "DL-001"

    def __init__(self, session_id: str = "") -> None:
        detail = f" (session_id={session_id!r})" if session_id else ""
        super().__init__(
            f"Decision session not found{detail}",
            code=self.error_code,
        )


class DecisionInvalidTransitionError(DecisionLifecycleError):
    """
    Raised when an attempted state transition is not permitted by the
    institutional state machine.
    """
    error_code = "DL-002"

    def __init__(
        self,
        from_state: DecisionState | str = "",
        to_state:   DecisionState | str = "",
        session_id: str = "",
    ) -> None:
        from_v = from_state.value if isinstance(from_state, DecisionState) else str(from_state)
        to_v   = to_state.value   if isinstance(to_state,   DecisionState) else str(to_state)
        sid    = f", session_id={session_id!r}" if session_id else ""
        super().__init__(
            f"Invalid decision state transition: {from_v!r} → {to_v!r}{sid}",
            code=self.error_code,
        )
        self.from_state = from_state
        self.to_state   = to_state


class DecisionLifecycleNotRunningError(DecisionLifecycleError):
    """
    Raised when an operation is attempted on
    :class:`~iios.decision.lifecycle.DecisionLifecycle` while it is not
    in a running state.
    """
    error_code = "DL-003"

    def __init__(self, operation: str = "") -> None:
        detail = f" (operation: {operation})" if operation else ""
        super().__init__(
            f"Decision lifecycle is not running{detail}",
            code=self.error_code,
        )


class DecisionSessionAlreadyExistsError(DecisionLifecycleError):
    """
    Raised when :meth:`DecisionLifecycle.create` is called with a
    ``session_id`` that is already registered and still active.
    """
    error_code = "DL-004"

    def __init__(self, session_id: str = "") -> None:
        detail = f" (session_id={session_id!r})" if session_id else ""
        super().__init__(
            f"Decision session already exists{detail}",
            code=self.error_code,
        )


class DecisionValidationError(DecisionLifecycleError):
    """
    Raised when one or more decision lifecycle validation checks fail.
    ``failed_checks`` is a tuple of :class:`DecisionValidationCode` string
    values identifying which checks did not pass.
    """
    error_code = "DL-005"

    def __init__(
        self,
        failed_checks: tuple[str, ...] = (),
        detail: str = "",
    ) -> None:
        checks_str = ", ".join(failed_checks) if failed_checks else "unknown"
        msg = f"Decision lifecycle validation failed — checks: {checks_str}"
        if detail:
            msg = f"{msg} — {detail}"
        super().__init__(msg, code=self.error_code)
        self.failed_checks: tuple[str, ...] = failed_checks


class DecisionSessionTerminatedError(DecisionLifecycleError):
    """
    Raised when an operation is attempted on a session that has already
    reached a terminal state (COMPLETED, FAILED, or ARCHIVED).
    """
    error_code = "DL-006"

    def __init__(self, session_id: str = "", state: DecisionState | str | None = None) -> None:
        state_str = (
            state.value if isinstance(state, DecisionState)
            else str(state) if state else "terminal"
        )
        sid = f" (session_id={session_id!r})" if session_id else ""
        super().__init__(
            f"Decision session is in terminal state {state_str!r}{sid}",
            code=self.error_code,
        )
