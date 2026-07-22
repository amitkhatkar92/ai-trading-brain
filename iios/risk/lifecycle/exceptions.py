"""
exceptions.py — iios.risk.lifecycle
======================================
Exception hierarchy for the Institutional Risk Lifecycle subsystem.

Error-code prefix: RL (Risk Lifecycle).

C11 Risk Intelligence — Phase 1, Module 1
"""
from __future__ import annotations

from iios.common.errors.exceptions import IIOSError

from .constants import RiskState


class RiskLifecycleError(IIOSError):
    """
    Base error for the Institutional Risk Lifecycle subsystem (RL-000).

    All risk lifecycle exceptions derive from this class.
    """
    error_code: str = "RL-000"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message, code=code or self.error_code)


class RiskSessionNotFoundError(RiskLifecycleError):
    """Raised when a session_id lookup fails in the registry (RL-001)."""
    error_code = "RL-001"

    def __init__(self, session_id: str = "") -> None:
        detail = f" (session_id={session_id!r})" if session_id else ""
        super().__init__(
            f"Risk session not found{detail}",
            code=self.error_code,
        )
        self.session_id = session_id


class RiskInvalidTransitionError(RiskLifecycleError):
    """
    Raised when an attempted state transition is not permitted by the
    institutional risk state machine (RL-002).
    """
    error_code = "RL-002"

    def __init__(
        self,
        from_state: RiskState | str = "",
        to_state:   RiskState | str = "",
        session_id: str = "",
    ) -> None:
        from_v = from_state.value if isinstance(from_state, RiskState) else str(from_state)
        to_v   = to_state.value   if isinstance(to_state,   RiskState) else str(to_state)
        sid    = f", session_id={session_id!r}" if session_id else ""
        super().__init__(
            f"Invalid transition: {from_v!r} → {to_v!r}{sid}",
            code=self.error_code,
        )
        self.from_state = from_state
        self.to_state   = to_state
        self.session_id = session_id


class RiskSessionTerminatedError(RiskLifecycleError):
    """
    Raised when an operation is attempted on a session in a terminal
    (COMPLETED / FAILED / ARCHIVED) or immutable (ARCHIVED) state (RL-003).
    """
    error_code = "RL-003"

    def __init__(self, session_id: str = "", state: str = "") -> None:
        st = f" (state={state!r})" if state else ""
        super().__init__(
            f"Risk session has terminated{st}",
            code=self.error_code,
        )
        self.session_id = session_id


class RiskLifecycleNotRunningError(RiskLifecycleError):
    """
    Raised when an operation requires the lifecycle to be running
    but it is stopped (RL-004).
    """
    error_code = "RL-004"

    def __init__(self, message: str = "Risk lifecycle is not running") -> None:
        super().__init__(message, code=self.error_code)


class RiskCapacityExceededError(RiskLifecycleError):
    """
    Raised when the active-session limit has been reached (RL-005).
    """
    error_code = "RL-005"

    def __init__(self, limit: int = 0) -> None:
        msg = f"Active risk session capacity exceeded (limit={limit})"
        super().__init__(msg, code=self.error_code)
        self.limit = limit


class RiskValidationError(RiskLifecycleError):
    """
    Raised when lifecycle validation checks fail (RL-006).
    """
    error_code = "RL-006"

    def __init__(self, message: str, failed_checks: tuple = ()) -> None:
        super().__init__(message, code=self.error_code)
        self.failed_checks: tuple = tuple(failed_checks)


class RiskHistoryError(RiskLifecycleError):
    """
    Raised when the lifecycle history is inconsistent (RL-007).
    """
    error_code = "RL-007"

    def __init__(self, message: str = "Risk lifecycle history is inconsistent") -> None:
        super().__init__(message, code=self.error_code)


class RiskRegistryError(RiskLifecycleError):
    """
    Raised for duplicate or invalid registry operations (RL-008).
    """
    error_code = "RL-008"

    def __init__(self, message: str = "Risk registry error") -> None:
        super().__init__(message, code=self.error_code)


class RiskConfigurationError(RiskLifecycleError):
    """
    Raised when the lifecycle receives an invalid configuration (RL-009).
    """
    error_code = "RL-009"

    def __init__(self, message: str = "Risk lifecycle configuration error") -> None:
        super().__init__(message, code=self.error_code)
