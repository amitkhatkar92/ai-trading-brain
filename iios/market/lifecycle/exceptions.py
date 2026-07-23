"""
exceptions.py — iios.market.lifecycle
=======================================
Exception hierarchy for the Institutional Market Lifecycle subsystem.

Error-code prefix: ML (Market Lifecycle).

C12 Market Intelligence — Phase 1, Module 1
"""
from __future__ import annotations

from iios.common.errors.exceptions import IIOSError

from .constants import MarketState


class MarketLifecycleError(IIOSError):
    """
    Base error for the Institutional Market Lifecycle subsystem (ML-000).

    All market lifecycle exceptions derive from this class.
    """
    error_code: str = "ML-000"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message, code=code or self.error_code)


class MarketSessionNotFoundError(MarketLifecycleError):
    """Raised when a session_id lookup fails in the registry (ML-001)."""
    error_code = "ML-001"

    def __init__(self, session_id: str = "") -> None:
        detail = f" (session_id={session_id!r})" if session_id else ""
        super().__init__(
            f"Market session not found{detail}",
            code=self.error_code,
        )
        self.session_id = session_id


class MarketInvalidTransitionError(MarketLifecycleError):
    """
    Raised when an attempted state transition is not permitted by the
    institutional market state machine (ML-002).
    """
    error_code = "ML-002"

    def __init__(
        self,
        from_state: MarketState | str = "",
        to_state:   MarketState | str = "",
        session_id: str = "",
    ) -> None:
        from_v = from_state.value if isinstance(from_state, MarketState) else str(from_state)
        to_v   = to_state.value   if isinstance(to_state,   MarketState) else str(to_state)
        sid    = f", session_id={session_id!r}" if session_id else ""
        super().__init__(
            f"Invalid transition: {from_v!r} → {to_v!r}{sid}",
            code=self.error_code,
        )
        self.from_state = from_state
        self.to_state   = to_state
        self.session_id = session_id


class MarketSessionTerminatedError(MarketLifecycleError):
    """
    Raised when an operation is attempted on a session in a terminal
    (COMPLETED / FAILED / ARCHIVED) or immutable (ARCHIVED) state (ML-003).
    """
    error_code = "ML-003"

    def __init__(self, session_id: str = "", state: str = "") -> None:
        st = f" (state={state!r})" if state else ""
        super().__init__(
            f"Market session has terminated{st}",
            code=self.error_code,
        )
        self.session_id = session_id


class MarketLifecycleNotRunningError(MarketLifecycleError):
    """
    Raised when a lifecycle operation is attempted while the engine is
    not in RUNNING state (ML-004).
    """
    error_code = "ML-004"

    def __init__(self, message: str = "MarketLifecycle is not running") -> None:
        super().__init__(message, code=self.error_code)


class MarketCapacityExceededError(MarketLifecycleError):
    """
    Raised when the active-session limit or archive limit is breached (ML-005).
    """
    error_code = "ML-005"

    def __init__(self, limit: int = 0) -> None:
        detail = f" (limit={limit})" if limit else ""
        super().__init__(
            f"Market session capacity exceeded{detail}",
            code=self.error_code,
        )
        self.limit = limit


class MarketValidationError(MarketLifecycleError):
    """
    Raised when structural validation of a market session fails (ML-006).
    """
    error_code = "ML-006"

    def __init__(self, message: str, session_id: str = "") -> None:
        super().__init__(message, code=self.error_code)
        self.session_id = session_id


class MarketHistoryError(MarketLifecycleError):
    """Raised on history integrity failures (ML-007)."""
    error_code = "ML-007"


class MarketRegistryError(MarketLifecycleError):
    """Raised on registry integrity failures (ML-008)."""
    error_code = "ML-008"


class MarketConfigurationError(MarketLifecycleError):
    """Raised when the lifecycle is misconfigured (ML-009)."""
    error_code = "ML-009"
