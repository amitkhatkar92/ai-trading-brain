"""
exceptions.py — iios.risk.engine
==================================
Exception hierarchy for the Institutional Risk Engine subsystem.

Error-code prefix: RE (Risk Engine).

C11 Risk Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

from iios.common.errors.exceptions import IIOSError


class RiskEngineError(IIOSError):
    """Base error for the Institutional Risk Engine subsystem (RE-000)."""
    error_code: str = "RE-000"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message, code=code or self.error_code)


class RiskEngineNotRunningError(RiskEngineError):
    """Raised when an operation is attempted before the engine is started (RE-001)."""
    error_code = "RE-001"

    def __init__(self) -> None:
        super().__init__(
            "Risk engine is not running — call start() first",
            code=self.error_code,
        )


class RiskSessionError(RiskEngineError):
    """Raised when a risk session operation fails (RE-002)."""
    error_code = "RE-002"

    def __init__(self, message: str = "", *, session_id: str = "") -> None:
        detail = f" (session_id={session_id!r})" if session_id else ""
        super().__init__(
            f"Risk session error{detail}: {message}",
            code=self.error_code,
        )
        self.session_id = session_id


class RiskPipelineError(RiskEngineError):
    """Raised when a risk pipeline operation fails (RE-003)."""
    error_code = "RE-003"

    def __init__(self, message: str = "", *, pipeline_id: str = "") -> None:
        detail = f" (pipeline_id={pipeline_id!r})" if pipeline_id else ""
        super().__init__(
            f"Risk pipeline error{detail}: {message}",
            code=self.error_code,
        )
        self.pipeline_id = pipeline_id


class RiskDispatchError(RiskEngineError):
    """Raised when dispatching a risk workflow fails (RE-004)."""
    error_code = "RE-004"

    def __init__(self, message: str = "", *, workflow_type: str = "") -> None:
        detail = f" (workflow={workflow_type!r})" if workflow_type else ""
        super().__init__(
            f"Risk dispatch error{detail}: {message}",
            code=self.error_code,
        )
        self.workflow_type = workflow_type


class RiskCollectionError(RiskEngineError):
    """Raised when collecting institutional inputs fails (RE-005)."""
    error_code = "RE-005"

    def __init__(self, message: str = "", *, missing_inputs: tuple = ()) -> None:
        super().__init__(
            f"Risk input collection error: {message}",
            code=self.error_code,
        )
        self.missing_inputs = missing_inputs


class RiskPublicationError(RiskEngineError):
    """Raised when publishing a risk snapshot fails (RE-006)."""
    error_code = "RE-006"

    def __init__(self, message: str = "", *, risk_id: str = "") -> None:
        detail = f" (risk_id={risk_id!r})" if risk_id else ""
        super().__init__(
            f"Risk publication error{detail}: {message}",
            code=self.error_code,
        )
        self.risk_id = risk_id


class RiskEngineValidationError(RiskEngineError):
    """Raised when risk engine validation checks fail (RE-007)."""
    error_code = "RE-007"

    def __init__(self, message: str = "", *, failed_checks: tuple = ()) -> None:
        super().__init__(
            f"Risk engine validation failed: {message}",
            code=self.error_code,
        )
        self.failed_checks = failed_checks


class RiskSchedulerError(RiskEngineError):
    """Raised when the risk scheduler encounters an error (RE-008)."""
    error_code = "RE-008"

    def __init__(self, message: str = "") -> None:
        super().__init__(
            f"Risk scheduler error: {message}",
            code=self.error_code,
        )


class RiskCapacityError(RiskEngineError):
    """Raised when an engine capacity limit is exceeded (RE-009)."""
    error_code = "RE-009"

    def __init__(self, limit: int = 0) -> None:
        super().__init__(
            f"Risk engine capacity exceeded (limit={limit})",
            code=self.error_code,
        )
        self.limit = limit
