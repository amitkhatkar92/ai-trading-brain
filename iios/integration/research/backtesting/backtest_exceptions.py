"""backtest_exceptions.py — Exception hierarchy for the Strategy Backtesting Framework."""
from __future__ import annotations


class BacktestError(Exception):
    """Root exception for the Backtesting Framework. Code BT-000."""
    code = "BT-000"

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.code}: {self})"


# ── Engine ────────────────────────────────────────────────────────────────────

class BacktestEngineNotRunningError(BacktestError):
    """Engine must be started before use. Code BT-001."""
    code = "BT-001"


class BacktestEngineAlreadyRunningError(BacktestError):
    """Engine is already running. Code BT-002."""
    code = "BT-002"


class BacktestEngineInitializationError(BacktestError):
    """Engine failed to initialize. Code BT-003."""
    code = "BT-003"


# ── Backtest lifecycle ────────────────────────────────────────────────────────

class BacktestNotFoundError(BacktestError):
    """Backtest not found in registry. Code BT-010."""
    code = "BT-010"


class BacktestAlreadyExistsError(BacktestError):
    """A backtest with this ID already exists. Code BT-011."""
    code = "BT-011"


class BacktestValidationError(BacktestError):
    """Backtest configuration failed validation. Code BT-012."""
    code = "BT-012"


class BacktestStateError(BacktestError):
    """Invalid state transition requested. Code BT-013."""
    code = "BT-013"


class BacktestCapacityError(BacktestError):
    """Maximum backtest registry capacity reached. Code BT-014."""
    code = "BT-014"


# ── Simulation ────────────────────────────────────────────────────────────────

class SimulationError(BacktestError):
    """General simulation error. Code BT-020."""
    code = "BT-020"


class SimulationDataError(BacktestError):
    """Data error during simulation. Code BT-021."""
    code = "BT-021"


class SimulationStateError(BacktestError):
    """Simulation is in an invalid state. Code BT-022."""
    code = "BT-022"


class SimulationClockError(BacktestError):
    """Simulation clock error. Code BT-023."""
    code = "BT-023"


# ── Data ──────────────────────────────────────────────────────────────────────

class BacktestDatasetError(BacktestError):
    """Dataset error during backtesting. Code BT-030."""
    code = "BT-030"


class BacktestDataNotFoundError(BacktestError):
    """Required market data not found. Code BT-031."""
    code = "BT-031"


class InsufficientDataError(BacktestError):
    """Not enough historical bars for a meaningful backtest. Code BT-032."""
    code = "BT-032"


# ── Metrics ───────────────────────────────────────────────────────────────────

class MetricsCalculationError(BacktestError):
    """Error during performance metrics calculation. Code BT-040."""
    code = "BT-040"


class InsufficientTradesError(BacktestError):
    """Not enough completed trades to compute statistics. Code BT-041."""
    code = "BT-041"


# ── Reporting ─────────────────────────────────────────────────────────────────

class ReportGenerationError(BacktestError):
    """Error generating backtest report. Code BT-050."""
    code = "BT-050"


# ── Validation ────────────────────────────────────────────────────────────────

class BacktestValidationFrameworkError(BacktestError):
    """General validation framework error. Code BT-060."""
    code = "BT-060"


class WalkForwardError(BacktestError):
    """Walk-forward validation error. Code BT-061."""
    code = "BT-061"


class RobustnessError(BacktestError):
    """Robustness analysis error. Code BT-062."""
    code = "BT-062"


class OverfittingDetectedError(BacktestError):
    """Significant overfitting detected. Code BT-063."""
    code = "BT-063"


# ── Execution ─────────────────────────────────────────────────────────────────

class ExecutionError(BacktestError):
    """Order execution error. Code BT-070."""
    code = "BT-070"


class OrderRejectedError(BacktestError):
    """Order was rejected by the execution simulator. Code BT-071."""
    code = "BT-071"


class InsufficientCapitalError(BacktestError):
    """Insufficient capital to execute order. Code BT-072."""
    code = "BT-072"
