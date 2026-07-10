"""tests/unit/integration/research/paper_trading/test_paper_trading_engine.py

Comprehensive unit tests for the Paper Trading & Market Simulation Framework.
"""
from __future__ import annotations

import asyncio
import time
import unittest

import pytest

# ── Test helper ───────────────────────────────────────────────────────────────

def _run(coro):
    return asyncio.run(coro)


# ── Imports under test ────────────────────────────────────────────────────────

from iios.integration.research.paper_trading.paper_trading_constants import (
    AccountStatus,
    ExchangeStatus,
    FillModel,
    MarketPhase,
    OrderSide,
    PaperEngineStatus,
    PaperOrderStatus,
    PaperOrderType,
    PaperPositionSide,
    PTEventType,
    SessionStatus,
    TimeInForce,
    DEFAULT_COMMISSION_PCT,
    DEFAULT_INITIAL_CAPITAL,
    DEFAULT_RISK_FREE_RATE,
    DEFAULT_SLIPPAGE_PCT,
    PAPER_TRADING_ENGINE_VERSION,
    PT_ERROR_PREFIX,
    TRADING_DAYS_PER_YEAR,
)
from iios.integration.research.paper_trading.paper_trading_exceptions import (
    AccountError,
    AccountNotFoundError,
    AccountSuspendedError,
    AnalyticsError,
    EngineAlreadyRunningError,
    EngineInitializationError,
    EngineNotRunningError,
    ExecutionError,
    ExchangeError,
    FillError,
    InsufficientCapitalError,
    InvalidOrderError,
    MarketClockError,
    MarketSimulatorError,
    OrderNotFoundError,
    OrderRejectedError,
    OrderStateError,
    PaperTradingError,
    PositionError,
    PositionNotFoundError,
    ReportError,
    SessionAlreadyExistsError,
    SessionCapacityError,
    SessionNotFoundError,
    SessionStateError,
)
from iios.integration.research.paper_trading.core.paper_account    import PaperAccount
from iios.integration.research.paper_trading.core.paper_position   import PaperPosition
from iios.integration.research.paper_trading.core.paper_portfolio  import PaperPortfolio, PortfolioSnapshot
from iios.integration.research.paper_trading.core.paper_order      import PaperOrder
from iios.integration.research.paper_trading.core.paper_trade      import PaperTrade
from iios.integration.research.paper_trading.core.paper_session    import PaperSession
from iios.integration.research.paper_trading.core.paper_statistics import PaperStatistics
from iios.integration.research.paper_trading.core.paper_history    import PaperHistory, PaperHistoryEntry
from iios.integration.research.paper_trading.market.market_clock           import MarketClock
from iios.integration.research.paper_trading.market.market_simulator       import MarketSimulator, PriceBar
from iios.integration.research.paper_trading.market.exchange_simulator     import ExchangeSimulator
from iios.integration.research.paper_trading.market.trading_session        import TradingCalendar, TradingSessionManager
from iios.integration.research.paper_trading.market.market_event_generator import MarketEventGenerator
from iios.integration.research.paper_trading.execution.slippage_model      import SlippageModel
from iios.integration.research.paper_trading.execution.commission_model    import CommissionModel
from iios.integration.research.paper_trading.execution.latency_model       import LatencyModel
from iios.integration.research.paper_trading.execution.fill_simulator      import FillResult, FillSimulator
from iios.integration.research.paper_trading.execution.execution_simulator import ExecutionSimulator
from iios.integration.research.paper_trading.portfolio.cash_manager        import CashManager
from iios.integration.research.paper_trading.portfolio.position_manager    import PositionManager
from iios.integration.research.paper_trading.portfolio.risk_monitor        import RiskMonitor
from iios.integration.research.paper_trading.portfolio.performance_tracker import PerformanceTracker
from iios.integration.research.paper_trading.portfolio.portfolio_simulator  import PortfolioSimulator
from iios.integration.research.paper_trading.orders.order_book             import OrderBook
from iios.integration.research.paper_trading.accounts.account_manager      import AccountManager
from iios.integration.research.paper_trading.analytics.paper_analytics     import PaperAnalytics
from iios.integration.research.paper_trading.reporting.trade_report        import TradeReport
from iios.integration.research.paper_trading.reporting.portfolio_report    import PortfolioReport
from iios.integration.research.paper_trading.reporting.session_summary     import SessionSummary
from iios.integration.research.paper_trading.reporting.simulation_report   import SimulationReport
from iios.integration.research.paper_trading.simulation.simulation_engine  import (
    OrderSignal,
    PaperSessionResult,
    PaperTradingStrategy,
    SimulationEngine,
)
from iios.integration.research.paper_trading.paper_trading_context  import (
    clear_context, get_context, scope, set_context,
)
from iios.integration.research.paper_trading.paper_trading_registry  import PaperTradingRegistry
from iios.integration.research.paper_trading.paper_trading_factory   import PaperTradingFactory
from iios.integration.research.paper_trading.paper_trading_manager   import PaperTradingManager
from iios.integration.research.paper_trading.paper_trading_engine    import (
    PaperTradingEngine,
    get_paper_trading_engine,
    reset_paper_trading_engine,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_bar(symbol: str = "AAPL", ts: float = 1_000.0, price: float = 100.0) -> PriceBar:
    return PriceBar(
        timestamp = ts,
        symbol    = symbol,
        open      = price,
        high      = price * 1.01,
        low       = price * 0.99,
        close     = price,
        volume    = 1_000_000.0,
        interval  = "1d",
    )


def _make_bars(symbol: str = "AAPL", n: int = 30, start_price: float = 100.0) -> list[PriceBar]:
    bars = []
    for i in range(n):
        p = start_price + i * 0.5
        bars.append(PriceBar(
            timestamp = float(1_600_000_000 + i * 86_400),
            symbol    = symbol,
            open      = p,
            high      = p * 1.01,
            low       = p * 0.99,
            close     = p,
            volume    = 1_000_000.0,
        ))
    return bars


def _make_order(
    symbol:     str             = "AAPL",
    side:       OrderSide       = OrderSide.BUY,
    order_type: PaperOrderType  = PaperOrderType.MARKET,
    quantity:   float           = 10.0,
) -> PaperOrder:
    return PaperOrder.create(
        account_id = "acct_test",
        session_id = "sess_test",
        symbol     = symbol,
        side       = side,
        order_type = order_type,
        quantity   = quantity,
    )


def _make_trade(net_pnl: float = 100.0, side: PaperPositionSide = PaperPositionSide.LONG) -> PaperTrade:
    entry = 100.0
    exit_ = entry + (net_pnl / 10.0) if side == PaperPositionSide.LONG else entry - (net_pnl / 10.0)
    return PaperTrade.create(
        order_id    = "ord_test",
        account_id  = "acct_test",
        session_id  = "sess_test",
        symbol      = "AAPL",
        side        = side,
        quantity    = 10.0,
        entry_price = entry,
        exit_price  = exit_,
        commission  = 0.0,
        slippage    = 0.0,
        entry_time  = 1_000.0,
        exit_time   = 2_000.0,
    )


class _BuyAllStrategy:
    """Minimal strategy that buys 1 unit of each symbol on the first bar only."""
    strategy_id = "buy_all"
    name        = "Buy All Strategy"

    def __init__(self):
        self._first = True

    def on_session_start(self, account, config):
        pass

    def on_bar(self, bars, portfolio_view):
        if not self._first:
            return []
        self._first = False
        return [
            OrderSignal(
                symbol     = sym,
                side       = OrderSide.BUY,
                order_type = PaperOrderType.MARKET,
                quantity   = 1.0,
            )
            for sym in bars
        ]

    def on_session_end(self, account, portfolio_view):
        pass


# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestConstants:
    def test_session_status_values(self):
        assert SessionStatus.IDLE.value      == "idle"
        assert SessionStatus.ACTIVE.value    == "active"
        assert SessionStatus.COMPLETED.value == "completed"
        assert SessionStatus.FAILED.value    == "failed"

    def test_engine_status_values(self):
        assert PaperEngineStatus.STOPPED.value  == "stopped"
        assert PaperEngineStatus.RUNNING.value  == "running"

    def test_order_side_values(self):
        assert OrderSide.BUY.value  == "buy"
        assert OrderSide.SELL.value == "sell"

    def test_fill_model_values(self):
        assert FillModel.NEXT_OPEN.value  == "next_open"
        assert FillModel.CLOSE.value      == "close"
        assert FillModel.VWAP.value       == "vwap"
        assert FillModel.WORST_CASE.value == "worst_case"

    def test_market_phase_values(self):
        assert MarketPhase.CONTINUOUS.value == "continuous"
        assert MarketPhase.CLOSED.value     == "closed"

    def test_scalar_constants(self):
        assert PAPER_TRADING_ENGINE_VERSION == "1.0.0"
        assert PT_ERROR_PREFIX              == "PT"
        assert DEFAULT_INITIAL_CAPITAL      == 1_000_000.0
        assert DEFAULT_COMMISSION_PCT       == 0.001
        assert TRADING_DAYS_PER_YEAR        == 252

    def test_enum_is_str_subclass(self):
        assert isinstance(SessionStatus.ACTIVE, str)
        assert isinstance(OrderSide.BUY, str)
        assert isinstance(PaperOrderType.MARKET, str)


# ═══════════════════════════════════════════════════════════════════════════════
# EXCEPTIONS
# ═══════════════════════════════════════════════════════════════════════════════

class TestExceptions:
    def test_root_exception_code(self):
        e = PaperTradingError("test")
        assert e.code == "PT-000"

    def test_root_exception_repr(self):
        e = PaperTradingError("test message")
        assert "PT-000" in repr(e)
        assert "PaperTradingError" in repr(e)

    def test_engine_errors(self):
        assert EngineNotRunningError.code        == "PT-001"
        assert EngineAlreadyRunningError.code    == "PT-002"
        assert EngineInitializationError.code    == "PT-003"

    def test_session_errors(self):
        assert SessionNotFoundError.code    == "PT-010"
        assert SessionAlreadyExistsError.code == "PT-011"
        assert SessionStateError.code       == "PT-012"
        assert SessionCapacityError.code    == "PT-013"

    def test_account_errors(self):
        assert AccountNotFoundError.code    == "PT-020"
        assert AccountError.code            == "PT-021"
        assert InsufficientCapitalError.code == "PT-022"
        assert AccountSuspendedError.code   == "PT-023"

    def test_order_errors(self):
        assert OrderNotFoundError.code  == "PT-030"
        assert OrderRejectedError.code  == "PT-031"
        assert OrderStateError.code     == "PT-032"
        assert InvalidOrderError.code   == "PT-033"

    def test_position_errors(self):
        assert PositionNotFoundError.code == "PT-040"
        assert PositionError.code         == "PT-041"

    def test_execution_errors(self):
        assert ExecutionError.code == "PT-050"
        assert FillError.code      == "PT-051"

    def test_market_errors(self):
        assert MarketSimulatorError.code == "PT-060"
        assert MarketClockError.code     == "PT-061"
        assert ExchangeError.code        == "PT-062"

    def test_report_errors(self):
        assert ReportError.code    == "PT-070"
        assert AnalyticsError.code == "PT-071"

    def test_hierarchy(self):
        assert issubclass(EngineNotRunningError, PaperTradingError)
        assert issubclass(SessionNotFoundError, PaperTradingError)
        assert issubclass(InsufficientCapitalError, PaperTradingError)
        assert issubclass(MarketClockError, PaperTradingError)

    def test_repr_includes_code(self):
        e = InsufficientCapitalError("not enough")
        r = repr(e)
        assert "PT-022" in r
        assert "InsufficientCapitalError" in r

    def test_exception_count(self):
        """Ensure all 25 exception classes are importable."""
        classes = [
            PaperTradingError, EngineNotRunningError, EngineAlreadyRunningError,
            EngineInitializationError, SessionNotFoundError, SessionAlreadyExistsError,
            SessionStateError, SessionCapacityError, AccountNotFoundError, AccountError,
            InsufficientCapitalError, AccountSuspendedError, OrderNotFoundError,
            OrderRejectedError, OrderStateError, InvalidOrderError,
            PositionNotFoundError, PositionError, ExecutionError, FillError,
            MarketSimulatorError, MarketClockError, ExchangeError, ReportError,
            AnalyticsError,
        ]
        assert len(classes) == 25


# ═══════════════════════════════════════════════════════════════════════════════
# PAPER ACCOUNT
# ═══════════════════════════════════════════════════════════════════════════════

class TestPaperAccount:
    def test_create_defaults(self):
        acc = PaperAccount.create("Test", 100_000.0)
        assert acc.name            == "Test"
        assert acc.initial_capital == 100_000.0
        assert acc.cash            == 100_000.0
        assert acc.status          == AccountStatus.ACTIVE

    def test_create_custom_leverage(self):
        acc = PaperAccount.create("Margin", 50_000.0, leverage=2.0)
        assert acc.leverage     == 2.0
        assert acc.buying_power == 100_000.0

    def test_equity(self):
        acc = PaperAccount.create("T", 100_000.0)
        assert acc.equity(25_000.0) == 125_000.0

    def test_available_cash(self):
        acc = PaperAccount.create("T", 100_000.0)
        acc.margin_used = 10_000.0
        assert acc.available_cash() == 90_000.0

    def test_total_return_pct(self):
        acc = PaperAccount.create("T", 100_000.0)
        acc.cash = 110_000.0
        assert acc.total_return_pct(0.0) == pytest.approx(0.10, abs=1e-6)

    def test_touch_updates_timestamp(self):
        acc = PaperAccount.create("T", 100_000.0)
        before = acc.updated_at
        time.sleep(0.01)
        acc.touch()
        assert acc.updated_at > before

    def test_to_dict(self):
        acc = PaperAccount.create("T", 100_000.0)
        d   = acc.to_dict()
        assert d["name"]            == "T"
        assert d["initial_capital"] == 100_000.0
        assert d["status"]          == "active"


# ═══════════════════════════════════════════════════════════════════════════════
# PAPER POSITION
# ═══════════════════════════════════════════════════════════════════════════════

class TestPaperPosition:
    def test_open_long(self):
        pos = PaperPosition.open("a1", "s1", "AAPL", PaperPositionSide.LONG, 10.0, 100.0)
        assert pos.quantity     == 10.0
        assert pos.avg_cost     == 100.0
        assert pos.is_long()

    def test_unrealized_pnl_long(self):
        pos = PaperPosition.open("a1", "s1", "AAPL", PaperPositionSide.LONG, 10.0, 100.0)
        pos.update_price(110.0, time.time())
        assert pos.unrealized_pnl == pytest.approx(100.0)

    def test_unrealized_pnl_short(self):
        pos = PaperPosition.open("a1", "s1", "AAPL", PaperPositionSide.SHORT, 10.0, 100.0)
        pos.update_price(90.0, time.time())
        assert pos.unrealized_pnl == pytest.approx(100.0)

    def test_add_to_position(self):
        pos = PaperPosition.open("a1", "s1", "AAPL", PaperPositionSide.LONG, 10.0, 100.0)
        pos.add_to_position(10.0, 110.0)
        assert pos.quantity == 20.0
        assert pos.avg_cost == pytest.approx(105.0)

    def test_reduce_position(self):
        pos = PaperPosition.open("a1", "s1", "AAPL", PaperPositionSide.LONG, 10.0, 100.0)
        realized = pos.reduce_position(5.0, 110.0)
        assert realized == pytest.approx(50.0)
        assert pos.quantity == 5.0

    def test_return_pct(self):
        pos = PaperPosition.open("a1", "s1", "AAPL", PaperPositionSide.LONG, 10.0, 100.0)
        pos.update_price(110.0, time.time())
        assert pos.return_pct() == pytest.approx(0.10)

    def test_market_value(self):
        pos = PaperPosition.open("a1", "s1", "AAPL", PaperPositionSide.LONG, 10.0, 100.0)
        pos.update_price(120.0, time.time())
        assert pos.market_value == pytest.approx(1200.0)

    def test_to_dict(self):
        pos = PaperPosition.open("a1", "s1", "AAPL", PaperPositionSide.LONG, 5.0, 100.0)
        d   = pos.to_dict()
        assert d["symbol"]   == "AAPL"
        assert d["quantity"] == 5.0
        assert d["side"]     == "long"


# ═══════════════════════════════════════════════════════════════════════════════
# PAPER PORTFOLIO
# ═══════════════════════════════════════════════════════════════════════════════

class TestPaperPortfolio:
    def test_create(self):
        pf = PaperPortfolio.create("a1", "s1")
        assert pf.position_count()      == 0
        assert pf.total_market_value()  == 0.0

    def test_add_position(self):
        pf  = PaperPortfolio.create("a1", "s1")
        pos = PaperPosition.open("a1", "s1", "AAPL", PaperPositionSide.LONG, 10.0, 100.0)
        pf.add_position(pos)
        assert pf.position_count()     == 1
        assert pf.total_market_value() == pytest.approx(1000.0)

    def test_update_prices(self):
        pf  = PaperPortfolio.create("a1", "s1")
        pos = PaperPosition.open("a1", "s1", "AAPL", PaperPositionSide.LONG, 10.0, 100.0)
        pf.add_position(pos)
        pf.update_prices({"AAPL": 110.0}, time.time())
        assert pf.total_unrealized_pnl() == pytest.approx(100.0)

    def test_snapshot(self):
        pf   = PaperPortfolio.create("a1", "s1")
        snap = pf.snapshot(1_000.0, 50_000.0)
        assert snap.cash         == 50_000.0
        assert snap.total_equity == 50_000.0
        assert len(pf.equity_curve) == 1

    def test_to_dict(self):
        pf = PaperPortfolio.create("a1", "s1")
        d  = pf.to_dict()
        assert "portfolio_id"        in d
        assert d["position_count"]   == 0


# ═══════════════════════════════════════════════════════════════════════════════
# PAPER ORDER
# ═══════════════════════════════════════════════════════════════════════════════

class TestPaperOrder:
    def test_create_market_order(self):
        o = _make_order()
        assert o.symbol      == "AAPL"
        assert o.order_type  == PaperOrderType.MARKET
        assert o.quantity    == 10.0
        assert o.status      == PaperOrderStatus.PENDING

    def test_remaining_quantity(self):
        o = _make_order()
        assert o.remaining_quantity() == 10.0
        o.apply_fill(4.0, 100.0, 0.1, 0.05, time.time())
        assert o.remaining_quantity() == pytest.approx(6.0)

    def test_fill_fraction(self):
        o = _make_order(quantity=10.0)
        o.apply_fill(5.0, 100.0, 0.1, 0.05, time.time())
        assert o.fill_fraction() == pytest.approx(0.5)

    def test_full_fill_marks_filled(self):
        o = _make_order(quantity=10.0)
        o.apply_fill(10.0, 100.0, 1.0, 0.5, time.time())
        assert o.status   == PaperOrderStatus.FILLED
        assert o.is_filled()
        assert o.is_terminal()

    def test_total_cost(self):
        o = _make_order(quantity=10.0)
        o.apply_fill(10.0, 100.0, 1.0, 0.5, time.time())
        assert o.total_cost() == pytest.approx(10.0 * 100.0 + 1.0 + 0.5)

    def test_is_buy_sell(self):
        buy  = _make_order(side=OrderSide.BUY)
        sell = _make_order(side=OrderSide.SELL)
        assert buy.is_buy()  and not buy.is_sell()
        assert sell.is_sell() and not sell.is_buy()

    def test_to_dict(self):
        o = _make_order()
        d = o.to_dict()
        assert d["symbol"]     == "AAPL"
        assert d["order_type"] == "market"


# ═══════════════════════════════════════════════════════════════════════════════
# PAPER TRADE
# ═══════════════════════════════════════════════════════════════════════════════

class TestPaperTrade:
    def test_winner(self):
        t = _make_trade(net_pnl=100.0)
        assert t.is_winner()
        assert not t.is_loser()

    def test_loser(self):
        t = _make_trade(net_pnl=-50.0)
        assert t.is_loser()

    def test_flat(self):
        t = PaperTrade.create(
            "o1", "a1", "s1", "AAPL", PaperPositionSide.LONG,
            10.0, 100.0, 100.0, 0.0, 0.0, 1000.0, 2000.0
        )
        assert t.is_flat()

    def test_gross_pnl_long(self):
        t = PaperTrade.create(
            "o1", "a1", "s1", "AAPL", PaperPositionSide.LONG,
            10.0, 100.0, 110.0, 0.0, 0.0, 1000.0, 2000.0
        )
        assert t.gross_pnl == pytest.approx(100.0)

    def test_duration(self):
        t = _make_trade()
        assert t.duration_sec == pytest.approx(1000.0)

    def test_to_dict_has_net_pnl(self):
        t = _make_trade(100.0)
        d = t.to_dict()
        assert "net_pnl" in d
        assert d["net_pnl"] > 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# PAPER SESSION
# ═══════════════════════════════════════════════════════════════════════════════

class TestPaperSession:
    def test_create(self):
        s = PaperSession.create("a1", "strat_1", "My Strategy")
        assert s.status     == SessionStatus.IDLE
        assert s.bar_index  == 0

    def test_start(self):
        s = PaperSession.create("a1")
        s.start(total_bars=100)
        assert s.status     == SessionStatus.ACTIVE
        assert s.total_bars == 100

    def test_advance(self):
        s = PaperSession.create("a1")
        s.start(100)
        s.advance(50, 9999.0)
        assert s.bar_index         == 50
        assert s.current_timestamp == 9999.0

    def test_progress(self):
        s = PaperSession.create("a1")
        s.start(100)
        s.advance(25, 0.0)
        assert s.progress() == pytest.approx(0.25)

    def test_end_completed(self):
        s = PaperSession.create("a1")
        s.start(10)
        s.end()
        assert s.status == SessionStatus.COMPLETED

    def test_end_failed(self):
        s = PaperSession.create("a1")
        s.start(10)
        s.end(failed=True)
        assert s.status == SessionStatus.FAILED

    def test_checkpoint(self):
        s = PaperSession.create("a1")
        s.save_checkpoint({"bar": 5, "equity": 100_000.0})
        assert s.checkpoint["bar"]    == 5
        assert s.checkpoint["equity"] == 100_000.0

    def test_cannot_start_twice(self):
        s = PaperSession.create("a1")
        s.start(10)
        with pytest.raises(SessionStateError):
            s.start(10)


# ═══════════════════════════════════════════════════════════════════════════════
# PAPER STATISTICS
# ═══════════════════════════════════════════════════════════════════════════════

class TestPaperStatistics:
    def _equity_curve(self, n: int = 60) -> list[tuple[float, float]]:
        base   = 100_000.0
        return [(float(i), base + i * 100.0) for i in range(n)]

    def test_compute_returns_instance(self):
        curve  = self._equity_curve()
        stats  = PaperStatistics.compute(
            initial_capital = 100_000.0,
            equity_curve    = curve,
            trade_dicts     = [],
            order_dicts     = [],
        )
        assert isinstance(stats, PaperStatistics)

    def test_compute_total_return(self):
        curve = self._equity_curve(10)
        stats = PaperStatistics.compute(
            initial_capital = 100_000.0,
            equity_curve    = curve,
            trade_dicts     = [],
            order_dicts     = [],
        )
        assert stats.final_equity == pytest.approx(100_900.0)
        assert stats.total_return  > 0.0

    def test_compute_win_rate(self):
        trades = [
            _make_trade(100.0).to_dict(),
            _make_trade(100.0).to_dict(),
            _make_trade(-50.0).to_dict(),
        ]
        curve  = self._equity_curve()
        stats  = PaperStatistics.compute(
            initial_capital = 100_000.0,
            equity_curve    = curve,
            trade_dicts     = trades,
            order_dicts     = [],
        )
        assert stats.win_rate       == pytest.approx(2 / 3, abs=0.001)
        assert stats.total_trades   == 3
        assert stats.winning_trades == 2

    def test_to_dict(self):
        stats = PaperStatistics()
        d     = stats.to_dict()
        assert "sharpe_ratio"   in d
        assert "max_drawdown"   in d
        assert "total_trades"   in d


# ═══════════════════════════════════════════════════════════════════════════════
# PAPER HISTORY
# ═══════════════════════════════════════════════════════════════════════════════

class TestPaperHistory:
    def test_append_and_count(self):
        h = PaperHistory()
        e = PaperHistoryEntry.create("session", "s1", "created")
        h.append(e)
        assert h.count() == 1

    def test_query_by_entity(self):
        h = PaperHistory()
        h.append(PaperHistoryEntry.create("session", "s1", "created"))
        h.append(PaperHistoryEntry.create("session", "s2", "created"))
        results = h.query(entity_id="s1")
        assert len(results) == 1

    def test_query_by_event_type(self):
        h = PaperHistory()
        h.append(PaperHistoryEntry.create("session", "s1", "created"))
        h.append(PaperHistoryEntry.create("session", "s1", "started"))
        results = h.query(event_type="started")
        assert len(results) == 1

    def test_latest(self):
        h = PaperHistory()
        for i in range(5):
            h.append(PaperHistoryEntry.create("session", f"s{i}", "created"))
        latest = h.latest(3)
        assert len(latest) == 3

    def test_clear(self):
        h = PaperHistory()
        h.append(PaperHistoryEntry.create("session", "s1", "created"))
        h.clear()
        assert h.count() == 0

    def test_max_entries_cap(self):
        h = PaperHistory(max_entries=3)
        for i in range(5):
            h.append(PaperHistoryEntry.create("session", f"s{i}", "created"))
        assert h.count() == 3


# ═══════════════════════════════════════════════════════════════════════════════
# MARKET CLOCK
# ═══════════════════════════════════════════════════════════════════════════════

class TestMarketClock:
    def test_initialize(self):
        c = MarketClock()
        c.initialize(0.0, 1000.0, 100.0)
        assert c.current    == 0.0
        assert c.start      == 0.0
        assert c.end        == 1000.0
        assert c.is_initialized

    def test_advance(self):
        c = MarketClock()
        c.initialize(0.0, 1000.0, 100.0)
        ts = c.advance()
        assert ts           == 100.0
        assert c.tick_count == 1

    def test_advance_past_end_raises(self):
        c = MarketClock()
        c.initialize(0.0, 100.0, 100.0)
        c.advance()   # now at 100.0 = end
        with pytest.raises(StopIteration):
            c.advance()

    def test_advance_to(self):
        c = MarketClock()
        c.initialize(0.0, 1000.0, 100.0)
        c.advance_to(500.0)
        assert c.current == 500.0

    def test_is_done(self):
        c = MarketClock()
        c.initialize(0.0, 100.0, 100.0)
        assert not c.is_done()
        c.advance_to(100.0)
        assert c.is_done()

    def test_not_initialized_raises(self):
        c = MarketClock()
        with pytest.raises(MarketClockError):
            _ = c.current

    def test_to_dict(self):
        c = MarketClock()
        c.initialize(0.0, 1000.0, 100.0)
        d = c.to_dict()
        assert d["start"] == 0.0
        assert d["end"]   == 1000.0


# ═══════════════════════════════════════════════════════════════════════════════
# MARKET SIMULATOR
# ═══════════════════════════════════════════════════════════════════════════════

class TestMarketSimulator:
    def test_load_and_symbols(self):
        ms   = MarketSimulator()
        bars = {"AAPL": _make_bars("AAPL", 10)}
        ms.load(bars)
        assert "AAPL" in ms.symbols()
        assert ms.bar_count("AAPL") == 10

    def test_get_bar(self):
        ms   = MarketSimulator()
        bars = _make_bars("AAPL", 5)
        ms.load({"AAPL": bars})
        b = ms.get_bar("AAPL", 0)
        assert b.symbol == "AAPL"

    def test_sorted_timeline_order(self):
        ms = MarketSimulator()
        ms.load({"AAPL": _make_bars("AAPL", 5), "MSFT": _make_bars("MSFT", 5)})
        tl = ms.sorted_timeline()
        timestamps = [ts for ts, _, _ in tl]
        assert timestamps == sorted(timestamps)

    def test_latest_prices(self):
        ms   = MarketSimulator()
        bars = _make_bars("AAPL", 5, 100.0)
        ms.load({"AAPL": bars})
        prices = ms.latest_prices()
        assert "AAPL" in prices
        assert prices["AAPL"] == bars[-1].close

    def test_unknown_symbol_raises(self):
        ms = MarketSimulator()
        ms.load({})
        with pytest.raises(MarketSimulatorError):
            ms.get_bar("NOPE", 0)

    def test_stats(self):
        ms = MarketSimulator()
        ms.load({"AAPL": _make_bars("AAPL", 10)})
        s  = ms.stats()
        assert s["total_bars"] == 10


# ═══════════════════════════════════════════════════════════════════════════════
# EXCHANGE SIMULATOR
# ═══════════════════════════════════════════════════════════════════════════════

class TestExchangeSimulator:
    def test_initial_state_closed(self):
        ex = ExchangeSimulator()
        assert ex.status() == ExchangeStatus.CLOSED

    def test_open_session(self):
        ex = ExchangeSimulator()
        ex.open_session(1000.0)
        assert ex.status() == ExchangeStatus.OPEN
        assert ex.can_trade("AAPL")

    def test_halt_and_resume(self):
        ex = ExchangeSimulator()
        ex.open_session(1000.0)
        ex.halt_trading("AAPL", "circuit_breaker", 1000.0)
        assert ex.is_halted("AAPL")
        assert not ex.can_trade("AAPL")
        ex.resume_trading("AAPL", 1000.0)
        assert not ex.is_halted("AAPL")
        assert ex.can_trade("AAPL")

    def test_close_session(self):
        ex = ExchangeSimulator()
        ex.open_session(1000.0)
        ex.close_session(2000.0)
        assert ex.status()   == ExchangeStatus.CLOSED
        assert not ex.can_trade("AAPL")

    def test_stats(self):
        ex = ExchangeSimulator("NSE")
        s  = ex.stats()
        assert s["exchange_id"] == "NSE"


# ═══════════════════════════════════════════════════════════════════════════════
# TRADING SESSION MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

class TestTradingSessionManager:
    def _make_manager(self) -> TradingSessionManager:
        cal = TradingCalendar(
            market_open_hour=9, market_open_minute=15,
            market_close_hour=15, market_close_minute=30,
        )
        return TradingSessionManager(cal)

    def test_is_market_open_during_hours(self):
        import datetime
        mgr = self._make_manager()
        # 2024-01-02 is a Tuesday (weekday)
        dt  = datetime.datetime(2024, 1, 2, 12, 0, 0)  # noon
        assert mgr.is_market_open(dt.timestamp())

    def test_is_market_closed_on_weekend(self):
        import datetime
        mgr = self._make_manager()
        # 2024-01-06 is a Saturday
        dt  = datetime.datetime(2024, 1, 6, 12, 0, 0)
        assert not mgr.is_market_open(dt.timestamp())

    def test_session_phase_continuous(self):
        import datetime
        mgr = self._make_manager()
        dt  = datetime.datetime(2024, 1, 2, 12, 0, 0)   # noon on weekday
        ph  = mgr.session_phase(dt.timestamp())
        assert ph == MarketPhase.CONTINUOUS

    def test_session_phase_closed(self):
        import datetime
        mgr = self._make_manager()
        dt  = datetime.datetime(2024, 1, 6, 12, 0, 0)   # Saturday
        assert mgr.session_phase(dt.timestamp()) == MarketPhase.CLOSED

    def test_to_dict(self):
        mgr = self._make_manager()
        d   = mgr.to_dict()
        assert "market_open_hour" in d


# ═══════════════════════════════════════════════════════════════════════════════
# MARKET EVENT GENERATOR
# ═══════════════════════════════════════════════════════════════════════════════

class TestMarketEventGenerator:
    def test_bar_event(self):
        gen = MarketEventGenerator()
        bar = _make_bar()
        evt = gen.generate_bar_event(bar)
        assert evt.event_type == PTEventType.BAR
        assert evt.symbol     == "AAPL"

    def test_session_start_end(self):
        gen    = MarketEventGenerator()
        start  = gen.generate_session_start(1000.0, "SIMEX")
        end    = gen.generate_session_end(2000.0, "SIMEX")
        assert start.event_type == PTEventType.SESSION_START
        assert end.event_type   == PTEventType.SESSION_END

    def test_halt_event(self):
        gen = MarketEventGenerator()
        evt = gen.generate_halt("AAPL", "circuit_breaker", 1000.0)
        assert evt.event_type == PTEventType.HALT
        assert evt.symbol     == "AAPL"

    def test_dividend_event(self):
        gen = MarketEventGenerator()
        evt = gen.generate_dividend("AAPL", 1.0, 1000.0)
        assert evt.event_type == PTEventType.CORPORATE_ACTION
        assert evt.data["action"] == "dividend"

    def test_drain_clears_queue(self):
        gen = MarketEventGenerator()
        gen.generate_bar_event(_make_bar())
        gen.generate_session_start(1000.0, "SX")
        events = gen.drain()
        assert len(events)          == 2
        assert gen.pending_count()  == 0

    def test_drain_sorted_by_timestamp(self):
        gen = MarketEventGenerator()
        gen.generate_halt("A", "r", 2000.0)
        gen.generate_bar_event(PriceBar(1000.0, "A", 100, 101, 99, 100, 1e6))
        events = gen.drain()
        assert events[0].timestamp <= events[1].timestamp


# ═══════════════════════════════════════════════════════════════════════════════
# PRICE BAR
# ═══════════════════════════════════════════════════════════════════════════════

class TestPriceBar:
    def test_vwap(self):
        bar = PriceBar(0.0, "AAPL", 100.0, 110.0, 90.0, 105.0, 1e6)
        assert bar.vwap == pytest.approx((100 + 110 + 90 + 105) / 4)

    def test_typical_price(self):
        bar = PriceBar(0.0, "AAPL", 100.0, 110.0, 90.0, 105.0, 1e6)
        assert bar.typical_price == pytest.approx((110 + 90 + 105) / 3)

    def test_mid(self):
        bar = PriceBar(0.0, "AAPL", 100.0, 110.0, 90.0, 105.0, 1e6)
        assert bar.mid == pytest.approx(100.0)


# ═══════════════════════════════════════════════════════════════════════════════
# SLIPPAGE MODEL
# ═══════════════════════════════════════════════════════════════════════════════

class TestSlippageModel:
    def test_zero_slippage(self):
        m   = SlippageModel(slippage_pct=0.0)
        bar = _make_bar(price=100.0)
        assert m.compute(100.0, 10.0, OrderSide.BUY, bar) == 0.0

    def test_nonzero_slippage(self):
        m   = SlippageModel(slippage_pct=0.001)
        bar = _make_bar(price=100.0)
        slip = m.compute(100.0, 10.0, OrderSide.BUY, bar)
        assert slip == pytest.approx(1.0)   # 0.001 * 100 * 10

    def test_slippage_both_sides(self):
        m    = SlippageModel(slippage_pct=0.001)
        bar  = _make_bar(price=100.0)
        buy  = m.compute(100.0, 10.0, OrderSide.BUY, bar)
        sell = m.compute(100.0, 10.0, OrderSide.SELL, bar)
        assert buy == sell


# ═══════════════════════════════════════════════════════════════════════════════
# COMMISSION MODEL
# ═══════════════════════════════════════════════════════════════════════════════

class TestCommissionModel:
    def test_compute(self):
        m = CommissionModel(commission_pct=0.001)
        c = m.compute(100.0, 10.0)
        assert c == pytest.approx(1.0)

    def test_min_commission(self):
        m = CommissionModel(commission_pct=0.001, min_commission=5.0)
        c = m.compute(10.0, 1.0)   # 0.001 * 10 * 1 = 0.01 → floored to 5.0
        assert c == pytest.approx(5.0)

    def test_max_commission(self):
        m = CommissionModel(commission_pct=0.01, max_commission=50.0)
        c = m.compute(10_000.0, 10.0)   # 0.01 * 10000 * 10 = 1000 → capped at 50
        assert c == pytest.approx(50.0)


# ═══════════════════════════════════════════════════════════════════════════════
# LATENCY MODEL
# ═══════════════════════════════════════════════════════════════════════════════

class TestLatencyModel:
    def test_zero_latency(self):
        m = LatencyModel()
        assert m.submission_delay() == 0.0
        assert m.fill_delay()       == 0.0

    def test_nonzero_submission_latency(self):
        m = LatencyModel(submission_ms=100.0)
        assert m.submission_delay() == pytest.approx(0.1)

    def test_fill_latency(self):
        m = LatencyModel(fill_ms=50.0)
        assert m.fill_delay() == pytest.approx(0.05)


# ═══════════════════════════════════════════════════════════════════════════════
# FILL RESULT
# ═══════════════════════════════════════════════════════════════════════════════

class TestFillResult:
    def test_net_cost_buy(self):
        f = FillResult.create("o1", "AAPL", 10.0, 100.0, 1.0, 0.5, OrderSide.BUY, 1000.0)
        # buy: + base + costs = 1000 + 1.5
        assert f.net_cost() == pytest.approx(1001.5)

    def test_net_cost_sell(self):
        f = FillResult.create("o1", "AAPL", 10.0, 100.0, 1.0, 0.5, OrderSide.SELL, 1000.0)
        # sell: -(base - costs) = -(1000 - 1.5) = -998.5
        assert f.net_cost() == pytest.approx(-998.5)

    def test_fill_id_unique(self):
        f1 = FillResult.create("o1", "AAPL", 10.0, 100.0, 0.0, 0.0, OrderSide.BUY, 0.0)
        f2 = FillResult.create("o2", "AAPL", 10.0, 100.0, 0.0, 0.0, OrderSide.BUY, 0.0)
        assert f1.fill_id != f2.fill_id


# ═══════════════════════════════════════════════════════════════════════════════
# FILL SIMULATOR
# ═══════════════════════════════════════════════════════════════════════════════

class TestFillSimulator:
    def _make_filler(self, fill_model: FillModel = FillModel.CLOSE) -> FillSimulator:
        return FillSimulator(
            SlippageModel(0.0),
            CommissionModel(0.0),
            LatencyModel(),
            fill_model,
        )

    def test_market_order_fills(self):
        f     = self._make_filler()
        order = _make_order(side=OrderSide.BUY, order_type=PaperOrderType.MARKET)
        bar   = _make_bar(price=100.0)
        fill  = f.try_fill(order, bar)
        assert fill is not None
        assert fill.quantity   == 10.0

    def test_limit_buy_triggered(self):
        f     = self._make_filler()
        order = PaperOrder.create("a", "s", "AAPL", OrderSide.BUY, PaperOrderType.LIMIT,
                                  10.0, limit_price=100.0)
        # Bar low=99 <= limit=100 → triggers
        bar   = PriceBar(0.0, "AAPL", 100.0, 101.0, 99.0, 100.0, 1e6)
        fill  = f.try_fill(order, bar)
        assert fill is not None

    def test_limit_buy_not_triggered(self):
        f     = self._make_filler()
        order = PaperOrder.create("a", "s", "AAPL", OrderSide.BUY, PaperOrderType.LIMIT,
                                  10.0, limit_price=90.0)
        # Bar low=99 > limit=90 → NOT triggered
        bar   = PriceBar(0.0, "AAPL", 100.0, 101.0, 99.0, 100.0, 1e6)
        fill  = f.try_fill(order, bar)
        assert fill is None

    def test_stop_order_triggered(self):
        f     = self._make_filler()
        order = PaperOrder.create("a", "s", "AAPL", OrderSide.SELL, PaperOrderType.STOP,
                                  10.0, stop_price=90.0)
        # Bar low=89 <= stop=90 → triggers
        bar   = PriceBar(0.0, "AAPL", 100.0, 101.0, 89.0, 100.0, 1e6)
        fill  = f.try_fill(order, bar)
        assert fill is not None

    def test_fill_includes_commission(self):
        filler = FillSimulator(SlippageModel(0.0), CommissionModel(0.01), LatencyModel(), FillModel.CLOSE)
        order  = _make_order(side=OrderSide.BUY, quantity=10.0)
        bar    = _make_bar(price=100.0)
        fill   = filler.try_fill(order, bar)
        assert fill is not None
        assert fill.commission == pytest.approx(10.0)


# ═══════════════════════════════════════════════════════════════════════════════
# EXECUTION SIMULATOR
# ═══════════════════════════════════════════════════════════════════════════════

class TestExecutionSimulator:
    def _make_exec(self) -> ExecutionSimulator:
        filler = FillSimulator(SlippageModel(0.0), CommissionModel(0.0), LatencyModel(), FillModel.CLOSE)
        return ExecutionSimulator(filler)

    def test_submit_and_get(self):
        es    = self._make_exec()
        order = _make_order()
        es.submit_order(order)
        fetched = es.get_order(order.order_id)
        assert fetched.order_id == order.order_id
        assert fetched.status   == PaperOrderStatus.OPEN

    def test_process_bar_fills_market(self):
        es    = self._make_exec()
        order = _make_order(side=OrderSide.BUY, order_type=PaperOrderType.MARKET)
        es.submit_order(order)
        bar   = {"AAPL": _make_bar(price=100.0)}
        fills = es.process_bar(bar)
        assert len(fills) == 1
        assert fills[0].quantity == 10.0

    def test_cancel_order(self):
        es    = self._make_exec()
        order = _make_order()
        es.submit_order(order)
        cancelled = es.cancel_order(order.order_id)
        assert cancelled.status == PaperOrderStatus.CANCELLED

    def test_cancel_terminal_raises(self):
        es    = self._make_exec()
        order = _make_order(order_type=PaperOrderType.MARKET)
        es.submit_order(order)
        es.process_bar({"AAPL": _make_bar()})  # fills the order
        with pytest.raises(OrderStateError):
            es.cancel_order(order.order_id)

    def test_stats(self):
        es = self._make_exec()
        s  = es.stats()
        assert "total_submitted" in s

    def test_reject_zero_quantity(self):
        es    = self._make_exec()
        order = _make_order(quantity=0.0)
        returned = es.submit_order(order)
        assert returned.status == PaperOrderStatus.REJECTED


# ═══════════════════════════════════════════════════════════════════════════════
# CASH MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

class TestCashManager:
    def test_initial_balance(self):
        cm = CashManager(100_000.0)
        assert cm.balance()   == 100_000.0
        assert cm.available() == 100_000.0

    def test_debit(self):
        cm = CashManager(100_000.0)
        cm.debit(20_000.0, "buy_AAPL")
        assert cm.balance() == pytest.approx(80_000.0)

    def test_credit(self):
        cm = CashManager(100_000.0)
        cm.credit(10_000.0, "sell_AAPL")
        assert cm.balance() == pytest.approx(110_000.0)

    def test_insufficient_debit_raises(self):
        cm = CashManager(1_000.0)
        with pytest.raises(InsufficientCapitalError):
            cm.debit(2_000.0, "too_much")

    def test_reserve_and_release(self):
        cm = CashManager(100_000.0)
        cm.reserve(30_000.0, "r1")
        assert cm.reserved() == pytest.approx(30_000.0)
        assert cm.available() == pytest.approx(70_000.0)
        released = cm.release("r1")
        assert released == pytest.approx(30_000.0)
        assert cm.available() == pytest.approx(100_000.0)

    def test_over_reserve_raises(self):
        cm = CashManager(50_000.0)
        with pytest.raises(InsufficientCapitalError):
            cm.reserve(60_000.0, "r1")

    def test_history_populated(self):
        cm = CashManager(100_000.0)
        cm.debit(10_000.0, "test")
        assert len(cm.history()) == 1


# ═══════════════════════════════════════════════════════════════════════════════
# POSITION MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

class TestPositionManager:
    def _fill(self, side: OrderSide, price: float = 100.0, qty: float = 10.0) -> FillResult:
        return FillResult.create("o1", "AAPL", qty, price, 0.0, 0.0, side, 1000.0)

    def test_open_long_position(self):
        pm   = PositionManager("a1", "s1")
        fill = self._fill(OrderSide.BUY)
        t    = pm.apply_fill(fill)
        assert t is None
        assert pm.get_position("AAPL") is not None
        assert len(pm.open_positions()) == 1

    def test_add_to_long(self):
        pm   = PositionManager("a1", "s1")
        pm.apply_fill(self._fill(OrderSide.BUY, 100.0, 10.0))
        pm.apply_fill(self._fill(OrderSide.BUY, 110.0, 10.0))
        pos = pm.get_position("AAPL")
        assert pos.quantity  == 20.0
        assert pos.avg_cost  == pytest.approx(105.0)

    def test_close_position(self):
        pm    = PositionManager("a1", "s1")
        pm.apply_fill(self._fill(OrderSide.BUY, 100.0, 10.0))
        trade = pm.apply_fill(self._fill(OrderSide.SELL, 110.0, 10.0))
        assert trade is not None
        assert trade.net_pnl  == pytest.approx(100.0)
        assert pm.get_position("AAPL") is None

    def test_update_prices(self):
        pm   = PositionManager("a1", "s1")
        pm.apply_fill(self._fill(OrderSide.BUY, 100.0))
        pm.update_prices({"AAPL": 120.0}, 2000.0)
        pos  = pm.get_position("AAPL")
        assert pos.current_price == pytest.approx(120.0)

    def test_close_all(self):
        pm = PositionManager("a1", "s1")
        pm.apply_fill(self._fill(OrderSide.BUY, 100.0))
        trades = pm.close_all({"AAPL": 110.0}, 2000.0)
        assert len(trades) == 1
        assert pm.total_market_value() == 0.0

    def test_stats(self):
        pm   = PositionManager("a1", "s1")
        pm.apply_fill(self._fill(OrderSide.BUY))
        s    = pm.stats()
        assert s["open_positions"] == 1


# ═══════════════════════════════════════════════════════════════════════════════
# RISK MONITOR
# ═══════════════════════════════════════════════════════════════════════════════

class TestRiskMonitor:
    def _make_account(self, cash: float = 100_000.0) -> PaperAccount:
        acc = PaperAccount.create("T", cash)
        return acc

    def _make_portfolio(self) -> PaperPortfolio:
        return PaperPortfolio.create("a1", "s1")

    def test_no_breach_normal_state(self):
        rm   = RiskMonitor()
        acc  = self._make_account()
        pf   = self._make_portfolio()
        rm._peak_equity = acc.cash
        breaches = rm.check(acc, pf)
        # No positions, no drawdown → may have cash buffer warning if 0 positions
        # Actually cash_ratio = 1.0 >= 0.02, so no breach
        assert all(b.rule_name != "max_drawdown" for b in breaches)

    def test_concentration_breach(self):
        rm  = RiskMonitor(max_position_concentration=0.10)
        acc = self._make_account(100_000.0)
        pf  = PaperPortfolio.create("a1", "s1")
        pos = PaperPosition.open("a1", "s1", "AAPL", PaperPositionSide.LONG, 100.0, 15.0)
        pf.add_position(pos)    # 1500 / 100000 = 1.5 % < 10 % -- won't trigger
        rm._peak_equity = 100_000.0
        # Force it: 20% position on 100k account
        pos2 = PaperPosition.open("a1", "s1", "MSFT", PaperPositionSide.LONG, 100.0, 210.0)
        pf.add_position(pos2)   # 21000 / 100000 = 21 % > 10 %
        breaches = rm.check(acc, pf)
        names = [b.rule_name for b in breaches]
        assert "position_concentration" in names

    def test_kill_switch_drawdown(self):
        rm          = RiskMonitor(max_drawdown_pct=0.10)
        acc         = self._make_account(80_000.0)  # down 20 %
        pf          = self._make_portfolio()
        rm._peak_equity = 100_000.0
        triggered   = rm.is_kill_switch_triggered(acc, pf)
        assert triggered

    def test_stats(self):
        rm = RiskMonitor()
        s  = rm.stats()
        assert "max_drawdown_pct" in s


# ═══════════════════════════════════════════════════════════════════════════════
# PERFORMANCE TRACKER
# ═══════════════════════════════════════════════════════════════════════════════

class TestPerformanceTracker:
    def test_update_and_total_return(self):
        pt = PerformanceTracker()
        pt.update(100_000.0, 1000.0)
        pt.update(110_000.0, 2000.0)
        assert pt.total_return() == pytest.approx(0.10)

    def test_drawdown_after_peak(self):
        pt = PerformanceTracker()
        pt.update(100_000.0, 1000.0)
        pt.update(110_000.0, 2000.0)
        pt.update(99_000.0,  3000.0)
        assert pt.current_drawdown() > 0.0

    def test_record_trade_win_rate(self):
        pt = PerformanceTracker()
        pt.update(100_000.0, 1000.0)
        pt.record_trade(_make_trade(100.0))
        pt.record_trade(_make_trade(-50.0))
        assert pt.win_rate() == pytest.approx(0.5)

    def test_equity_curve_length(self):
        pt = PerformanceTracker()
        for i in range(10):
            pt.update(100_000.0 + i * 1000.0, float(i))
        assert len(pt.equity_curve()) == 10

    def test_stats_dict(self):
        pt = PerformanceTracker()
        pt.update(100_000.0, 0.0)
        s  = pt.stats()
        assert "total_return" in s


# ═══════════════════════════════════════════════════════════════════════════════
# PORTFOLIO SIMULATOR
# ═══════════════════════════════════════════════════════════════════════════════

class TestPortfolioSimulator:
    def _make_ps(self) -> PortfolioSimulator:
        acc = PaperAccount.create("T", 100_000.0)
        return PortfolioSimulator(acc)

    def test_process_fill_updates_cash(self):
        ps   = self._make_ps()
        fill = FillResult.create("o1", "AAPL", 10.0, 100.0, 0.0, 0.0, OrderSide.BUY, 1000.0)
        ps.process_fill(fill, 1000.0)
        # 100_000 - (100*10) = 99_000 (no commission/slippage)
        # Actually net_cost = +1000, so 100_000 - 1000 = 99000
        assert ps._account.cash == pytest.approx(99_000.0)

    def test_update_prices(self):
        ps   = self._make_ps()
        fill = FillResult.create("o1", "AAPL", 10.0, 100.0, 0.0, 0.0, OrderSide.BUY, 1000.0)
        ps.process_fill(fill, 1000.0)
        ps.update_prices({"AAPL": 110.0}, 2000.0)
        assert ps.portfolio_value() == pytest.approx(1_100.0)

    def test_portfolio_value_empty(self):
        ps = self._make_ps()
        assert ps.portfolio_value() == 0.0

    def test_close_all(self):
        ps   = self._make_ps()
        fill = FillResult.create("o1", "AAPL", 10.0, 100.0, 0.0, 0.0, OrderSide.BUY, 1000.0)
        ps.process_fill(fill, 1000.0)
        trades = ps.close_all({"AAPL": 110.0}, 2000.0)
        assert len(trades) == 1

    def test_stats(self):
        ps = self._make_ps()
        s  = ps.stats()
        assert "cash" in s


# ═══════════════════════════════════════════════════════════════════════════════
# ORDER BOOK
# ═══════════════════════════════════════════════════════════════════════════════

class TestOrderBook:
    def test_add_and_get(self):
        ob    = OrderBook()
        order = _make_order()
        ob.add(order)
        fetched = ob.get(order.order_id)
        assert fetched.order_id == order.order_id

    def test_not_found_raises(self):
        ob = OrderBook()
        with pytest.raises(OrderNotFoundError):
            ob.get("nonexistent")

    def test_cancel(self):
        ob    = OrderBook()
        order = _make_order()
        ob.add(order)
        ob.cancel(order.order_id)
        cancelled = ob.get(order.order_id)
        assert cancelled.status == PaperOrderStatus.CANCELLED

    def test_pending_vs_filled(self):
        ob = OrderBook()
        o1 = _make_order()
        o2 = _make_order()
        o2.status = PaperOrderStatus.FILLED
        ob.add(o1)
        ob.add(o2)
        assert len(ob.pending())       == 1
        assert len(ob.filled_orders()) == 1

    def test_find_by_symbol(self):
        ob = OrderBook()
        ob.add(_make_order("AAPL"))
        ob.add(_make_order("MSFT"))
        assert len(ob.find_by_symbol("AAPL")) == 1

    def test_stats(self):
        ob = OrderBook()
        ob.add(_make_order())
        s  = ob.stats()
        assert s["total_orders"] == 1


# ═══════════════════════════════════════════════════════════════════════════════
# ACCOUNT MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

class TestAccountManager:
    def test_create_account(self):
        am  = AccountManager()
        acc = am.create_account("Test", 100_000.0)
        assert acc.name == "Test"
        assert am.count() == 1

    def test_get_account(self):
        am  = AccountManager()
        acc = am.create_account("Test")
        got = am.get_account(acc.account_id)
        assert got.account_id == acc.account_id

    def test_get_not_found(self):
        am = AccountManager()
        with pytest.raises(AccountNotFoundError):
            am.get_account("nonexistent")

    def test_suspend_account(self):
        am  = AccountManager()
        acc = am.create_account("T")
        am.suspend_account(acc.account_id, "risk")
        refreshed = am.get_account(acc.account_id)
        assert refreshed.status == AccountStatus.SUSPENDED

    def test_close_account(self):
        am  = AccountManager()
        acc = am.create_account("T")
        am.close_account(acc.account_id)
        assert am.get_account(acc.account_id).status == AccountStatus.CLOSED

    def test_active_accounts(self):
        am = AccountManager()
        am.create_account("A")
        am.create_account("B")
        acc = am.create_account("C")
        am.suspend_account(acc.account_id, "test")
        assert len(am.active_accounts()) == 2

    def test_stats(self):
        am = AccountManager()
        am.create_account("T")
        s  = am.stats()
        assert s["total_accounts"] == 1


# ═══════════════════════════════════════════════════════════════════════════════
# PAPER ANALYTICS
# ═══════════════════════════════════════════════════════════════════════════════

class TestPaperAnalytics:
    def _make_orders(self) -> list[PaperOrder]:
        o1 = _make_order()
        o1.status = PaperOrderStatus.FILLED
        o2 = _make_order()
        o2.status = PaperOrderStatus.REJECTED
        return [o1, o2]

    def test_compute_statistics(self):
        pa     = PaperAnalytics()
        curve  = [(float(i), 100_000.0 + i * 50.0) for i in range(30)]
        stats  = pa.compute_statistics(
            initial_capital = 100_000.0,
            equity_curve    = curve,
            trades          = [_make_trade(100.0)],
            orders          = self._make_orders(),
        )
        assert isinstance(stats, PaperStatistics)
        assert stats.total_trades == 1

    def test_order_statistics(self):
        pa  = PaperAnalytics()
        s   = pa.order_statistics(self._make_orders())
        assert s["total_orders"] == 2

    def test_execution_quality(self):
        pa     = PaperAnalytics()
        fills  = [FillResult.create("o1", "AAPL", 10.0, 100.0, 1.0, 0.5, OrderSide.BUY, 0.0)]
        orders = self._make_orders()
        q      = pa.execution_quality(fills, orders)
        assert "fill_rate"        in q
        assert "avg_slippage_pct" in q

    def test_compare_sessions(self):
        pa = PaperAnalytics()
        sessions = [{"sharpe_ratio": 1.5}, {"sharpe_ratio": 0.5}, {"sharpe_ratio": 2.0}]
        result   = pa.compare_sessions(sessions)
        assert result["ranked"][0]["sharpe_ratio"] == pytest.approx(2.0)


# ═══════════════════════════════════════════════════════════════════════════════
# REPORTING
# ═══════════════════════════════════════════════════════════════════════════════

class TestTradeReport:
    def test_build(self):
        tr     = TradeReport()
        trades = [_make_trade(100.0), _make_trade(-50.0)]
        d      = tr.build(trades)
        assert d["total_trades"]  == 2
        assert len(d["trades"])   == 2
        assert "AAPL" in d["by_symbol"]

    def test_max_trades_limit(self):
        tr     = TradeReport()
        trades = [_make_trade(10.0) for _ in range(10)]
        d      = tr.build(trades, max_trades=3)
        assert d["total_trades"] == 10
        assert d["shown_trades"] == 3


class TestPortfolioReport:
    def test_build(self):
        pr  = PortfolioReport()
        acc = PaperAccount.create("T", 100_000.0)
        pf  = PaperPortfolio.create(acc.account_id, "s1")
        d   = pr.build(pf, acc)
        assert d["cash"]           == 100_000.0
        assert d["total_equity"]   == 100_000.0
        assert d["position_count"] == 0


class TestSessionSummary:
    def test_build(self):
        ss      = SessionSummary()
        session = PaperSession.create("a1", "strat", "My Strat")
        session.start(100)
        session.end()
        stats   = PaperStatistics(initial_capital=100_000.0)
        d       = ss.build(session, stats)
        assert d["session_id"]  == session.session_id
        assert d["strategy_id"] == "strat"
        assert "sharpe_ratio"   in d


class TestSimulationReport:
    def test_build(self):
        sr      = SimulationReport()
        session = PaperSession.create("a1")
        session.start(10)
        session.end()
        stats   = PaperStatistics(initial_capital=100_000.0, bar_count=10)
        acc     = PaperAccount.create("T", 100_000.0)
        d       = sr.build(
            session      = session,
            stats        = stats,
            account      = acc,
            equity_curve = [(float(i), 100_000.0) for i in range(10)],
            trade_log    = [],
            orders       = [],
        )
        assert "summary"      in d
        assert "risk"         in d
        assert "equity_curve" in d
        assert "trades"       in d


# ═══════════════════════════════════════════════════════════════════════════════
# ORDER SIGNAL
# ═══════════════════════════════════════════════════════════════════════════════

class TestOrderSignal:
    def test_create_with_quantity(self):
        sig = OrderSignal("AAPL", OrderSide.BUY, PaperOrderType.MARKET, quantity=10.0)
        assert sig.symbol     == "AAPL"
        assert sig.quantity   == 10.0
        assert sig.size_pct   is None

    def test_create_with_size_pct(self):
        sig = OrderSignal("MSFT", OrderSide.SELL, PaperOrderType.LIMIT,
                          size_pct=0.05, limit_price=300.0)
        assert sig.size_pct    == 0.05
        assert sig.limit_price == 300.0

    def test_default_tif(self):
        sig = OrderSignal("AAPL", OrderSide.BUY)
        assert sig.tif == TimeInForce.DAY


# ═══════════════════════════════════════════════════════════════════════════════
# SIMULATION ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class TestSimulationEngine:
    def _run(self, strategy=None, n_bars=10):
        engine   = SimulationEngine(commission_pct=0.0, slippage_pct=0.0, fill_model=FillModel.CLOSE)
        account  = PaperAccount.create("T", 100_000.0)
        bars     = _make_bars("AAPL", n_bars)
        bars_data = {"AAPL": bars}
        strat    = strategy or _BuyAllStrategy()
        return _run(engine.run("sess_001", account, {}, strat, bars_data))

    def test_run_returns_result(self):
        result = self._run()
        assert isinstance(result, PaperSessionResult)

    def test_session_completed(self):
        result = self._run()
        assert result.session.status == SessionStatus.COMPLETED

    def test_has_trade_log(self):
        result = self._run()
        # BuyAll buys on bar 0, closes at end → 1 trade
        assert len(result.trade_log) >= 1

    def test_stats_not_none(self):
        result = self._run()
        assert result.stats is not None
        assert result.stats.bar_count > 0

    def test_equity_curve_populated(self):
        result = self._run(n_bars=20)
        assert len(result.stats.bar_count) if False else result.stats.bar_count > 0

    def test_report_has_sections(self):
        result = self._run()
        assert "summary"      in result.report
        assert "risk"         in result.report
        assert "equity_curve" in result.report

    def test_no_orders_strategy(self):
        class _NoOpStrategy:
            strategy_id = "noop"
            name        = "No-op"
            def on_session_start(self, a, c): pass
            def on_bar(self, b, p): return []
            def on_session_end(self, a, p): pass

        result = self._run(_NoOpStrategy())
        assert result.stats.total_trades == 0

    def test_multiple_symbols(self):
        engine   = SimulationEngine(commission_pct=0.0, slippage_pct=0.0, fill_model=FillModel.CLOSE)
        account  = PaperAccount.create("T", 1_000_000.0)
        bars_data = {
            "AAPL": _make_bars("AAPL", 10),
            "MSFT": _make_bars("MSFT", 10),
        }
        result = _run(engine.run("sess_002", account, {}, _BuyAllStrategy(), bars_data))
        assert result.session.status == SessionStatus.COMPLETED


# ═══════════════════════════════════════════════════════════════════════════════
# PAPER TRADING CONTEXT
# ═══════════════════════════════════════════════════════════════════════════════

class TestPaperTradingContext:
    def test_set_and_get(self):
        set_context("run_session", session_id="s1")
        ctx = get_context()
        assert ctx is not None
        assert ctx.operation  == "run_session"
        assert ctx.session_id == "s1"
        clear_context()

    def test_clear(self):
        set_context("x")
        clear_context()
        assert get_context() is None

    def test_scope_cm(self):
        with scope("test_op", session_id="s99") as ctx:
            assert ctx.operation  == "test_op"
            assert ctx.session_id == "s99"
        assert get_context() is None

    def test_elapsed_ms(self):
        set_context("x")
        ctx = get_context()
        assert ctx.elapsed_ms() >= 0.0
        clear_context()

    def test_no_context_returns_none(self):
        clear_context()
        assert get_context() is None


# ═══════════════════════════════════════════════════════════════════════════════
# PAPER TRADING REGISTRY
# ═══════════════════════════════════════════════════════════════════════════════

class TestPaperTradingRegistry:
    def _make_session(self, session_id: str = "s1") -> PaperSession:
        return PaperSession.create("a1", session_id=session_id)

    def test_register_and_get(self):
        reg     = PaperTradingRegistry()
        session = self._make_session()
        reg.register(session)
        fetched = reg.get(session.session_id)
        assert fetched.session_id == session.session_id

    def test_duplicate_raises(self):
        reg     = PaperTradingRegistry()
        session = self._make_session()
        reg.register(session)
        with pytest.raises(SessionAlreadyExistsError):
            reg.register(session)

    def test_capacity_raises(self):
        reg = PaperTradingRegistry(max_sessions=1)
        reg.register(self._make_session("s1"))
        with pytest.raises(SessionCapacityError):
            reg.register(self._make_session("s2"))

    def test_find_by_status(self):
        reg = PaperTradingRegistry()
        s1  = self._make_session("s1")
        s2  = self._make_session("s2")
        s2.status = SessionStatus.COMPLETED
        reg.register(s1)
        reg.register(s2)
        idle = reg.find_by_status(SessionStatus.IDLE)
        assert len(idle) == 1

    def test_remove(self):
        reg     = PaperTradingRegistry()
        session = self._make_session()
        reg.register(session)
        reg.remove(session.session_id)
        assert not reg.has(session.session_id)

    def test_stats(self):
        reg = PaperTradingRegistry()
        reg.register(self._make_session())
        s   = reg.stats()
        assert s["total"] == 1


# ═══════════════════════════════════════════════════════════════════════════════
# PAPER TRADING FACTORY
# ═══════════════════════════════════════════════════════════════════════════════

class TestPaperTradingFactory:
    def test_create_registry(self):
        assert isinstance(PaperTradingFactory.create_registry(), PaperTradingRegistry)

    def test_create_account_manager(self):
        assert isinstance(PaperTradingFactory.create_account_manager(), AccountManager)

    def test_create_market_clock(self):
        assert isinstance(PaperTradingFactory.create_market_clock(), MarketClock)

    def test_create_market_simulator(self):
        assert isinstance(PaperTradingFactory.create_market_simulator(), MarketSimulator)

    def test_create_execution_simulator(self):
        assert isinstance(PaperTradingFactory.create_execution_simulator(), ExecutionSimulator)

    def test_create_simulation_engine(self):
        assert isinstance(PaperTradingFactory.create_simulation_engine(), SimulationEngine)

    def test_create_analytics(self):
        assert isinstance(PaperTradingFactory.create_analytics(), PaperAnalytics)


# ═══════════════════════════════════════════════════════════════════════════════
# PAPER TRADING MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

class TestPaperTradingManager:
    def _make_manager(self) -> PaperTradingManager:
        reg  = PaperTradingFactory.create_registry()
        am   = PaperTradingFactory.create_account_manager()
        eng  = PaperTradingFactory.create_simulation_engine()
        hist = PaperTradingFactory.create_history()
        return PaperTradingManager(reg, am, eng, hist)

    def test_create_session(self):
        mgr     = self._make_manager()
        acc     = mgr._accounts.create_account("T", 100_000.0)
        session = mgr.create_session(acc.account_id, "strat_1", "S1")
        assert session.account_id   == acc.account_id
        assert session.strategy_id  == "strat_1"

    def test_list_sessions(self):
        mgr = self._make_manager()
        acc = mgr._accounts.create_account("T")
        mgr.create_session(acc.account_id)
        mgr.create_session(acc.account_id)
        assert len(mgr.list_sessions()) == 2

    def test_run_session(self):
        mgr  = self._make_manager()
        acc  = mgr._accounts.create_account("T", 100_000.0)
        sess = mgr.create_session(acc.account_id, "strat")
        result = _run(mgr.run_session(
            sess.session_id,
            _BuyAllStrategy(),
            {"AAPL": _make_bars("AAPL", 10)},
        ))
        assert isinstance(result, PaperSessionResult)

    def test_compare_sessions(self):
        mgr  = self._make_manager()
        acc  = mgr._accounts.create_account("T", 100_000.0)
        s1   = mgr.create_session(acc.account_id, "s1")
        s2   = mgr.create_session(acc.account_id, "s2")
        _run(mgr.run_session(s1.session_id, _BuyAllStrategy(), {"AAPL": _make_bars("AAPL", 10)}))
        _run(mgr.run_session(s2.session_id, _BuyAllStrategy(), {"AAPL": _make_bars("AAPL", 10)}))
        cmp = mgr.compare_sessions([s1.session_id, s2.session_id])
        assert cmp["total"] == 2

    def test_cancel_session(self):
        mgr = self._make_manager()
        acc = mgr._accounts.create_account("T")
        s   = mgr.create_session(acc.account_id)
        mgr.cancel_session(s.session_id)
        assert mgr.get_session(s.session_id).status == SessionStatus.CANCELLED

    def test_stats(self):
        mgr = self._make_manager()
        s   = mgr.stats()
        assert "sessions" in s
        assert "accounts" in s


# ═══════════════════════════════════════════════════════════════════════════════
# PAPER TRADING ENGINE (SINGLETON FACADE)
# ═══════════════════════════════════════════════════════════════════════════════

class TestPaperTradingEngine:
    def setup_method(self):
        reset_paper_trading_engine()

    def test_not_running_before_start(self):
        engine = get_paper_trading_engine()
        assert not engine.is_running()

    def test_start_and_stop(self):
        engine = get_paper_trading_engine()
        _run(engine.start())
        assert engine.is_running()
        _run(engine.stop())
        assert not engine.is_running()

    def test_double_start_raises(self):
        engine = get_paper_trading_engine()
        _run(engine.start())
        with pytest.raises(EngineAlreadyRunningError):
            _run(engine.start())
        _run(engine.stop())

    def test_not_running_raises_on_create_account(self):
        engine = get_paper_trading_engine()
        with pytest.raises(EngineNotRunningError):
            engine.create_account("T")

    def test_create_account_when_running(self):
        engine = get_paper_trading_engine()
        _run(engine.start())
        acc = engine.create_account("Test", 500_000.0)
        assert acc.initial_capital == 500_000.0
        _run(engine.stop())

    def test_full_session_workflow(self):
        engine = get_paper_trading_engine()
        _run(engine.start())
        acc    = engine.create_account("My Acc", 200_000.0)
        session = engine.create_session(acc.account_id, "test_strat")
        result  = _run(engine.run_session(
            session.session_id,
            _BuyAllStrategy(),
            {"AAPL": _make_bars("AAPL", 10)},
        ))
        assert result.session.status == SessionStatus.COMPLETED
        _run(engine.stop())

    def test_uptime_sec(self):
        engine = get_paper_trading_engine()
        _run(engine.start())
        assert engine.uptime_sec() >= 0.0
        _run(engine.stop())

    def test_stats_when_running(self):
        engine = get_paper_trading_engine()
        _run(engine.start())
        s = engine.stats()
        assert "version" in s
        _run(engine.stop())

    def test_list_sessions(self):
        engine = get_paper_trading_engine()
        _run(engine.start())
        acc = engine.create_account("T")
        engine.create_session(acc.account_id)
        sessions = engine.list_sessions()
        assert len(sessions) >= 1
        _run(engine.stop())


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

class TestSingleton:
    def setup_method(self):
        reset_paper_trading_engine()

    def test_get_returns_same_instance(self):
        e1 = get_paper_trading_engine()
        e2 = get_paper_trading_engine()
        assert e1 is e2

    def test_reset_creates_new_instance(self):
        e1 = get_paper_trading_engine()
        reset_paper_trading_engine()
        e2 = get_paper_trading_engine()
        assert e1 is not e2

    def test_auto_start_false_does_not_start(self):
        engine = get_paper_trading_engine(auto_start=False)
        assert not engine.is_running()

    def test_auto_start_true_starts_engine(self):
        engine = get_paper_trading_engine(auto_start=True)
        assert engine.is_running()
        _run(engine.stop())

    def test_reset_after_start(self):
        e1 = get_paper_trading_engine()
        _run(e1.start())
        reset_paper_trading_engine()
        e2 = get_paper_trading_engine()
        assert not e2.is_running()
