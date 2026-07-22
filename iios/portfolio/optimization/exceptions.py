"""
exceptions.py — iios.portfolio.optimization
=============================================
Exception hierarchy for the Portfolio Optimization Framework.

Error-code prefix: PO (Portfolio Optimization)

C10 Portfolio Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

from iios.common.errors.exceptions import IIOSError


class PortfolioOptimizationError(IIOSError):
    """Base error for the Portfolio Optimization Framework."""
    error_code: str = "PO-000"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message, code=code or self.error_code)


class PortfolioOptimizationNotRunningError(PortfolioOptimizationError):
    """Raised when the engine is called before it has been started."""
    error_code = "PO-001"

    def __init__(self) -> None:
        super().__init__(
            "Portfolio optimization engine is not running", code=self.error_code
        )


class PortfolioOptimizationNotFoundError(PortfolioOptimizationError):
    """Raised when an optimization run or strategy lookup fails."""
    error_code = "PO-002"

    def __init__(self, item_id: str = "", item_type: str = "optimization") -> None:
        self.item_id   = item_id
        self.item_type = item_type
        detail = f" ({item_type}_id={item_id!r})" if item_id else ""
        super().__init__(f"{item_type.title()} not found{detail}", code=self.error_code)


class PortfolioOptimizationConfigurationError(PortfolioOptimizationError):
    """Raised when an optimization strategy or engine is misconfigured."""
    error_code = "PO-003"

    def __init__(self, message: str, *, field: str = "") -> None:
        self.field = field
        super().__init__(message, code=self.error_code)


class PortfolioOptimizationValidationError(PortfolioOptimizationError):
    """Raised when a request or solution fails validation."""
    error_code = "PO-004"

    def __init__(self, message: str, *, failed_checks: tuple = ()) -> None:
        self.failed_checks = failed_checks
        super().__init__(message, code=self.error_code)


class PortfolioOptimizationSolutionError(PortfolioOptimizationError):
    """Raised when no feasible solution can be selected."""
    error_code = "PO-005"

    def __init__(self, message: str, *, optimization_id: str = "") -> None:
        self.optimization_id = optimization_id
        super().__init__(message, code=self.error_code)


class PortfolioOptimizationConstraintError(PortfolioOptimizationError):
    """Raised when constraint evaluation fails unrecoverably."""
    error_code = "PO-006"

    def __init__(self, message: str, *, constraint_name: str = "") -> None:
        self.constraint_name = constraint_name
        super().__init__(message, code=self.error_code)


class PortfolioOptimizationStrategyError(PortfolioOptimizationError):
    """Raised when a strategy cannot be loaded or applied."""
    error_code = "PO-007"

    def __init__(self, message: str, *, strategy_id: str = "") -> None:
        self.strategy_id = strategy_id
        super().__init__(message, code=self.error_code)


class PortfolioOptimizationCapacityError(PortfolioOptimizationError):
    """Raised when a registry is at capacity."""
    error_code = "PO-008"

    def __init__(self, limit: int, *, resource: str = "registry") -> None:
        self.limit    = limit
        self.resource = resource
        super().__init__(
            f"{resource} capacity exceeded (limit={limit})", code=self.error_code
        )


class PortfolioOptimizationCandidateError(PortfolioOptimizationError):
    """Raised when a portfolio candidate is invalid or cannot be evaluated."""
    error_code = "PO-009"

    def __init__(self, message: str, *, candidate_id: str = "") -> None:
        self.candidate_id = candidate_id
        super().__init__(message, code=self.error_code)
