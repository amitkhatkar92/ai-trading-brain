"""iios/investment/portfolio/portfolio_exceptions.py
Exception hierarchy for the Portfolio & Risk Intelligence Engine.
All codes carry the PR- prefix.
"""
from __future__ import annotations


class PortfolioIntelligenceError(Exception):
    """Root exception — PR-000."""

    code = "PR-000"

    def __init__(
        self,
        message: str = "Portfolio intelligence error",
        code: str | None = None,
    ) -> None:
        self.code = code or self.__class__.code
        super().__init__(f"[{self.code}] {message}")


# ── Portfolio (PR-010) ────────────────────────────────────────────────────────

class PortfolioError(PortfolioIntelligenceError):
    code = "PR-010"


class PortfolioNotFoundError(PortfolioError):
    code = "PR-011"

    def __init__(self, message: str = "", *, portfolio_id: str = "") -> None:
        self.portfolio_id = portfolio_id
        super().__init__(message or f"Portfolio not found: {portfolio_id!r}")


class PortfolioAlreadyExistsError(PortfolioError):
    code = "PR-012"

    def __init__(self, message: str = "", *, portfolio_id: str = "") -> None:
        self.portfolio_id = portfolio_id
        super().__init__(message or f"Portfolio already exists: {portfolio_id!r}")


class PortfolioInvalidError(PortfolioError):
    code = "PR-013"

    def __init__(self, message: str = "", detail: str = "") -> None:
        super().__init__(message or f"Invalid portfolio: {detail}")


# ── Position (PR-020) ─────────────────────────────────────────────────────────

class PositionError(PortfolioIntelligenceError):
    code = "PR-020"


class PositionNotFoundError(PositionError):
    code = "PR-021"

    def __init__(self, message: str = "", *, position_id: str = "") -> None:
        self.position_id = position_id
        super().__init__(message or f"Position not found: {position_id!r}")


class PositionAlreadyExistsError(PositionError):
    code = "PR-022"

    def __init__(self, message: str = "", *, position_id: str = "") -> None:
        self.position_id = position_id
        super().__init__(message or f"Position already exists: {position_id!r}")


class PositionInvalidError(PositionError):
    code = "PR-023"

    def __init__(self, message: str = "", detail: str = "") -> None:
        super().__init__(message or f"Invalid position: {detail}")


# ── Risk (PR-030) ─────────────────────────────────────────────────────────────

class RiskError(PortfolioIntelligenceError):
    code = "PR-030"


class RiskLimitExceededError(RiskError):
    code = "PR-031"

    def __init__(self, message: str = "", *, limit_name: str = "", value: float = 0.0) -> None:
        self.limit_name = limit_name
        self.value = value
        super().__init__(message or f"Risk limit exceeded: {limit_name}={value:.4f}")


class RiskAnalysisFailedError(RiskError):
    code = "PR-032"

    def __init__(self, message: str = "", reason: str = "") -> None:
        super().__init__(message or f"Risk analysis failed: {reason}")


# ── Exposure (PR-040) ─────────────────────────────────────────────────────────

class ExposureError(PortfolioIntelligenceError):
    code = "PR-040"


class ExposureLimitExceededError(ExposureError):
    code = "PR-041"

    def __init__(self, message: str = "", *, limit_name: str = "", value: float = 0.0) -> None:
        self.limit_name = limit_name
        self.value = value
        super().__init__(message or f"Exposure limit exceeded: {limit_name}={value:.4f}")


class ExposureDataMissingError(ExposureError):
    code = "PR-042"

    def __init__(self, message: str = "", field: str = "") -> None:
        super().__init__(message or f"Exposure data missing: {field!r}")


# ── Allocation (PR-050) ───────────────────────────────────────────────────────

class AllocationError(PortfolioIntelligenceError):
    code = "PR-050"


class AllocationLimitExceededError(AllocationError):
    code = "PR-051"

    def __init__(self, message: str = "", *, limit_name: str = "", value: float = 0.0) -> None:
        self.limit_name = limit_name
        self.value = value
        super().__init__(message or f"Allocation limit exceeded: {limit_name}={value:.4f}")


class AllocationInvalidError(AllocationError):
    code = "PR-052"

    def __init__(self, message: str = "", detail: str = "") -> None:
        super().__init__(message or f"Invalid allocation: {detail}")


# ── Drawdown (PR-060) ─────────────────────────────────────────────────────────

class DrawdownError(PortfolioIntelligenceError):
    code = "PR-060"


class DrawdownLimitExceededError(DrawdownError):
    code = "PR-061"

    def __init__(self, message: str = "", *, current_pct: float = 0.0, limit_pct: float = 0.0) -> None:
        self.current_pct = current_pct
        self.limit_pct   = limit_pct
        super().__init__(
            message or f"Drawdown limit exceeded: {current_pct:.2%} > {limit_pct:.2%}"
        )


# ── Engine lifecycle (PR-070) ─────────────────────────────────────────────────

class PortfolioEngineError(PortfolioIntelligenceError):
    code = "PR-070"


class PortfolioEngineNotInitializedError(PortfolioEngineError):
    code = "PR-071"

    def __init__(self, message: str = "") -> None:
        super().__init__(message or "Portfolio Intelligence Engine is not initialized")


class PortfolioEngineAlreadyRunningError(PortfolioEngineError):
    code = "PR-072"

    def __init__(self, message: str = "") -> None:
        super().__init__(message or "Portfolio Intelligence Engine is already running")


# ── Registry (PR-080) ─────────────────────────────────────────────────────────

class PortfolioRegistryError(PortfolioIntelligenceError):
    code = "PR-080"


class PortfolioRegistryItemNotFoundError(PortfolioRegistryError):
    code = "PR-081"

    def __init__(self, message: str = "", *, item_id: str = "") -> None:
        self.item_id = item_id
        super().__init__(message or f"Registry item not found: {item_id!r}")


class PortfolioRegistryItemAlreadyExistsError(PortfolioRegistryError):
    code = "PR-082"

    def __init__(self, message: str = "", *, item_id: str = "") -> None:
        self.item_id = item_id
        super().__init__(message or f"Registry item already exists: {item_id!r}")


class PortfolioRegistryOverflowError(PortfolioRegistryError):
    code = "PR-083"

    def __init__(self, message: str = "", *, capacity: int = 0, current: int = 0) -> None:
        self.capacity = capacity
        self.current  = current
        super().__init__(message or f"Registry capacity exceeded (max={capacity})")
