"""
exceptions.py — iios.portfolio.engine
=======================================
Exception hierarchy for the Institutional Portfolio Engine subsystem.

Error-code prefix: PE (Portfolio Engine).

C10 Portfolio Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

from iios.common.errors.exceptions import IIOSError


class PortfolioEngineError(IIOSError):
    """
    Base error for the Institutional Portfolio Engine subsystem (PE-000).

    All portfolio engine exceptions derive from this class.
    """
    error_code: str = "PE-000"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message, code=code or self.error_code)


class PortfolioEngineNotRunningError(PortfolioEngineError):
    """Raised when an operation is attempted before the engine is started (PE-001)."""
    error_code = "PE-001"

    def __init__(self) -> None:
        super().__init__(
            "Portfolio engine is not running — call start() first",
            code=self.error_code,
        )


class PortfolioSessionError(PortfolioEngineError):
    """Raised when a portfolio session operation fails (PE-002)."""
    error_code = "PE-002"

    def __init__(self, message: str = "", *, session_id: str = "") -> None:
        detail = f" (session_id={session_id!r})" if session_id else ""
        super().__init__(
            f"Portfolio session error{detail}: {message}",
            code=self.error_code,
        )
        self.session_id = session_id


class PortfolioPipelineError(PortfolioEngineError):
    """Raised when a portfolio pipeline operation fails (PE-003)."""
    error_code = "PE-003"

    def __init__(self, message: str = "", *, pipeline_id: str = "") -> None:
        detail = f" (pipeline_id={pipeline_id!r})" if pipeline_id else ""
        super().__init__(
            f"Portfolio pipeline error{detail}: {message}",
            code=self.error_code,
        )
        self.pipeline_id = pipeline_id


class PortfolioDispatchError(PortfolioEngineError):
    """Raised when dispatching a portfolio workflow fails (PE-004)."""
    error_code = "PE-004"

    def __init__(self, message: str = "", *, workflow_type: str = "") -> None:
        detail = f" (workflow={workflow_type!r})" if workflow_type else ""
        super().__init__(
            f"Portfolio dispatch error{detail}: {message}",
            code=self.error_code,
        )
        self.workflow_type = workflow_type


class PortfolioCollectionError(PortfolioEngineError):
    """Raised when collecting institutional inputs fails (PE-005)."""
    error_code = "PE-005"

    def __init__(self, message: str = "", *, missing_inputs: tuple = ()) -> None:
        super().__init__(
            f"Portfolio input collection error: {message}",
            code=self.error_code,
        )
        self.missing_inputs = missing_inputs


class PortfolioPublicationError(PortfolioEngineError):
    """Raised when publishing a portfolio snapshot fails (PE-006)."""
    error_code = "PE-006"

    def __init__(self, message: str = "", *, portfolio_id: str = "") -> None:
        detail = f" (portfolio_id={portfolio_id!r})" if portfolio_id else ""
        super().__init__(
            f"Portfolio publication error{detail}: {message}",
            code=self.error_code,
        )
        self.portfolio_id = portfolio_id


class PortfolioEngineValidationError(PortfolioEngineError):
    """Raised when portfolio engine validation checks fail (PE-007)."""
    error_code = "PE-007"

    def __init__(self, message: str = "", *, failed_checks: tuple = ()) -> None:
        super().__init__(
            f"Portfolio engine validation failed: {message}",
            code=self.error_code,
        )
        self.failed_checks = failed_checks


class PortfolioSchedulerError(PortfolioEngineError):
    """Raised when the portfolio scheduler encounters an error (PE-008)."""
    error_code = "PE-008"

    def __init__(self, message: str = "") -> None:
        super().__init__(
            f"Portfolio scheduler error: {message}",
            code=self.error_code,
        )


class PortfolioCapacityError(PortfolioEngineError):
    """Raised when engine capacity limits are exceeded (PE-009)."""
    error_code = "PE-009"

    def __init__(self, limit: int = 0) -> None:
        super().__init__(
            f"Portfolio engine capacity exceeded (limit={limit})",
            code=self.error_code,
        )
        self.limit = limit
