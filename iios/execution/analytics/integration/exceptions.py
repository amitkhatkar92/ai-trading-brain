"""
exceptions.py — iios.execution.analytics.integration
=====================================================
Exception hierarchy for the Execution Analytics Integration subsystem.

Error-code prefix: EAI (Execution Analytics Integration).
"""
from __future__ import annotations

from iios.common.errors.exceptions import IIOSError


class IntegrationError(IIOSError):
    """
    Base error for the Execution Analytics Integration subsystem.

    All integration exceptions derive from this class so callers can catch
    the entire family with a single ``except IntegrationError``.
    """
    error_code: str = "EAI-000"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message, code=code or self.error_code)


class IntegrationNotRunningError(IntegrationError):
    """
    Raised when an operation is attempted on the integration subsystem
    while it is not in a running state.
    """
    error_code = "EAI-001"

    def __init__(self, operation: str = "") -> None:
        detail = f" (operation: {operation})" if operation else ""
        super().__init__(
            f"Integration subsystem is not running{detail}",
            code=self.error_code,
        )


class IntegrationNotReadyError(IntegrationError):
    """
    Raised when the integration subsystem has been started but has not
    finished initializing all components and is not yet ready to accept
    analytics requests.
    """
    error_code = "EAI-002"

    def __init__(self, detail: str = "") -> None:
        msg = "Integration subsystem is not ready"
        if detail:
            msg = f"{msg}: {detail}"
        super().__init__(msg, code=self.error_code)


class IntegrationRequestError(IntegrationError):
    """
    Raised when an analytics integration request is malformed, missing
    required fields, or violates business rules.
    """
    error_code = "EAI-003"

    def __init__(self, request_id: str = "", detail: str = "") -> None:
        parts = ["Integration request is invalid"]
        if request_id:
            parts.append(f"request_id={request_id!r}")
        if detail:
            parts.append(detail)
        super().__init__(" — ".join(parts), code=self.error_code)


class IntegrationValidationError(IntegrationError):
    """
    Raised when one or more of the seven integration validation checks fail.
    ``failed_checks`` is a tuple of ``IntegrationValidationCode`` string values
    that identifies which checks did not pass.
    """
    error_code = "EAI-004"

    def __init__(
        self,
        failed_checks: tuple[str, ...] = (),
        detail: str = "",
    ) -> None:
        checks_str = ", ".join(failed_checks) if failed_checks else "unknown"
        msg = f"Integration validation failed — checks: {checks_str}"
        if detail:
            msg = f"{msg} — {detail}"
        super().__init__(msg, code=self.error_code)
        self.failed_checks: tuple[str, ...] = failed_checks


class IntegrationComponentError(IntegrationError):
    """
    Raised when a managed analytics component (M1-M5) fails to start,
    stop, or respond within its expected contract.
    """
    error_code = "EAI-005"

    def __init__(self, component: str = "", detail: str = "") -> None:
        parts = ["Integration component error"]
        if component:
            parts.append(f"component={component!r}")
        if detail:
            parts.append(detail)
        super().__init__(" — ".join(parts), code=self.error_code)


class IntegrationTimeoutError(IntegrationError):
    """
    Raised when an analytics operation exceeds its configured time budget.
    """
    error_code = "EAI-006"

    def __init__(self, operation: str = "", timeout_s: float | None = None) -> None:
        detail = f" (operation: {operation})" if operation else ""
        limit  = f", limit={timeout_s:.1f}s" if timeout_s is not None else ""
        super().__init__(
            f"Integration operation timed out{detail}{limit}",
            code=self.error_code,
        )


class IntegrationAlreadyRunningError(IntegrationError):
    """Raised when ``start()`` is called on an already-running integration."""
    error_code = "EAI-007"

    def __init__(self) -> None:
        super().__init__(
            "Integration subsystem is already running",
            code=self.error_code,
        )
