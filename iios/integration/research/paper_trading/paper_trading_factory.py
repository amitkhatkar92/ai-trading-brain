"""paper_trading_factory.py — Static factory for all Paper Trading Framework components."""
from __future__ import annotations

from iios.integration.research.paper_trading.paper_trading_constants import (
    DEFAULT_COMMISSION_PCT,
    DEFAULT_HISTORY_MAX_ENTRIES,
    DEFAULT_INITIAL_CAPITAL,
    DEFAULT_MAX_ACCOUNTS,
    DEFAULT_MAX_SESSIONS,
    DEFAULT_SLIPPAGE_PCT,
    FillModel,
)
from iios.integration.research.paper_trading.core.paper_history      import PaperHistory
from iios.integration.research.paper_trading.paper_trading_registry  import PaperTradingRegistry
from iios.integration.research.paper_trading.accounts.account_manager import AccountManager
from iios.integration.research.paper_trading.analytics.paper_analytics import PaperAnalytics
from iios.integration.research.paper_trading.execution.commission_model import CommissionModel
from iios.integration.research.paper_trading.execution.fill_simulator   import FillSimulator
from iios.integration.research.paper_trading.execution.latency_model    import LatencyModel
from iios.integration.research.paper_trading.execution.slippage_model   import SlippageModel
from iios.integration.research.paper_trading.execution.execution_simulator import ExecutionSimulator
from iios.integration.research.paper_trading.market.exchange_simulator  import ExchangeSimulator
from iios.integration.research.paper_trading.market.market_clock        import MarketClock
from iios.integration.research.paper_trading.market.market_event_generator import MarketEventGenerator
from iios.integration.research.paper_trading.market.market_simulator    import MarketSimulator
from iios.integration.research.paper_trading.market.trading_session     import TradingCalendar, TradingSessionManager
from iios.integration.research.paper_trading.portfolio.portfolio_simulator import PortfolioSimulator
from iios.integration.research.paper_trading.portfolio.risk_monitor     import RiskMonitor
from iios.integration.research.paper_trading.reporting.simulation_report import SimulationReport
from iios.integration.research.paper_trading.simulation.simulation_engine import SimulationEngine


class PaperTradingFactory:
    """
    Centralised static factory.

    All component creation is isolated here so callers never need to import
    concrete classes directly.
    """

    # ── Core infrastructure ───────────────────────────────────────────────────

    @staticmethod
    def create_registry(max_sessions: int = DEFAULT_MAX_SESSIONS) -> PaperTradingRegistry:
        return PaperTradingRegistry(max_sessions=max_sessions)

    @staticmethod
    def create_account_manager(max_accounts: int = DEFAULT_MAX_ACCOUNTS) -> AccountManager:
        return AccountManager(max_accounts=max_accounts)

    @staticmethod
    def create_history(max_entries: int = DEFAULT_HISTORY_MAX_ENTRIES) -> PaperHistory:
        return PaperHistory(max_entries=max_entries)

    # ── Market ────────────────────────────────────────────────────────────────

    @staticmethod
    def create_market_clock() -> MarketClock:
        return MarketClock()

    @staticmethod
    def create_market_simulator() -> MarketSimulator:
        return MarketSimulator()

    @staticmethod
    def create_exchange_simulator(exchange_id: str = "SIMEX") -> ExchangeSimulator:
        return ExchangeSimulator(exchange_id=exchange_id)

    @staticmethod
    def create_trading_session_manager(
        calendar: TradingCalendar | None = None,
    ) -> TradingSessionManager:
        return TradingSessionManager(calendar=calendar)

    @staticmethod
    def create_event_generator() -> MarketEventGenerator:
        return MarketEventGenerator()

    # ── Execution ─────────────────────────────────────────────────────────────

    @staticmethod
    def create_slippage_model(slippage_pct: float = DEFAULT_SLIPPAGE_PCT) -> SlippageModel:
        return SlippageModel(slippage_pct=slippage_pct)

    @staticmethod
    def create_commission_model(commission_pct: float = DEFAULT_COMMISSION_PCT) -> CommissionModel:
        return CommissionModel(commission_pct=commission_pct)

    @staticmethod
    def create_latency_model() -> LatencyModel:
        return LatencyModel()

    @staticmethod
    def create_fill_simulator(
        slippage_pct:   float    = DEFAULT_SLIPPAGE_PCT,
        commission_pct: float    = DEFAULT_COMMISSION_PCT,
        fill_model:     FillModel = FillModel.NEXT_OPEN,
    ) -> FillSimulator:
        return FillSimulator(
            slippage_model   = SlippageModel(slippage_pct),
            commission_model = CommissionModel(commission_pct),
            latency_model    = LatencyModel(),
            fill_model       = fill_model,
        )

    @staticmethod
    def create_execution_simulator(
        slippage_pct:   float    = DEFAULT_SLIPPAGE_PCT,
        commission_pct: float    = DEFAULT_COMMISSION_PCT,
        fill_model:     FillModel = FillModel.NEXT_OPEN,
    ) -> ExecutionSimulator:
        filler = PaperTradingFactory.create_fill_simulator(
            slippage_pct, commission_pct, fill_model
        )
        return ExecutionSimulator(filler)

    # ── Portfolio ─────────────────────────────────────────────────────────────

    @staticmethod
    def create_risk_monitor() -> RiskMonitor:
        return RiskMonitor()

    # ── Simulation ────────────────────────────────────────────────────────────

    @staticmethod
    def create_simulation_engine(
        commission_pct: float    = DEFAULT_COMMISSION_PCT,
        slippage_pct:   float    = DEFAULT_SLIPPAGE_PCT,
        fill_model:     FillModel = FillModel.NEXT_OPEN,
    ) -> SimulationEngine:
        return SimulationEngine(
            commission_pct = commission_pct,
            slippage_pct   = slippage_pct,
            fill_model     = fill_model,
        )

    # ── Reporting & analytics ─────────────────────────────────────────────────

    @staticmethod
    def create_simulation_report() -> SimulationReport:
        return SimulationReport()

    @staticmethod
    def create_analytics() -> PaperAnalytics:
        return PaperAnalytics()
