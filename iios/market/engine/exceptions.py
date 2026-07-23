"""
exceptions.py — iios.market.engine
=====================================
Exception hierarchy for the Institutional Market Engine subsystem.

Error-code prefix: ME (Market Engine).

C12 Market Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

from iios.common.errors.exceptions import IIOSError


class MarketEngineError(IIOSError):
    """Base error for the Institutional Market Engine subsystem (ME-000)."""
    error_code: str = "ME-000"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message, code=code or self.error_code)


class MarketEngineNotRunningError(MarketEngineError):
    """Raised when an operation is attempted before the engine is started (ME-001)."""
    error_code = "ME-001"

    def __init__(self) -> None:
        super().__init__(
            "Market engine is not running — call start() first",
            code=self.error_code,
        )


class MarketSessionError(MarketEngineError):
    """Raised when a market session operation fails (ME-002)."""
    error_code = "ME-002"

    def __init__(self, message: str = "", *, session_id: str = "") -> None:
        detail = f" (session_id={session_id!r})" if session_id else ""
        super().__init__(
            f"Market session error{detail}: {message}",
            code=self.error_code,
        )
        self.session_id = session_id


class MarketPipelineError(MarketEngineError):
    """Raised when a market pipeline operation fails (ME-003)."""
    error_code = "ME-003"

    def __init__(self, message: str = "", *, pipeline_id: str = "") -> None:
        detail = f" (pipeline_id={pipeline_id!r})" if pipeline_id else ""
        super().__init__(
            f"Market pipeline error{detail}: {message}",
            code=self.error_code,
        )
        self.pipeline_id = pipeline_id


class MarketDispatchError(MarketEngineError):
    """Raised when dispatching a market workflow fails (ME-004)."""
    error_code = "ME-004"

    def __init__(self, message: str = "", *, workflow_type: str = "") -> None:
        detail = f" (workflow={workflow_type!r})" if workflow_type else ""
        super().__init__(
            f"Market dispatch error{detail}: {message}",
            code=self.error_code,
        )
        self.workflow_type = workflow_type


class MarketCollectionError(MarketEngineError):
    """Raised when collecting institutional market inputs fails (ME-005)."""
    error_code = "ME-005"

    def __init__(self, message: str = "", *, missing_inputs: tuple = ()) -> None:
        super().__init__(
            f"Market input collection error: {message}",
            code=self.error_code,
        )
        self.missing_inputs = missing_inputs


class MarketPublicationError(MarketEngineError):
    """Raised when publishing a market snapshot fails (ME-006)."""
    error_code = "ME-006"

    def __init__(self, message: str = "", *, market_analysis_id: str = "") -> None:
        detail = f" (market_analysis_id={market_analysis_id!r})" if market_analysis_id else ""
        super().__init__(
            f"Market publication error{detail}: {message}",
            code=self.error_code,
        )
        self.market_analysis_id = market_analysis_id


class MarketEngineValidationError(MarketEngineError):
    """Raised when market engine validation checks fail (ME-007)."""
    error_code = "ME-007"

    def __init__(self, message: str = "", *, failed_checks: tuple = ()) -> None:
        super().__init__(
            f"Market engine validation failed: {message}",
            code=self.error_code,
        )
        self.failed_checks = failed_checks


class MarketSchedulerError(MarketEngineError):
    """Raised when the market scheduler encounters an error (ME-008)."""
    error_code = "ME-008"

    def __init__(self, message: str = "") -> None:
        super().__init__(
            f"Market scheduler error: {message}",
            code=self.error_code,
        )


class MarketEngineCapacityError(MarketEngineError):
    """Raised when an engine capacity limit is exceeded (ME-009)."""
    error_code = "ME-009"

    def __init__(self, limit: int = 0) -> None:
        super().__init__(
            f"Market engine capacity exceeded (limit={limit})",
            code=self.error_code,
        )
        self.limit = limit
