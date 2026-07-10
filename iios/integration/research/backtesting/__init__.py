"""iios/integration/research/backtesting/__init__.py

Strategy Backtesting Framework
================================
Production-grade framework for executing deterministic historical simulations,
evaluating investment strategies, measuring performance, and validating robustness.

Quick-start::

    from iios.integration.research.backtesting import (
        get_backtesting_engine,
        BacktestRequest,
        BacktestConfiguration,
        BarEvent,
    )

    engine = get_backtesting_engine(auto_start=True)
    config = BacktestConfiguration(
        symbols         = ["AAPL"],
        initial_capital = 100_000,
    )
    request  = BacktestRequest(strategy_id="my_strat", configuration=config)
    backtest = engine.submit(request)
    result   = await engine.run(backtest.backtest_id, my_strategy_instance, bars_data)
"""
from iios.integration.research.backtesting.backtest_constants   import (
    BacktestStatus, SimulationStatus, BacktestEngineStatus,
    OrderDirection, OrderType, OrderStatus, PositionSide, ExecutionModel,
    ValidationStatus, ReportFormat, BacktestEventType,
    BACKTESTING_ENGINE_VERSION, BACKTEST_ERROR_PREFIX,
    DEFAULT_INITIAL_CAPITAL, DEFAULT_COMMISSION_PCT, DEFAULT_SLIPPAGE_PCT,
    DEFAULT_RISK_FREE_RATE, TRADING_DAYS_PER_YEAR,
)
from iios.integration.research.backtesting.backtest_exceptions   import (
    BacktestError,
    BacktestEngineNotRunningError, BacktestEngineAlreadyRunningError,
    BacktestNotFoundError, BacktestAlreadyExistsError,
    BacktestValidationError, BacktestStateError, BacktestCapacityError,
    SimulationError, SimulationDataError, InsufficientDataError,
    MetricsCalculationError, InsufficientTradesError,
    ReportGenerationError,
    WalkForwardError, OverfittingDetectedError,
    ExecutionError, OrderRejectedError, InsufficientCapitalError,
)
from iios.integration.research.backtesting.core                  import (
    BacktestMetadata, BacktestConfiguration, BacktestRequest,
    Backtest, BacktestSession, BacktestResult, BacktestStatistics,
    BacktestHistory, BacktestHistoryEntry,
)
from iios.integration.research.backtesting.engine               import (
    BarEvent, BacktestStrategy,
    SimulationEngine, MarketSimulator, ExecutionSimulator,
    SimulationClock, EventScheduler,
)
from iios.integration.research.backtesting.execution            import (
    Order, OrderSignal, Fill,
    Trade, Portfolio, Position, PortfolioSnapshot,
)
from iios.integration.research.backtesting.metrics              import (
    PerformanceEngine, PerformanceReport,
    sharpe_ratio, sortino_ratio, calmar_ratio, volatility,
    max_drawdown, win_rate, profit_factor, expectancy,
)
from iios.integration.research.backtesting.reporting            import (
    ReportGenerator, EquityCurveReport, TradeReport,
    BenchmarkReport, ComparisonReport,
)
from iios.integration.research.backtesting.validation           import (
    ValidationEngine, ValidationResult,
    WalkForwardValidator, OutOfSampleValidator,
    OverfittingDetector, OverfittingScore,
    RobustnessAnalyzer,
)
from iios.integration.research.backtesting.backtest_context     import BacktestContext
from iios.integration.research.backtesting.backtest_registry    import BacktestRegistry
from iios.integration.research.backtesting.backtest_factory     import BacktestFactory
from iios.integration.research.backtesting.backtest_manager     import BacktestManager
from iios.integration.research.backtesting.backtesting_engine   import (
    BacktestingEngine,
    get_backtesting_engine,
    reset_backtesting_engine,
)

__all__ = [
    # Constants
    "BacktestStatus", "SimulationStatus", "BacktestEngineStatus",
    "OrderDirection", "OrderType", "OrderStatus", "PositionSide",
    "ExecutionModel", "ValidationStatus", "ReportFormat",
    "BacktestEventType", "BACKTESTING_ENGINE_VERSION",
    "DEFAULT_INITIAL_CAPITAL", "DEFAULT_COMMISSION_PCT",
    "DEFAULT_SLIPPAGE_PCT", "DEFAULT_RISK_FREE_RATE",
    # Exceptions
    "BacktestError", "BacktestEngineNotRunningError", "BacktestEngineAlreadyRunningError",
    "BacktestNotFoundError", "BacktestValidationError", "BacktestStateError",
    "SimulationError", "InsufficientDataError", "MetricsCalculationError",
    "ReportGenerationError", "OverfittingDetectedError",
    # Core models
    "BacktestMetadata", "BacktestConfiguration", "BacktestRequest",
    "Backtest", "BacktestSession", "BacktestResult", "BacktestStatistics",
    "BacktestHistory", "BacktestHistoryEntry",
    # Engine
    "BarEvent", "BacktestStrategy", "SimulationEngine",
    "MarketSimulator", "ExecutionSimulator", "SimulationClock",
    # Execution
    "Order", "OrderSignal", "Fill", "Trade", "Portfolio", "PortfolioSnapshot",
    # Metrics
    "PerformanceEngine", "PerformanceReport",
    "sharpe_ratio", "sortino_ratio", "volatility", "max_drawdown",
    "win_rate", "profit_factor",
    # Reporting
    "ReportGenerator", "ComparisonReport",
    # Validation
    "ValidationEngine", "ValidationResult",
    "WalkForwardValidator", "OutOfSampleValidator",
    "OverfittingDetector", "RobustnessAnalyzer",
    # Top-level
    "BacktestContext", "BacktestRegistry", "BacktestFactory",
    "BacktestManager", "BacktestingEngine",
    "get_backtesting_engine", "reset_backtesting_engine",
]
