"""enterprise_ai_platform/integration/research/paper_trading/__init__.py

Paper Trading & Market Simulation Framework
==============================================
Production-grade framework for validating investment strategies, execution
workflows, portfolio management, and decision logic in a simulated environment
without risking real capital.

Quick-start::

    from enterprise_ai_platform.integration.research.paper_trading import (
        get_paper_trading_engine,
        PaperAccount,
        PriceBar,
        OrderSignal,
        OrderSide,
        PaperOrderType,
    )

    engine  = get_paper_trading_engine(auto_start=True)
    account = engine.create_account("Strategy A", initial_capital=500_000)
    session = engine.create_session(account.account_id, strategy_id="my_strat")
    result  = await engine.run_session(session.session_id, my_strategy, bars_data)
"""
# ── Public API ────────────────────────────────────────────────────────────────

from enterprise_ai_platform.integration.research.paper_trading.paper_trading_constants import (
    SessionStatus,
    PaperEngineStatus,
    AccountStatus,
    OrderSide,
    PaperOrderType,
    PaperOrderStatus,
    TimeInForce,
    PaperPositionSide,
    ExchangeStatus,
    MarketPhase,
    PTEventType,
    FillModel,
    PAPER_TRADING_ENGINE_VERSION,
    PT_ERROR_PREFIX,
    DEFAULT_INITIAL_CAPITAL,
    DEFAULT_COMMISSION_PCT,
    DEFAULT_SLIPPAGE_PCT,
    DEFAULT_RISK_FREE_RATE,
    TRADING_DAYS_PER_YEAR,
)
from enterprise_ai_platform.integration.research.paper_trading.paper_trading_exceptions import (
    PaperTradingError,
    EngineNotRunningError,
    EngineAlreadyRunningError,
    EngineInitializationError,
    SessionNotFoundError,
    SessionAlreadyExistsError,
    SessionStateError,
    SessionCapacityError,
    AccountNotFoundError,
    AccountError,
    InsufficientCapitalError,
    AccountSuspendedError,
    OrderNotFoundError,
    OrderRejectedError,
    OrderStateError,
    InvalidOrderError,
    PositionNotFoundError,
    PositionError,
    ExecutionError,
    FillError,
    MarketSimulatorError,
    MarketClockError,
    ExchangeError,
    ReportError,
    AnalyticsError,
)
from enterprise_ai_platform.integration.research.paper_trading.core import (
    PaperAccount,
    PaperPosition,
    PaperPortfolio,
    PortfolioSnapshot,
    PaperOrder,
    PaperTrade,
    PaperSession,
    PaperStatistics,
    PaperHistory,
    PaperHistoryEntry,
)
from enterprise_ai_platform.integration.research.paper_trading.market import (
    MarketClock,
    MarketSimulator,
    PriceBar,
    ExchangeSimulator,
    TradingCalendar,
    TradingSessionManager,
    MarketEventGenerator,
    MarketEvent,
)
from enterprise_ai_platform.integration.research.paper_trading.execution import (
    SlippageModel,
    CommissionModel,
    LatencyModel,
    FillSimulator,
    FillResult,
    ExecutionSimulator,
)
from enterprise_ai_platform.integration.research.paper_trading.portfolio import (
    CashManager,
    PositionManager,
    RiskMonitor,
    RiskBreachEvent,
    PerformanceTracker,
    PortfolioSimulator,
)
from enterprise_ai_platform.integration.research.paper_trading.orders    import OrderBook
from enterprise_ai_platform.integration.research.paper_trading.accounts  import AccountManager
from enterprise_ai_platform.integration.research.paper_trading.analytics import PaperAnalytics
from enterprise_ai_platform.integration.research.paper_trading.reporting import (
    TradeReport,
    PortfolioReport,
    SessionSummary,
    SimulationReport,
)
from enterprise_ai_platform.integration.research.paper_trading.simulation import (
    SimulationEngine,
    PaperTradingStrategy,
    PaperSessionResult,
    OrderSignal,
)
from enterprise_ai_platform.integration.research.paper_trading.paper_trading_context  import (
    set_context,
    get_context,
    clear_context,
    scope,
)
from enterprise_ai_platform.integration.research.paper_trading.paper_trading_registry import PaperTradingRegistry
from enterprise_ai_platform.integration.research.paper_trading.paper_trading_factory  import PaperTradingFactory
from enterprise_ai_platform.integration.research.paper_trading.paper_trading_manager  import PaperTradingManager
from enterprise_ai_platform.integration.research.paper_trading.paper_trading_engine   import (
    PaperTradingEngine,
    get_paper_trading_engine,
    reset_paper_trading_engine,
)

__all__ = [
    # Constants
    "SessionStatus", "PaperEngineStatus", "AccountStatus",
    "OrderSide", "PaperOrderType", "PaperOrderStatus", "TimeInForce",
    "PaperPositionSide", "ExchangeStatus", "MarketPhase", "PTEventType", "FillModel",
    "PAPER_TRADING_ENGINE_VERSION", "PT_ERROR_PREFIX",
    "DEFAULT_INITIAL_CAPITAL", "DEFAULT_COMMISSION_PCT", "DEFAULT_SLIPPAGE_PCT",
    "DEFAULT_RISK_FREE_RATE", "TRADING_DAYS_PER_YEAR",
    # Exceptions
    "PaperTradingError",
    "EngineNotRunningError", "EngineAlreadyRunningError", "EngineInitializationError",
    "SessionNotFoundError", "SessionAlreadyExistsError", "SessionStateError",
    "SessionCapacityError",
    "AccountNotFoundError", "AccountError", "InsufficientCapitalError",
    "AccountSuspendedError",
    "OrderNotFoundError", "OrderRejectedError", "OrderStateError", "InvalidOrderError",
    "PositionNotFoundError", "PositionError",
    "ExecutionError", "FillError",
    "MarketSimulatorError", "MarketClockError", "ExchangeError",
    "ReportError", "AnalyticsError",
    # Core models
    "PaperAccount", "PaperPosition", "PaperPortfolio", "PortfolioSnapshot",
    "PaperOrder", "PaperTrade", "PaperSession", "PaperStatistics",
    "PaperHistory", "PaperHistoryEntry",
    # Market
    "MarketClock", "MarketSimulator", "PriceBar",
    "ExchangeSimulator", "TradingCalendar", "TradingSessionManager",
    "MarketEventGenerator", "MarketEvent",
    # Execution
    "SlippageModel", "CommissionModel", "LatencyModel",
    "FillSimulator", "FillResult", "ExecutionSimulator",
    # Portfolio
    "CashManager", "PositionManager", "RiskMonitor", "RiskBreachEvent",
    "PerformanceTracker", "PortfolioSimulator",
    # Orders / Accounts
    "OrderBook", "AccountManager",
    # Analytics / Reporting
    "PaperAnalytics",
    "TradeReport", "PortfolioReport", "SessionSummary", "SimulationReport",
    # Simulation
    "SimulationEngine", "PaperTradingStrategy", "PaperSessionResult", "OrderSignal",
    # Infrastructure
    "set_context", "get_context", "clear_context", "scope",
    "PaperTradingRegistry", "PaperTradingFactory",
    "PaperTradingManager", "PaperTradingEngine",
    "get_paper_trading_engine", "reset_paper_trading_engine",
]
