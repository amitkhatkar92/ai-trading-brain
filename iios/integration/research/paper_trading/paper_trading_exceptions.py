"""paper_trading_exceptions.py — Exception hierarchy for the Paper Trading & Market Simulation Framework."""
from __future__ import annotations


class PaperTradingError(Exception):
    """Root exception for the Paper Trading Framework. Code PT-000."""
    code = "PT-000"

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.code}: {self})"


# ── Engine lifecycle ──────────────────────────────────────────────────────────

class EngineNotRunningError(PaperTradingError):
    """Engine must be started before use. Code PT-001."""
    code = "PT-001"


class EngineAlreadyRunningError(PaperTradingError):
    """Engine is already running. Code PT-002."""
    code = "PT-002"


class EngineInitializationError(PaperTradingError):
    """Engine failed to initialize. Code PT-003."""
    code = "PT-003"


# ── Session ───────────────────────────────────────────────────────────────────

class SessionNotFoundError(PaperTradingError):
    """Session not found in registry. Code PT-010."""
    code = "PT-010"


class SessionAlreadyExistsError(PaperTradingError):
    """A session with this ID already exists. Code PT-011."""
    code = "PT-011"


class SessionStateError(PaperTradingError):
    """Invalid session state transition requested. Code PT-012."""
    code = "PT-012"


class SessionCapacityError(PaperTradingError):
    """Maximum session registry capacity reached. Code PT-013."""
    code = "PT-013"


# ── Account ───────────────────────────────────────────────────────────────────

class AccountNotFoundError(PaperTradingError):
    """Account not found. Code PT-020."""
    code = "PT-020"


class AccountError(PaperTradingError):
    """Generic account error. Code PT-021."""
    code = "PT-021"


class InsufficientCapitalError(PaperTradingError):
    """Insufficient capital to execute the operation. Code PT-022."""
    code = "PT-022"


class AccountSuspendedError(PaperTradingError):
    """Account is suspended and cannot accept new orders. Code PT-023."""
    code = "PT-023"


# ── Orders ────────────────────────────────────────────────────────────────────

class OrderNotFoundError(PaperTradingError):
    """Order not found. Code PT-030."""
    code = "PT-030"


class OrderRejectedError(PaperTradingError):
    """Order was rejected by the exchange simulator. Code PT-031."""
    code = "PT-031"


class OrderStateError(PaperTradingError):
    """Invalid order state transition requested. Code PT-032."""
    code = "PT-032"


class InvalidOrderError(PaperTradingError):
    """Order parameters are invalid. Code PT-033."""
    code = "PT-033"


# ── Positions ─────────────────────────────────────────────────────────────────

class PositionNotFoundError(PaperTradingError):
    """Position not found. Code PT-040."""
    code = "PT-040"


class PositionError(PaperTradingError):
    """Generic position error. Code PT-041."""
    code = "PT-041"


# ── Execution ─────────────────────────────────────────────────────────────────

class ExecutionError(PaperTradingError):
    """Execution simulation error. Code PT-050."""
    code = "PT-050"


class FillError(PaperTradingError):
    """Fill simulation error. Code PT-051."""
    code = "PT-051"


# ── Market ────────────────────────────────────────────────────────────────────

class MarketSimulatorError(PaperTradingError):
    """Market simulator error. Code PT-060."""
    code = "PT-060"


class MarketClockError(PaperTradingError):
    """Market clock error. Code PT-061."""
    code = "PT-061"


class ExchangeError(PaperTradingError):
    """Exchange simulator error. Code PT-062."""
    code = "PT-062"


# ── Reporting & analytics ─────────────────────────────────────────────────────

class ReportError(PaperTradingError):
    """Report generation error. Code PT-070."""
    code = "PT-070"


class AnalyticsError(PaperTradingError):
    """Analytics computation error. Code PT-071."""
    code = "PT-071"
