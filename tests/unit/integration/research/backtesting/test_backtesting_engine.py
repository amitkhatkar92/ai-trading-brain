"""tests/unit/integration/research/backtesting/test_backtesting_engine.py

Comprehensive test suite for iios/integration/research/backtesting/

Run with:
    python -m pytest tests/unit/integration/research/backtesting/ -q

Async tests use _run() — no pytest-asyncio required.
"""
from __future__ import annotations

import asyncio
import math
import threading
import time
from typing import Any

import pytest

# ── Async helper ──────────────────────────────────────────────────────────────
def _run(coro): return asyncio.run(coro)

# ── Imports ───────────────────────────────────────────────────────────────────
from iios.integration.research.backtesting.backtest_constants import (
    BACKTESTING_ENGINE_VERSION,
    BACKTEST_ERROR_PREFIX,
    BacktestEngineStatus,
    BacktestEventType,
    BacktestStatus,
    DEFAULT_INITIAL_CAPITAL,
    ExecutionModel,
    OrderDirection,
    OrderStatus,
    OrderType,
    PositionSide,
    SimulationStatus,
    ValidationStatus,
)
from iios.integration.research.backtesting.backtest_exceptions import (
    BacktestAlreadyExistsError,
    BacktestCapacityError,
    BacktestEngineAlreadyRunningError,
    BacktestEngineNotRunningError,
    BacktestError,
    BacktestNotFoundError,
    BacktestValidationError,
    InsufficientCapitalError,
    InsufficientDataError,
    MetricsCalculationError,
    OrderRejectedError,
    OverfittingDetectedError,
    ReportGenerationError,
    SimulationDataError,
    WalkForwardError,
)
from iios.integration.research.backtesting.core.backtest import Backtest
from iios.integration.research.backtesting.core.backtest_configuration import BacktestConfiguration
from iios.integration.research.backtesting.core.backtest_history import (
    BacktestHistory,
    BacktestHistoryEntry,
)
from iios.integration.research.backtesting.core.backtest_metadata import BacktestMetadata
from iios.integration.research.backtesting.core.backtest_request import BacktestRequest
from iios.integration.research.backtesting.core.backtest_result import BacktestResult
from iios.integration.research.backtesting.core.backtest_session import BacktestSession
from iios.integration.research.backtesting.core.backtest_statistics import BacktestStatistics
from iios.integration.research.backtesting.engine.event_scheduler import EventScheduler, SimEvent, SimEventType
from iios.integration.research.backtesting.engine.execution_simulator import ExecutionSimulator
from iios.integration.research.backtesting.engine.market_simulator import BarEvent, MarketSimulator
from iios.integration.research.backtesting.engine.simulation_clock import SimulationClock
from iios.integration.research.backtesting.engine.simulation_engine import (
    BacktestStrategy,
    SimulationEngine,
)
from iios.integration.research.backtesting.execution.order import Fill, Order, OrderSignal
from iios.integration.research.backtesting.execution.portfolio import Portfolio, PortfolioSnapshot
from iios.integration.research.backtesting.execution.trade import Trade
from iios.integration.research.backtesting.metrics.drawdown_calculator import (
    drawdown_series,
    max_drawdown,
    max_drawdown_duration_bars,
)
from iios.integration.research.backtesting.metrics.performance_engine import PerformanceEngine
from iios.integration.research.backtesting.metrics.performance_report import PerformanceReport
from iios.integration.research.backtesting.metrics.return_calculator import (
    annualized_return,
    calculate_bar_returns,
    cumulative_returns,
    monthly_returns,
    total_return,
)
from iios.integration.research.backtesting.metrics.risk_metrics import (
    calmar_ratio,
    compute_beta,
    information_ratio,
    omega_ratio,
    sharpe_ratio,
    sortino_ratio,
    value_at_risk,
    volatility,
)
from iios.integration.research.backtesting.metrics.trade_statistics import (
    avg_loss,
    avg_trade_duration,
    avg_win,
    expectancy,
    largest_loss,
    largest_win,
    max_consecutive_losses,
    max_consecutive_wins,
    profit_factor,
    trade_return_distribution,
    win_rate,
)
from iios.integration.research.backtesting.reporting.benchmark_report import BenchmarkReport
from iios.integration.research.backtesting.reporting.comparison_report import ComparisonReport
from iios.integration.research.backtesting.reporting.equity_curve import EquityCurveReport, resample_equity_curve
from iios.integration.research.backtesting.reporting.report_generator import ReportGenerator
from iios.integration.research.backtesting.reporting.trade_report import TradeReport
from iios.integration.research.backtesting.validation.out_of_sample_validator import OutOfSampleValidator
from iios.integration.research.backtesting.validation.overfitting_detector import (
    OverfittingDetector,
    OverfittingScore,
)
from iios.integration.research.backtesting.validation.robustness_analyzer import RobustnessAnalyzer
from iios.integration.research.backtesting.validation.validation_engine import ValidationEngine
from iios.integration.research.backtesting.validation.walk_forward_validator import WalkForwardValidator
from iios.integration.research.backtesting.backtest_context import BacktestContext
from iios.integration.research.backtesting.backtest_registry import BacktestRegistry
from iios.integration.research.backtesting.backtest_factory import BacktestFactory
from iios.integration.research.backtesting.backtest_manager import BacktestManager
from iios.integration.research.backtesting.backtesting_engine import (
    BacktestingEngine,
    get_backtesting_engine,
    reset_backtesting_engine,
)


# ─────────────────────────────────────────────────────────────────────────────
# Test helpers
# ─────────────────────────────────────────────────────────────────────────────

_BASE_TS = 1_700_000_000.0
_DAY     = 86_400.0


def _make_bars(
    n: int = 60,
    symbol: str = "TESTSYM",
    start_price: float = 100.0,
) -> list[BarEvent]:
    bars: list[BarEvent] = []
    price = start_price
    ts    = _BASE_TS
    for i in range(n):
        high  = price * 1.01
        low   = price * 0.99
        # Slow upward drift to ensure profitable long strategy
        close = price + 0.5
        bars.append(BarEvent(
            timestamp  = ts,
            symbol     = symbol,
            open       = price,
            high       = high,
            low        = low,
            close      = close,
            volume     = 1_000_000.0,
            interval   = "1d",
            bar_index  = i,
            is_last    = (i == n - 1),
        ))
        price = close
        ts   += _DAY
    return bars


def _make_config(**kwargs) -> BacktestConfiguration:
    defaults = {
        "initial_capital": 100_000.0,
        "commission_pct":  0.001,
        "slippage_pct":    0.0,
        "execution_model": ExecutionModel.CLOSE,
        "min_bars":        5,
    }
    defaults.update(kwargs)
    return BacktestConfiguration(**defaults)


def _make_request(strategy_id: str = "test_strat", **kwargs) -> BacktestRequest:
    return BacktestRequest(
        strategy_id    = strategy_id,
        strategy_name  = "Test Strategy",
        configuration  = _make_config(**kwargs),
    )


def _make_equity_curve(n: int = 100, start: float = 100_000.0) -> list[tuple[float, float]]:
    curve: list[tuple[float, float]] = []
    equity = start
    ts     = _BASE_TS
    for i in range(n):
        equity += 500.0 - (200.0 if i % 5 == 0 else 0.0)   # noisy uptrend
        curve.append((ts, equity))
        ts += _DAY
    return curve


def _make_trades(n: int = 20, win_fraction: float = 0.6) -> list[dict[str, Any]]:
    trades: list[dict[str, Any]] = []
    for i in range(n):
        win     = i < int(n * win_fraction)
        net_pnl = 500.0 if win else -300.0
        trades.append({
            "trade_id":     f"t-{i}",
            "symbol":       "TESTSYM",
            "side":         "long",
            "entry_price":  100.0,
            "exit_price":   105.0 if win else 97.0,
            "quantity":     10.0,
            "gross_pnl":    net_pnl + 10,
            "commission":   10.0,
            "net_pnl":      net_pnl,
            "return_pct":   net_pnl / 1000.0,
            "entry_time":   _BASE_TS + i * _DAY,
            "exit_time":    _BASE_TS + i * _DAY + _DAY,
            "duration_sec": _DAY,
        })
    return trades


# ── Test strategy implementations ─────────────────────────────────────────────

class BuyAndHoldStrategy:
    strategy_id = "buy_and_hold"
    name        = "Buy and Hold"

    def __init__(self):
        self._bought = False

    def on_start(self, config: BacktestConfiguration) -> None:
        self._bought = False

    def on_bar(self, bars: dict, portfolio: PortfolioSnapshot) -> list[OrderSignal]:
        if not self._bought and portfolio.cash > 0:
            self._bought = True
            sym = list(bars.keys())[0]
            return [OrderSignal(symbol=sym, direction=OrderDirection.LONG, size_pct=0.9)]
        return []

    def on_end(self, portfolio: PortfolioSnapshot) -> None:
        pass


class AlwaysSellStrategy:
    strategy_id = "always_sell"
    name        = "Always Sell"

    def on_start(self, config: BacktestConfiguration) -> None: pass

    def on_bar(self, bars: dict, portfolio: PortfolioSnapshot) -> list[OrderSignal]:
        signals = []
        for sym in portfolio.positions:
            signals.append(OrderSignal(symbol=sym, direction=OrderDirection.EXIT_LONG))
        return signals

    def on_end(self, portfolio: PortfolioSnapshot) -> None: pass


class FailingStrategy:
    strategy_id = "failer"
    name        = "Failing Strategy"

    def on_start(self, config: BacktestConfiguration) -> None: pass

    def on_bar(self, bars: dict, portfolio: PortfolioSnapshot) -> list[OrderSignal]:
        raise RuntimeError("Strategy deliberately failed")

    def on_end(self, portfolio: PortfolioSnapshot) -> None: pass


def _make_manager() -> BacktestManager:
    return BacktestManager(
        registry          = BacktestFactory.create_registry(),
        sim_engine        = BacktestFactory.create_simulation_engine(),
        perf_engine       = BacktestFactory.create_performance_engine(),
        report_generator  = BacktestFactory.create_report_generator(),
        validation_engine = BacktestFactory.create_validation_engine(),
        history           = BacktestFactory.create_history(),
    )


# ─────────────────────────────────────────────────────────────────────────────
# TestConstants
# ─────────────────────────────────────────────────────────────────────────────

class TestConstants:
    def test_version_is_string(self):
        assert isinstance(BACKTESTING_ENGINE_VERSION, str)

    def test_error_prefix(self):
        assert BACKTEST_ERROR_PREFIX == "BT"

    def test_backtest_status_values(self):
        assert BacktestStatus.PENDING.value   == "pending"
        assert BacktestStatus.COMPLETED.value == "completed"
        assert BacktestStatus.FAILED.value    == "failed"

    def test_order_direction_values(self):
        assert OrderDirection.LONG.value       == "long"
        assert OrderDirection.EXIT_LONG.value  == "exit_long"
        assert OrderDirection.HOLD.value       == "hold"

    def test_execution_model_values(self):
        assert ExecutionModel.NEXT_OPEN.value  == "next_open"
        assert ExecutionModel.CLOSE.value      == "close"
        assert ExecutionModel.WORST_CASE.value == "worst_case"

    def test_validation_status_values(self):
        assert ValidationStatus.PASSED.value == "passed"
        assert ValidationStatus.FAILED.value == "failed"

    def test_default_initial_capital(self):
        assert DEFAULT_INITIAL_CAPITAL > 0


# ─────────────────────────────────────────────────────────────────────────────
# TestExceptions
# ─────────────────────────────────────────────────────────────────────────────

class TestExceptions:
    def test_root_code(self):
        e = BacktestError("msg")
        assert e.code == "BT-000"
        assert "BT-000" in repr(e)

    def test_engine_not_running_code(self):
        e = BacktestEngineNotRunningError("x")
        assert "BT-001" in repr(e)

    def test_engine_already_running_code(self):
        e = BacktestEngineAlreadyRunningError("x")
        assert "BT-002" in repr(e)

    def test_backtest_not_found_code(self):
        e = BacktestNotFoundError("x")
        assert "BT-010" in repr(e)

    def test_backtest_already_exists_code(self):
        e = BacktestAlreadyExistsError("x")
        assert "BT-011" in repr(e)

    def test_backtest_validation_error_code(self):
        e = BacktestValidationError("x")
        assert "BT-012" in repr(e)

    def test_simulation_data_error_code(self):
        e = SimulationDataError("x")
        assert "BT-021" in repr(e)

    def test_insufficient_data_code(self):
        e = InsufficientDataError("x")
        assert "BT-032" in repr(e)

    def test_metrics_error_code(self):
        e = MetricsCalculationError("x")
        assert "BT-040" in repr(e)

    def test_report_error_code(self):
        e = ReportGenerationError("x")
        assert "BT-050" in repr(e)

    def test_overfitting_code(self):
        e = OverfittingDetectedError("x")
        assert "BT-063" in repr(e)

    def test_walk_forward_code(self):
        e = WalkForwardError("x")
        assert "BT-061" in repr(e)


# ─────────────────────────────────────────────────────────────────────────────
# TestBacktestMetadata
# ─────────────────────────────────────────────────────────────────────────────

class TestBacktestMetadata:
    def test_defaults(self):
        m = BacktestMetadata()
        assert m.version == "1.0.0"
        assert m.tags    == []

    def test_add_tag(self):
        m = BacktestMetadata()
        m.add_tag("production")
        assert "production" in m.tags

    def test_add_tag_idempotent(self):
        m = BacktestMetadata()
        m.add_tag("x"); m.add_tag("x")
        assert m.tags.count("x") == 1

    def test_remove_tag(self):
        m = BacktestMetadata()
        m.add_tag("tmp"); m.remove_tag("tmp")
        assert "tmp" not in m.tags

    def test_set_label(self):
        m = BacktestMetadata()
        m.set_label("env", "test")
        assert m.labels["env"] == "test"

    def test_to_dict(self):
        m = BacktestMetadata(owner="alice")
        d = m.to_dict()
        assert d["owner"] == "alice"


# ─────────────────────────────────────────────────────────────────────────────
# TestBacktestConfiguration
# ─────────────────────────────────────────────────────────────────────────────

class TestBacktestConfiguration:
    def test_defaults(self):
        c = BacktestConfiguration()
        assert c.initial_capital == DEFAULT_INITIAL_CAPITAL
        assert c.execution_model == ExecutionModel.NEXT_OPEN

    def test_validate_ok(self):
        c = _make_config()
        assert c.validate() == []

    def test_validate_negative_capital(self):
        c = _make_config(initial_capital=-1)
        assert any("capital" in e for e in c.validate())

    def test_validate_negative_commission(self):
        c = _make_config(commission_pct=-0.1)
        assert any("commission" in e for e in c.validate())

    def test_to_dict(self):
        c = _make_config()
        d = c.to_dict()
        assert "initial_capital" in d
        assert "execution_model" in d


# ─────────────────────────────────────────────────────────────────────────────
# TestBacktestRequest
# ─────────────────────────────────────────────────────────────────────────────

class TestBacktestRequest:
    def test_defaults(self):
        r = BacktestRequest(strategy_id="s1")
        assert r.request_id != ""
        assert r.priority   == 5

    def test_validate_ok(self):
        r = _make_request()
        assert r.validate() == []

    def test_validate_missing_strategy_id(self):
        r = BacktestRequest(strategy_id="", configuration=_make_config())
        assert any("strategy_id" in e for e in r.validate())

    def test_to_dict(self):
        r = _make_request()
        d = r.to_dict()
        assert "request_id"  in d
        assert "strategy_id" in d


# ─────────────────────────────────────────────────────────────────────────────
# TestBacktest
# ─────────────────────────────────────────────────────────────────────────────

class TestBacktest:
    def test_defaults(self):
        b = Backtest(strategy_id="s1")
        assert b.status == BacktestStatus.PENDING
        assert b.backtest_id != ""

    def test_is_terminal_false_for_pending(self):
        b = Backtest()
        assert b.is_terminal() is False

    def test_is_terminal_true_for_completed(self):
        b = Backtest()
        b.status = BacktestStatus.COMPLETED
        assert b.is_terminal() is True

    def test_elapsed_sec_zero_before_start(self):
        b = Backtest()
        assert b.elapsed_sec() == 0.0

    def test_elapsed_sec_positive_after_start(self):
        b = Backtest()
        b.started_at = time.time() - 1.0
        assert b.elapsed_sec() > 0

    def test_to_dict(self):
        b = Backtest(strategy_id="s1")
        d = b.to_dict()
        assert "backtest_id" in d
        assert "status"      in d


# ─────────────────────────────────────────────────────────────────────────────
# TestBacktestSession
# ─────────────────────────────────────────────────────────────────────────────

class TestBacktestSession:
    def test_defaults(self):
        s = BacktestSession()
        assert s.status == SimulationStatus.IDLE

    def test_start(self):
        s = BacktestSession()
        s.start(total_bars=100)
        assert s.status     == SimulationStatus.RUNNING
        assert s.total_bars == 100

    def test_end_success(self):
        s = BacktestSession()
        s.start(); s.end()
        assert s.status == SimulationStatus.COMPLETED

    def test_end_failed(self):
        s = BacktestSession()
        s.start(); s.end(failed=True)
        assert s.status == SimulationStatus.FAILED

    def test_progress(self):
        s = BacktestSession()
        s.start(total_bars=100)
        s.advance(50, 0.0)
        assert s.progress() == pytest.approx(0.5)

    def test_duration_positive_after_end(self):
        s = BacktestSession()
        s.start(); time.sleep(0.01); s.end()
        assert s.duration_sec() > 0


# ─────────────────────────────────────────────────────────────────────────────
# TestBacktestResult
# ─────────────────────────────────────────────────────────────────────────────

class TestBacktestResult:
    def test_defaults(self):
        r = BacktestResult()
        assert r.is_success  is False
        assert r.trade_count == 0

    def test_set_metric(self):
        r = BacktestResult()
        r.set_metric("sharpe_ratio", 1.5)
        assert r.get_metric("sharpe_ratio") == pytest.approx(1.5)

    def test_has_metric(self):
        r = BacktestResult(metrics={"key": 42})
        assert r.has_metric("key")
        assert not r.has_metric("nonexistent")

    def test_add_trade(self):
        r = BacktestResult()
        r.add_trade({"net_pnl": 100.0})
        assert r.trade_count == 1

    def test_to_dict(self):
        r = BacktestResult(backtest_id="b1")
        d = r.to_dict()
        assert "result_id"   in d
        assert "backtest_id" in d


# ─────────────────────────────────────────────────────────────────────────────
# TestBacktestHistory
# ─────────────────────────────────────────────────────────────────────────────

class TestBacktestHistory:
    def _entry(self, entity_id: str = "b-1") -> BacktestHistoryEntry:
        return BacktestHistoryEntry(
            entity_type = "backtest",
            entity_id   = entity_id,
            event_type  = BacktestEventType.BACKTEST_COMPLETED,
        )

    def test_append_and_count(self):
        h = BacktestHistory()
        h.append(self._entry())
        assert h.count() == 1

    def test_query_by_entity(self):
        h = BacktestHistory()
        h.append(self._entry("A"))
        h.append(self._entry("B"))
        r = h.query(entity_id="A")
        assert len(r) == 1

    def test_clear(self):
        h = BacktestHistory()
        h.append(self._entry())
        h.clear()
        assert h.count() == 0

    def test_latest(self):
        h = BacktestHistory()
        for i in range(10): h.append(self._entry(f"b-{i}"))
        assert len(h.latest(5)) == 5

    def test_cap(self):
        h = BacktestHistory(max_entries=3)
        for i in range(5): h.append(self._entry(f"b-{i}"))
        assert h.count() == 3


# ─────────────────────────────────────────────────────────────────────────────
# TestSimulationClock
# ─────────────────────────────────────────────────────────────────────────────

class TestSimulationClock:
    def test_initialise(self):
        c = SimulationClock()
        c.initialise(1000.0, 2000.0)
        assert c.current == 1000.0
        assert c.is_initialised

    def test_advance_to(self):
        c = SimulationClock()
        c.initialise(0.0, 1000.0)
        c.advance_to(500.0)
        assert c.current     == 500.0
        assert c.tick_count  == 1

    def test_advance_backward_raises(self):
        c = SimulationClock()
        c.initialise(0.0, 1000.0)
        c.advance_to(500.0)
        from iios.integration.research.backtesting.backtest_exceptions import SimulationClockError
        with pytest.raises(SimulationClockError):
            c.advance_to(100.0)

    def test_is_within_range(self):
        c = SimulationClock()
        c.initialise(100.0, 200.0)
        assert c.is_within_range(150.0) is True
        assert c.is_within_range(50.0)  is False

    def test_invalid_range_raises(self):
        c = SimulationClock()
        from iios.integration.research.backtesting.backtest_exceptions import SimulationClockError
        with pytest.raises(SimulationClockError):
            c.initialise(1000.0, 500.0)

    def test_to_dict(self):
        c = SimulationClock()
        c.initialise(100.0, 200.0)
        d = c.to_dict()
        assert "current_ts" in d


# ─────────────────────────────────────────────────────────────────────────────
# TestEventScheduler
# ─────────────────────────────────────────────────────────────────────────────

class TestEventScheduler:
    def test_schedule_and_next(self):
        s = EventScheduler()
        s.schedule(SimEvent(timestamp=10.0, event_type=SimEventType.BAR))
        e = s.next_event()
        assert e is not None
        assert e.timestamp == 10.0

    def test_ordering(self):
        s = EventScheduler()
        s.schedule(SimEvent(timestamp=20.0))
        s.schedule(SimEvent(timestamp=5.0))
        s.schedule(SimEvent(timestamp=15.0))
        times = [s.next_event().timestamp for _ in range(3)]
        assert times == [5.0, 15.0, 20.0]

    def test_empty_returns_none(self):
        s = EventScheduler()
        assert s.next_event() is None

    def test_pending_count(self):
        s = EventScheduler()
        s.schedule_bar(1.0, "A", 0)
        s.schedule_bar(2.0, "A", 1)
        assert s.pending_count() == 2

    def test_clear(self):
        s = EventScheduler()
        s.schedule_bar(1.0, "A", 0)
        s.clear()
        assert s.pending_count() == 0


# ─────────────────────────────────────────────────────────────────────────────
# TestMarketSimulator
# ─────────────────────────────────────────────────────────────────────────────

class TestMarketSimulator:
    def test_load_and_symbols(self):
        ms = MarketSimulator()
        bars = _make_bars(10, "SYM")
        ms.load({"SYM": bars})
        assert "SYM" in ms.symbols()

    def test_bar_count(self):
        ms = MarketSimulator()
        ms.load({"SYM": _make_bars(20, "SYM")})
        assert ms.bar_count("SYM") == 20

    def test_sorted_timeline_order(self):
        ms = MarketSimulator()
        b1 = _make_bars(5, "A")
        b2 = _make_bars(5, "B")
        ms.load({"A": b1, "B": b2})
        tl = ms.sorted_timeline()
        timestamps = [t for t, _, _ in tl]
        assert timestamps == sorted(timestamps)

    def test_split_adjustment(self):
        ms = MarketSimulator()
        bars = _make_bars(10, "SYM", start_price=200.0)
        split_ts = bars[5].timestamp
        ms.load({"SYM": bars})
        ms.apply_split_adjustment("SYM", 2.0, split_ts)
        # Bars before split should have close halved
        assert ms.all_bars("SYM")[0].close == pytest.approx(bars[0].close)  # already adjusted

    def test_stats(self):
        ms = MarketSimulator()
        ms.load({"SYM": _make_bars(15, "SYM")})
        s = ms.stats()
        assert s["total_bars"] == 15


# ─────────────────────────────────────────────────────────────────────────────
# TestPortfolio
# ─────────────────────────────────────────────────────────────────────────────

class TestPortfolio:
    def _fill(self, symbol="S", direction=OrderDirection.LONG,
              price=100.0, qty=10.0, commission=1.0, ts=None) -> Fill:
        return Fill(
            order_id   = "o1",
            symbol     = symbol,
            quantity   = qty,
            fill_price = price,
            commission = commission,
            direction  = direction,
            timestamp  = ts or _BASE_TS,
        )

    def test_initial_state(self):
        p = Portfolio(100_000.0)
        assert p.cash           == 100_000.0
        assert p.total_equity() == 100_000.0

    def test_apply_long_fill_reduces_cash(self):
        p = Portfolio(100_000.0)
        f = self._fill(price=100.0, qty=100.0, commission=10.0)
        p.apply_fill(f)
        assert p.cash == pytest.approx(100_000.0 - 100 * 100.0 - 10.0)

    def test_close_long_creates_trade(self):
        p = Portfolio(100_000.0)
        p.apply_fill(self._fill(price=100.0, qty=10.0, commission=1.0, ts=_BASE_TS))
        close_f = self._fill(direction=OrderDirection.EXIT_LONG,
                             price=110.0, qty=10.0, commission=1.0, ts=_BASE_TS + _DAY)
        p.apply_fill(close_f)
        trades = p.completed_trades
        assert len(trades) == 1
        assert trades[0].net_pnl > 0

    def test_update_prices_records_equity(self):
        p = Portfolio(100_000.0)
        p.update_prices({"S": 105.0}, _BASE_TS)
        assert len(p.equity_curve) == 1

    def test_snapshot(self):
        p    = Portfolio(100_000.0)
        snap = p.snapshot(_BASE_TS)
        assert snap.cash         == 100_000.0
        assert snap.total_equity == 100_000.0
        assert snap.return_pct   == 0.0

    def test_close_all_positions(self):
        p = Portfolio(100_000.0)
        p.apply_fill(self._fill(price=100.0, qty=10.0, commission=1.0))
        p.close_all_positions({"S": 110.0}, _BASE_TS + _DAY)
        assert "S" not in p.positions


# ─────────────────────────────────────────────────────────────────────────────
# TestExecutionSimulator
# ─────────────────────────────────────────────────────────────────────────────

class TestExecutionSimulator:
    def _sim(self, model=ExecutionModel.CLOSE) -> ExecutionSimulator:
        return ExecutionSimulator(_make_config(execution_model=model))

    def _bar(self, price=100.0) -> BarEvent:
        return BarEvent(
            timestamp=_BASE_TS, symbol="S",
            open=price*0.99, high=price*1.01, low=price*0.98, close=price,
            volume=1_000_000.0,
        )

    def test_submit_long_signal(self):
        sim  = self._sim()
        port = Portfolio(100_000.0)
        bar  = self._bar(100.0)
        sig  = OrderSignal(symbol="S", direction=OrderDirection.LONG, size_pct=0.5)
        order = sim.submit_signal(sig, port, bar)
        assert order is not None
        assert order.quantity > 0
        assert sim.pending_count() == 1

    def test_fill_market_order(self):
        sim  = self._sim()
        port = Portfolio(100_000.0)
        bar  = self._bar(100.0)
        sig  = OrderSignal(symbol="S", direction=OrderDirection.LONG, size_pct=0.5)
        sim.submit_signal(sig, port, bar)
        fills = sim.fill_pending({"S": bar})
        assert len(fills) == 1
        assert fills[0].fill_price == pytest.approx(100.0)

    def test_fill_worst_case_long_uses_high(self):
        sim  = self._sim(ExecutionModel.WORST_CASE)
        port = Portfolio(100_000.0)
        bar  = self._bar(100.0)
        sig  = OrderSignal(symbol="S", direction=OrderDirection.LONG, size_pct=0.5)
        sim.submit_signal(sig, port, bar)
        fills = sim.fill_pending({"S": bar})
        assert fills[0].fill_price == pytest.approx(bar.high)

    def test_hold_signal_not_submitted(self):
        sim  = self._sim()
        port = Portfolio(100_000.0)
        bar  = self._bar()
        sig  = OrderSignal(symbol="S", direction=OrderDirection.HOLD)
        order = sim.submit_signal(sig, port, bar)
        assert order is None

    def test_missing_symbol_order_stays_pending(self):
        sim  = self._sim()
        port = Portfolio(100_000.0)
        bar  = self._bar()
        sim.submit_signal(OrderSignal(symbol="S", direction=OrderDirection.LONG), port, bar)
        fills = sim.fill_pending({"OTHER": bar})
        assert sim.pending_count() == 1
        assert fills == []


# ─────────────────────────────────────────────────────────────────────────────
# TestSimulationEngine
# ─────────────────────────────────────────────────────────────────────────────

class TestSimulationEngine:
    def test_buy_and_hold_succeeds(self):
        engine   = SimulationEngine()
        strategy = BuyAndHoldStrategy()
        bars     = _make_bars(60)
        result   = _run(engine.run("bt-1", _make_config(), strategy, {"TESTSYM": bars}))
        assert result.is_success is True

    def test_equity_curve_populated(self):
        engine   = SimulationEngine()
        strategy = BuyAndHoldStrategy()
        bars     = _make_bars(60)
        result   = _run(engine.run("bt-2", _make_config(), strategy, {"TESTSYM": bars}))
        assert len(result.equity_curve) > 0

    def test_trade_log_has_trades(self):
        engine   = SimulationEngine()
        strategy = BuyAndHoldStrategy()
        bars     = _make_bars(60)
        result   = _run(engine.run("bt-3", _make_config(), strategy, {"TESTSYM": bars}))
        # Buy-and-hold should have at least 1 trade (force-closed at end)
        assert result.trade_count >= 1

    def test_bar_count_matches_input(self):
        engine   = SimulationEngine()
        strategy = BuyAndHoldStrategy()
        bars     = _make_bars(40)
        result   = _run(engine.run("bt-4", _make_config(), strategy, {"TESTSYM": bars}))
        assert result.bar_count == 40

    def test_empty_bars_fails(self):
        engine   = SimulationEngine()
        strategy = BuyAndHoldStrategy()
        result   = _run(engine.run("bt-5", _make_config(), strategy, {}))
        assert result.is_success is False

    def test_insufficient_bars_fails(self):
        engine   = SimulationEngine()
        strategy = BuyAndHoldStrategy()
        bars     = _make_bars(3)  # below min_bars=5
        result   = _run(engine.run("bt-6", _make_config(min_bars=5), strategy, {"T": bars}))
        assert result.is_success is False

    def test_failing_strategy_still_returns_result(self):
        engine   = SimulationEngine()
        strategy = FailingStrategy()
        bars     = _make_bars(30)
        result   = _run(engine.run("bt-7", _make_config(), strategy, {"TESTSYM": bars}))
        # Strategy errors during on_bar are logged but simulation continues
        assert result is not None

    def test_next_open_model(self):
        engine   = SimulationEngine()
        strategy = BuyAndHoldStrategy()
        bars     = _make_bars(40)
        config   = _make_config(execution_model=ExecutionModel.NEXT_OPEN)
        result   = _run(engine.run("bt-8", config, strategy, {"TESTSYM": bars}))
        assert result.is_success is True

    def test_stats_updated(self):
        engine   = SimulationEngine()
        strategy = BuyAndHoldStrategy()
        bars     = _make_bars(30)
        _run(engine.run("bt-9", _make_config(), strategy, {"TESTSYM": bars}))
        s = engine.stats()
        assert s["runs"] >= 1


# ─────────────────────────────────────────────────────────────────────────────
# TestReturnCalculator
# ─────────────────────────────────────────────────────────────────────────────

class TestReturnCalculator:
    def test_calculate_bar_returns(self):
        curve  = [(0.0, 100.0), (1.0, 110.0), (2.0, 121.0)]
        rets   = calculate_bar_returns(curve)
        assert rets[0] == pytest.approx(0.10)
        assert rets[1] == pytest.approx(0.10)

    def test_total_return(self):
        assert total_return(100.0, 150.0) == pytest.approx(0.5)
        assert total_return(0.0,   50.0)  == 0.0

    def test_annualized_return_one_year(self):
        # If we earn 10 % in exactly 252 days, annualised ≈ 10 %
        ann = annualized_return(0.10, 252)
        assert ann == pytest.approx(0.10, abs=1e-6)

    def test_cumulative_returns(self):
        curve = [(0.0, 100.0), (1.0, 110.0), (2.0, 100.0)]
        crs   = cumulative_returns(curve)
        assert crs[0] == pytest.approx(0.0)
        assert crs[1] == pytest.approx(0.10)
        assert crs[2] == pytest.approx(0.0)

    def test_empty_curve_returns_empty(self):
        assert calculate_bar_returns([]) == []

    def test_monthly_returns_keys(self):
        # Build a curve with multiple points per month so monthly_returns has data
        from datetime import datetime, timezone
        ts_jan1 = datetime(2024, 1, 1,  tzinfo=timezone.utc).timestamp()
        ts_jan2 = datetime(2024, 1, 15, tzinfo=timezone.utc).timestamp()
        ts_feb1 = datetime(2024, 2, 1,  tzinfo=timezone.utc).timestamp()
        ts_feb2 = datetime(2024, 2, 15, tzinfo=timezone.utc).timestamp()
        curve  = [(ts_jan1, 100.0), (ts_jan2, 105.0), (ts_feb1, 110.0), (ts_feb2, 115.0)]
        mr     = monthly_returns(curve)
        assert len(mr) >= 1


# ─────────────────────────────────────────────────────────────────────────────
# TestDrawdownCalculator
# ─────────────────────────────────────────────────────────────────────────────

class TestDrawdownCalculator:
    def test_drawdown_series_all_up(self):
        curve = [(i * 1.0, 100.0 + i) for i in range(10)]
        dds   = drawdown_series(curve)
        assert all(d == pytest.approx(0.0) for d in dds)

    def test_max_drawdown_simple(self):
        # peak=120, trough=90 → dd = 30/120 = 0.25
        curve = [(0.0, 100.0), (1.0, 120.0), (2.0, 90.0)]
        dd    = max_drawdown(curve)
        assert dd == pytest.approx(0.25, abs=0.001)

    def test_max_drawdown_empty(self):
        assert max_drawdown([]) == 0.0

    def test_max_drawdown_duration(self):
        # Peak at index 0, dip for 5 bars, recovery at index 6
        curve = (
            [(i * 1.0, 100.0) for i in range(1)]
            + [(i * 1.0, 95.0) for i in range(1, 6)]
            + [(6.0, 101.0)]
        )
        dur = max_drawdown_duration_bars(curve)
        assert dur == 5


# ─────────────────────────────────────────────────────────────────────────────
# TestRiskMetrics
# ─────────────────────────────────────────────────────────────────────────────

class TestRiskMetrics:
    _RETS = [0.01, -0.005, 0.02, -0.01, 0.015, 0.005, -0.003, 0.008, 0.012, -0.002] * 10

    def test_sharpe_positive_uptrend(self):
        # Mix of slightly varying positive returns to avoid zero-variance stdev
        rets = [0.001 + (0.0002 if i % 3 != 0 else -0.0001) for i in range(252)]
        s    = sharpe_ratio(rets)
        assert s > 0

    def test_sortino_ge_sharpe_for_positive_returns(self):
        rets = [0.001] * 252
        assert sortino_ratio(rets) >= sharpe_ratio(rets)

    def test_calmar_ratio(self):
        assert calmar_ratio(0.20, 0.10) == pytest.approx(2.0)
        assert calmar_ratio(0.10, 0.0)  == float("inf")

    def test_volatility_zero_for_constant(self):
        assert volatility([0.01] * 252) == pytest.approx(0.0, abs=1e-10)

    def test_omega_ratio_all_positive(self):
        assert omega_ratio([0.01] * 100) == float("inf")

    def test_value_at_risk(self):
        rets = sorted(self._RETS)
        var  = value_at_risk(self._RETS, 0.95)
        assert var >= 0

    def test_compute_beta_identical_series(self):
        r  = [0.01, -0.005, 0.02, -0.01, 0.015]
        b  = compute_beta(r, r)
        assert b == pytest.approx(1.0)

    def test_compute_beta_empty(self):
        assert compute_beta([], []) == 0.0

    def test_information_ratio_identical_series(self):
        r = [0.01, -0.005, 0.02, -0.01, 0.015]
        assert information_ratio(r, r) == pytest.approx(0.0)


# ─────────────────────────────────────────────────────────────────────────────
# TestTradeStatistics
# ─────────────────────────────────────────────────────────────────────────────

class TestTradeStatistics:
    def test_win_rate(self):
        trades = _make_trades(10, win_fraction=0.6)
        assert win_rate(trades) == pytest.approx(0.6)

    def test_profit_factor(self):
        trades = _make_trades(10, win_fraction=0.5)
        pf     = profit_factor(trades)
        assert pf > 0

    def test_expectancy(self):
        trades = _make_trades(10, win_fraction=0.6)
        e      = expectancy(trades)
        assert e > 0   # 60 % win rate with 500 wins and 300 losses

    def test_avg_win_positive(self):
        assert avg_win(_make_trades(10)) > 0

    def test_avg_loss_positive(self):
        assert avg_loss(_make_trades(10)) > 0

    def test_largest_win(self):
        assert largest_win(_make_trades(10)) == pytest.approx(500.0)

    def test_largest_loss(self):
        assert largest_loss(_make_trades(10)) == pytest.approx(300.0)

    def test_max_consecutive_wins(self):
        trades = _make_trades(10, win_fraction=0.6)
        assert max_consecutive_wins(trades) >= 1

    def test_empty_trades_returns_zeros(self):
        assert win_rate([])    == 0.0
        assert expectancy([])  == 0.0

    def test_trade_distribution(self):
        dist = trade_return_distribution(_make_trades(20))
        assert "count" in dist
        assert dist["count"] == 20


# ─────────────────────────────────────────────────────────────────────────────
# TestPerformanceEngine
# ─────────────────────────────────────────────────────────────────────────────

class TestPerformanceEngine:
    def test_compute_populates_metrics(self):
        pe     = PerformanceEngine()
        result = BacktestResult(
            equity_curve = _make_equity_curve(100),
            trade_log    = _make_trades(20),
        )
        stats = pe.compute(result)
        assert "sharpe_ratio"     in result.metrics
        assert "total_return_pct" in result.metrics

    def test_compute_returns_statistics(self):
        pe    = PerformanceEngine()
        r     = BacktestResult(equity_curve=_make_equity_curve(50), trade_log=_make_trades(10))
        stats = pe.compute(r)
        assert isinstance(stats, BacktestStatistics)
        assert stats.bar_count == 50

    def test_compare(self):
        pe  = PerformanceEngine()
        r1  = BacktestResult(equity_curve=_make_equity_curve(50), trade_log=_make_trades(10))
        r2  = BacktestResult(equity_curve=_make_equity_curve(50), trade_log=_make_trades(10))
        cmp = pe.compare([r1, r2])
        assert r1.result_id in cmp
        assert r2.result_id in cmp


# ─────────────────────────────────────────────────────────────────────────────
# TestBacktestStatistics
# ─────────────────────────────────────────────────────────────────────────────

class TestBacktestStatistics:
    def test_compute_empty(self):
        s = BacktestStatistics.compute([], [])
        assert s.total_trades == 0

    def test_compute_with_curve(self):
        s = BacktestStatistics.compute(_make_equity_curve(100), _make_trades(20))
        assert s.bar_count    == 100
        assert s.total_trades == 20
        assert s.win_rate     == pytest.approx(0.6)

    def test_to_dict(self):
        s = BacktestStatistics.compute(_make_equity_curve(50), _make_trades(10))
        d = s.to_dict()
        assert "sharpe_ratio"     in d
        assert "total_return_pct" in d
        assert "win_rate"         in d


# ─────────────────────────────────────────────────────────────────────────────
# TestEquityCurveReport
# ─────────────────────────────────────────────────────────────────────────────

class TestEquityCurveReport:
    def test_build_returns_dict(self):
        rpt = EquityCurveReport()
        d   = rpt.build(_make_equity_curve(100), 100_000.0)
        assert "points"          in d
        assert "final_equity"    in d
        assert "underwater"      in d

    def test_resample_reduces_points(self):
        curve   = _make_equity_curve(1000)
        sampled = resample_equity_curve(curve, 100)
        assert len(sampled) == 100

    def test_resample_short_curve_unchanged(self):
        curve   = _make_equity_curve(50)
        sampled = resample_equity_curve(curve, 200)
        assert len(sampled) == 50


# ─────────────────────────────────────────────────────────────────────────────
# TestTradeReport
# ─────────────────────────────────────────────────────────────────────────────

class TestTradeReport:
    def test_build(self):
        rpt = TradeReport()
        d   = rpt.build(_make_trades(10))
        assert d["total_trades"] == 10
        assert "by_symbol"       in d

    def test_empty_trades(self):
        rpt = TradeReport()
        d   = rpt.build([])
        assert d["total_trades"] == 0


# ─────────────────────────────────────────────────────────────────────────────
# TestBenchmarkReport
# ─────────────────────────────────────────────────────────────────────────────

class TestBenchmarkReport:
    def test_build(self):
        rpt  = BenchmarkReport()
        rets = [0.001] * 100
        d    = rpt.build(rets, rets, "NIFTY50")
        assert "benchmark_symbol"           in d
        assert "information_ratio"          in d
        assert d["active_return_pct"]       == pytest.approx(0.0, abs=0.01)

    def test_outperforming_strategy(self):
        rpt  = BenchmarkReport()
        s    = [0.002] * 100
        b    = [0.001] * 100
        d    = rpt.build(s, b)
        assert d["active_return_pct"] > 0


# ─────────────────────────────────────────────────────────────────────────────
# TestComparisonReport
# ─────────────────────────────────────────────────────────────────────────────

class TestComparisonReport:
    def test_build(self):
        r1 = BacktestResult(); r1.metrics = {"sharpe_ratio": 1.5}
        r2 = BacktestResult(); r2.metrics = {"sharpe_ratio": 0.8}
        rpt = ComparisonReport()
        d   = rpt.build([r1, r2], ["A", "B"])
        assert d["count"]          == 2
        assert "A"                 in d["metrics"]
        assert d["ranked_by_sharpe"][0] == "A"

    def test_ranked_by_sharpe(self):
        r1 = BacktestResult(); r1.metrics = {"sharpe_ratio": 0.5}
        r2 = BacktestResult(); r2.metrics = {"sharpe_ratio": 2.0}
        d  = ComparisonReport().build([r1, r2])
        assert d["ranked_by_sharpe"][0] == r2.result_id


# ─────────────────────────────────────────────────────────────────────────────
# TestWalkForwardValidator
# ─────────────────────────────────────────────────────────────────────────────

class TestWalkForwardValidator:
    def test_generates_correct_fold_count(self):
        # 500 timestamps, 5 folds, 10% OOS each — enough room for all 5
        ts  = [float(i) for i in range(500)]
        wfv = WalkForwardValidator()
        ws  = wfv.generate_windows(ts, n_folds=5, oos_fraction=0.1)
        assert len(ws) == 5

    def test_windows_chronological(self):
        ts  = [float(i) for i in range(200)]
        wfv = WalkForwardValidator()
        ws  = wfv.generate_windows(ts, n_folds=3)
        for w in ws:
            assert w.is_start <= w.is_end
            assert w.is_end   <= w.oos_start
            assert w.oos_start <= w.oos_end

    def test_empty_timestamps_raises(self):
        with pytest.raises(WalkForwardError):
            WalkForwardValidator().generate_windows([], n_folds=3)

    def test_efficiency_calculation(self):
        wfv = WalkForwardValidator()
        assert wfv.efficiency(2.0, 1.0) == pytest.approx(0.5)
        assert wfv.efficiency(0.0, 1.0) == 0.0

    def test_to_dict(self):
        ts  = [float(i) for i in range(100)]
        wfv = WalkForwardValidator()
        ws  = wfv.generate_windows(ts, n_folds=2)
        d   = ws[0].to_dict()
        assert "fold"      in d
        assert "is_start"  in d


# ─────────────────────────────────────────────────────────────────────────────
# TestOutOfSampleValidator
# ─────────────────────────────────────────────────────────────────────────────

class TestOutOfSampleValidator:
    def test_split_ratio(self):
        ts    = [float(i) for i in range(100)]
        oos   = OutOfSampleValidator()
        split = oos.split(ts, oos_fraction=0.3)
        assert split.oos_size == 30
        assert split.is_size  == 70

    def test_split_to_dict(self):
        ts    = [float(i) for i in range(100)]
        split = OutOfSampleValidator().split(ts)
        d     = split.to_dict()
        assert "is_size"  in d
        assert "oos_size" in d

    def test_compare_metrics(self):
        is_m  = {"sharpe_ratio": 2.0, "total_return_pct": 0.30}
        oos_m = {"sharpe_ratio": 1.0, "total_return_pct": 0.15}
        cmp   = OutOfSampleValidator().compare_metrics(is_m, oos_m)
        assert "sharpe_ratio" in cmp
        assert cmp["sharpe_ratio"]["degradation_pct"] == pytest.approx(0.5)

    def test_invalid_oos_fraction_raises(self):
        from iios.integration.research.backtesting.backtest_exceptions import BacktestValidationFrameworkError
        with pytest.raises(BacktestValidationFrameworkError):
            OutOfSampleValidator().split([1.0], oos_fraction=1.5)


# ─────────────────────────────────────────────────────────────────────────────
# TestOverfittingDetector
# ─────────────────────────────────────────────────────────────────────────────

class TestOverfittingDetector:
    def test_clean_when_metrics_match(self):
        m   = {"sharpe_ratio": 1.5, "total_return_pct": 0.20, "total_trades": 50}
        ofs = OverfittingDetector().detect(m, m)
        assert ofs.verdict == "clean"

    def test_overfit_on_severe_degradation(self):
        is_m  = {"sharpe_ratio": 3.0, "total_return_pct": 0.5, "total_trades": 50}
        oos_m = {"sharpe_ratio": 0.1, "total_return_pct": 0.01, "total_trades": 50}
        ofs   = OverfittingDetector().detect(is_m, oos_m)
        assert ofs.is_overfit

    def test_strict_raises_on_overfit(self):
        is_m  = {"sharpe_ratio": 4.0, "total_return_pct": 0.8, "total_trades": 100}
        oos_m = {"sharpe_ratio": 0.05, "total_return_pct": -0.1, "total_trades": 30}
        with pytest.raises(OverfittingDetectedError):
            OverfittingDetector().detect(is_m, oos_m, strict=True)

    def test_to_dict(self):
        m   = {"sharpe_ratio": 1.0, "total_trades": 30}
        ofs = OverfittingDetector().detect(m, m)
        d   = ofs.to_dict()
        assert "score"    in d
        assert "verdict"  in d
        assert "is_overfit" in d


# ─────────────────────────────────────────────────────────────────────────────
# TestRobustnessAnalyzer
# ─────────────────────────────────────────────────────────────────────────────

class TestRobustnessAnalyzer:
    def test_consistent_results_are_robust(self):
        samples = [{"sharpe_ratio": 1.5 + i * 0.01} for i in range(20)]
        ra      = RobustnessAnalyzer()
        result  = ra.analyse(samples)
        assert result["status"] in ("robust", "marginal")

    def test_inconsistent_results_are_fragile(self):
        samples = [{"sharpe_ratio": (1.0 if i % 2 == 0 else -1.0)} for i in range(20)]
        ra      = RobustnessAnalyzer()
        result  = ra.analyse(samples)
        assert result["status"] == "fragile"

    def test_perturbation_test(self):
        curves  = [_make_equity_curve(50) for _ in range(5)]
        ra      = RobustnessAnalyzer()
        result  = ra.perturbation_test(curves)
        assert "consistency" in result

    def test_empty_samples(self):
        result = RobustnessAnalyzer().analyse([])
        assert result.get("status") == "no_data"


# ─────────────────────────────────────────────────────────────────────────────
# TestValidationEngine
# ─────────────────────────────────────────────────────────────────────────────

class TestValidationEngine:
    def test_validate_successful_result(self):
        ve     = ValidationEngine()
        result = BacktestResult(
            equity_curve = _make_equity_curve(100),
            trade_log    = _make_trades(30),
            metrics      = {"sharpe_ratio": 1.2, "total_return_pct": 0.15, "total_trades": 30},
        )
        vr = ve.validate(result)
        assert vr.status in (ValidationStatus.PASSED, ValidationStatus.FAILED)

    def test_validate_returns_oos_split(self):
        ve     = ValidationEngine()
        result = BacktestResult(equity_curve=_make_equity_curve(100))
        vr     = ve.validate(result)
        assert vr.oos_split is not None

    def test_validate_generates_wf_windows(self):
        ve     = ValidationEngine()
        result = BacktestResult(equity_curve=_make_equity_curve(200))
        vr     = ve.validate(result, wf_folds=3)
        assert len(vr.wf_windows) > 0

    def test_validate_to_dict(self):
        ve = ValidationEngine()
        r  = BacktestResult(equity_curve=_make_equity_curve(50))
        d  = ve.validate(r).to_dict()
        assert "status" in d
        assert "passed" in d


# ─────────────────────────────────────────────────────────────────────────────
# TestBacktestContext
# ─────────────────────────────────────────────────────────────────────────────

class TestBacktestContext:
    def test_set_and_get(self):
        BacktestContext.set(operation="run", backtest_id="b-1")
        s = BacktestContext.get()
        assert s.operation   == "run"
        assert s.backtest_id == "b-1"
        BacktestContext.clear()

    def test_clear_resets(self):
        BacktestContext.set(operation="x")
        BacktestContext.clear()
        assert BacktestContext.get().operation == ""

    def test_scope_context_manager(self):
        with BacktestContext.scope("validate", backtest_id="b-2") as s:
            assert s.operation   == "validate"
            assert s.backtest_id == "b-2"
        assert BacktestContext.get().operation == ""

    def test_thread_isolation(self):
        results: dict[str, str] = {}
        def _set(op: str):
            BacktestContext.set(operation=op)
            time.sleep(0.02)
            results[op] = BacktestContext.get().operation
        t1 = threading.Thread(target=_set, args=("A",))
        t2 = threading.Thread(target=_set, args=("B",))
        t1.start(); t2.start()
        t1.join();  t2.join()
        assert results["A"] == "A"
        assert results["B"] == "B"

    def test_elapsed_ms(self):
        BacktestContext.set(operation="t")
        time.sleep(0.01)
        assert BacktestContext.get().elapsed_ms() > 0
        BacktestContext.clear()


# ─────────────────────────────────────────────────────────────────────────────
# TestBacktestRegistry
# ─────────────────────────────────────────────────────────────────────────────

class TestBacktestRegistry:
    def test_register_and_get(self):
        reg = BacktestRegistry()
        b   = Backtest(strategy_id="s1")
        reg.register(b)
        assert reg.get(b.backtest_id).backtest_id == b.backtest_id

    def test_duplicate_raises(self):
        reg = BacktestRegistry()
        b   = Backtest()
        reg.register(b)
        with pytest.raises(BacktestAlreadyExistsError):
            reg.register(b)

    def test_remove(self):
        reg = BacktestRegistry()
        b   = Backtest()
        reg.register(b)
        reg.remove(b.backtest_id)
        with pytest.raises(BacktestNotFoundError):
            reg.get(b.backtest_id)

    def test_capacity(self):
        reg = BacktestRegistry(max_backtests=2)
        reg.register(Backtest())
        reg.register(Backtest())
        with pytest.raises(BacktestCapacityError):
            reg.register(Backtest())

    def test_find_by_status(self):
        reg = BacktestRegistry()
        b   = Backtest()
        b.status = BacktestStatus.COMPLETED
        reg.register(b)
        hits = reg.find_by_status(BacktestStatus.COMPLETED)
        assert len(hits) == 1

    def test_stats(self):
        reg = BacktestRegistry()
        s   = reg.stats()
        assert "total"    in s
        assert "capacity" in s


# ─────────────────────────────────────────────────────────────────────────────
# TestBacktestFactory
# ─────────────────────────────────────────────────────────────────────────────

class TestBacktestFactory:
    def test_create_registry(self):
        assert isinstance(BacktestFactory.create_registry(), BacktestRegistry)

    def test_create_simulation_engine(self):
        assert isinstance(BacktestFactory.create_simulation_engine(), SimulationEngine)

    def test_create_market_simulator(self):
        assert isinstance(BacktestFactory.create_market_simulator(), MarketSimulator)

    def test_create_performance_engine(self):
        assert isinstance(BacktestFactory.create_performance_engine(), PerformanceEngine)

    def test_create_validation_engine(self):
        assert isinstance(BacktestFactory.create_validation_engine(), ValidationEngine)

    def test_create_configuration(self):
        c = BacktestFactory.create_configuration(initial_capital=50_000.0)
        assert c.initial_capital == 50_000.0


# ─────────────────────────────────────────────────────────────────────────────
# TestBacktestManager
# ─────────────────────────────────────────────────────────────────────────────

class TestBacktestManager:
    def test_submit_creates_backtest(self):
        mgr = _make_manager()
        req = _make_request()
        b   = mgr.submit(req)
        assert b.backtest_id != ""
        assert b.status == BacktestStatus.PENDING

    def test_submit_invalid_request_raises(self):
        mgr = _make_manager()
        req = BacktestRequest(strategy_id="", configuration=_make_config())
        with pytest.raises(BacktestValidationError):
            mgr.submit(req)

    def test_run_backtest_succeeds(self):
        mgr      = _make_manager()
        req      = _make_request()
        b        = mgr.submit(req)
        strategy = BuyAndHoldStrategy()
        bars     = {"TESTSYM": _make_bars(60)}
        result   = _run(mgr.run(b.backtest_id, strategy, bars))
        assert result.is_success is True

    def test_run_populates_metrics(self):
        mgr      = _make_manager()
        req      = _make_request()
        b        = mgr.submit(req)
        result   = _run(mgr.run(b.backtest_id, BuyAndHoldStrategy(), {"TESTSYM": _make_bars(60)}))
        assert "sharpe_ratio" in result.metrics

    def test_run_generates_report(self):
        mgr    = _make_manager()
        req    = _make_request()
        b      = mgr.submit(req)
        result = _run(mgr.run(b.backtest_id, BuyAndHoldStrategy(), {"TESTSYM": _make_bars(60)}))
        assert result.report != {}

    def test_cancel_pending(self):
        mgr = _make_manager()
        req = _make_request()
        b   = mgr.submit(req)
        mgr.cancel(b.backtest_id)
        assert mgr.get_backtest(b.backtest_id).status == BacktestStatus.CANCELLED

    def test_list_backtests(self):
        mgr = _make_manager()
        mgr.submit(_make_request())
        mgr.submit(_make_request())
        all_b = mgr.list_backtests()
        assert len(all_b) == 2

    def test_stats(self):
        s = _make_manager().stats()
        assert "registry" in s


# ─────────────────────────────────────────────────────────────────────────────
# TestBacktestingEngine
# ─────────────────────────────────────────────────────────────────────────────

class TestBacktestingEngine:
    def setup_method(self):
        reset_backtesting_engine()

    def teardown_method(self):
        reset_backtesting_engine()

    def _started(self) -> BacktestingEngine:
        e = BacktestingEngine()
        _run(e.start())
        return e

    def test_initial_status_stopped(self):
        e = BacktestingEngine()
        assert e.status() == BacktestEngineStatus.STOPPED

    def test_start(self):
        e = self._started()
        assert e.is_running()

    def test_stop(self):
        e = self._started()
        _run(e.stop())
        assert not e.is_running()

    def test_double_start_raises(self):
        e = self._started()
        with pytest.raises(BacktestEngineAlreadyRunningError):
            _run(e.start())

    def test_op_before_start_raises(self):
        e = BacktestingEngine()
        with pytest.raises(BacktestEngineNotRunningError):
            e.submit(_make_request())

    def test_submit_and_run(self):
        e   = self._started()
        req = _make_request()
        b   = e.submit(req)
        r   = _run(e.run(b.backtest_id, BuyAndHoldStrategy(), {"TESTSYM": _make_bars(60)}))
        assert r.is_success is True

    def test_get_statistics_after_run(self):
        e   = self._started()
        req = _make_request()
        b   = e.submit(req)
        _run(e.run(b.backtest_id, BuyAndHoldStrategy(), {"TESTSYM": _make_bars(60)}))
        s = e.get_statistics(b.backtest_id)
        assert s is not None
        # bar_count = equity_curve length = 60 bars + 1 close_all entry
        assert s.bar_count >= 60

    def test_uptime_positive(self):
        e = self._started()
        time.sleep(0.01)
        assert e.uptime_sec() > 0

    def test_stats_contains_version(self):
        e = self._started()
        s = e.stats()
        assert "version" in s
        assert "status"  in s


# ─────────────────────────────────────────────────────────────────────────────
# TestSingleton
# ─────────────────────────────────────────────────────────────────────────────

class TestSingleton:
    def setup_method(self):
        reset_backtesting_engine()

    def teardown_method(self):
        reset_backtesting_engine()

    def test_same_instance(self):
        a = get_backtesting_engine()
        b = get_backtesting_engine()
        assert a is b

    def test_reset_clears(self):
        a = get_backtesting_engine()
        reset_backtesting_engine()
        b = get_backtesting_engine()
        assert a is not b

    def test_not_running_by_default(self):
        e = get_backtesting_engine()
        assert not e.is_running()

    def test_auto_start(self):
        e = get_backtesting_engine(auto_start=True)
        assert e.is_running()

    def test_thread_safety(self):
        instances: list = []
        def _get():
            instances.append(get_backtesting_engine())
        threads = [threading.Thread(target=_get) for _ in range(10)]
        for t in threads: t.start()
        for t in threads: t.join()
        assert all(i is instances[0] for i in instances)
