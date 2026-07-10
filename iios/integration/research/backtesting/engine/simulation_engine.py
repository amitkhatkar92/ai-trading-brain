"""engine/simulation_engine.py — Core deterministic simulation loop."""
from __future__ import annotations

import inspect
import logging
import time
import uuid
from itertools import groupby
from typing import Any, Callable, Optional, Protocol, runtime_checkable

from iios.integration.research.backtesting.backtest_constants import (
    DEFAULT_MIN_BARS_REQUIRED,
    ExecutionModel,
    OrderDirection,
    SimulationStatus,
)
from iios.integration.research.backtesting.backtest_exceptions import (
    InsufficientDataError,
    SimulationDataError,
    SimulationError,
)
from iios.integration.research.backtesting.core.backtest_configuration import BacktestConfiguration
from iios.integration.research.backtesting.core.backtest_result import BacktestResult
from iios.integration.research.backtesting.core.backtest_session import BacktestSession
from iios.integration.research.backtesting.engine.execution_simulator import ExecutionSimulator
from iios.integration.research.backtesting.engine.market_simulator import BarEvent, MarketSimulator
from iios.integration.research.backtesting.engine.simulation_clock import SimulationClock
from iios.integration.research.backtesting.execution.order import OrderSignal
from iios.integration.research.backtesting.execution.portfolio import Portfolio, PortfolioSnapshot

_log = logging.getLogger(__name__)


# ── Strategy interface ────────────────────────────────────────────────────────

@runtime_checkable
class BacktestStrategy(Protocol):
    """
    Interface every strategy must implement to participate in backtesting.

    The framework calls these methods at deterministic, reproducible points
    during the simulation.  Implementations must be stateful (maintain
    indicator state, position tracking helpers, etc. internally) and must
    not perform I/O or sleep.
    """

    strategy_id: str
    name:        str

    def on_start(self, config: BacktestConfiguration) -> None:
        """Called once before the first bar is delivered."""
        ...

    def on_bar(
        self,
        bars:      dict[str, BarEvent],
        portfolio: PortfolioSnapshot,
    ) -> list[OrderSignal]:
        """
        Called on every simulation timestamp.

        bars      – current bar for every symbol that has data at this timestamp
        portfolio – immutable snapshot of portfolio state at start of this bar

        Returns a (possibly empty) list of OrderSignals.
        """
        ...

    def on_end(self, portfolio: PortfolioSnapshot) -> None:
        """Called once after the last bar is processed."""
        ...


# ── Simulation engine ─────────────────────────────────────────────────────────

class SimulationEngine:
    """
    Deterministic, bar-by-bar simulation engine.

    Usage::

        engine = SimulationEngine()
        result = await engine.run(backtest_id, config, strategy, bars_data)
    """

    def __init__(self) -> None:
        self._runs:     int = 0
        self._failures: int = 0

    async def run(
        self,
        backtest_id: str,
        config:      BacktestConfiguration,
        strategy:    BacktestStrategy,
        bars_data:   dict[str, list[BarEvent]],
    ) -> BacktestResult:
        """
        Execute the simulation and return a BacktestResult.

        bars_data – dict mapping symbol → list[BarEvent] sorted by timestamp.
        """
        start_wall = time.perf_counter()
        session    = BacktestSession(backtest_id=backtest_id)
        result     = BacktestResult(backtest_id=backtest_id)
        self._runs += 1

        try:
            result = await self._run_inner(backtest_id, config, strategy, bars_data, session, start_wall)
        except Exception as exc:
            self._failures += 1
            result.is_success   = False
            result.error        = str(exc)
            result.duration_sec = time.perf_counter() - start_wall
            _log.error("[SimulationEngine] backtest=%s failed: %s", backtest_id, exc)

        return result

    async def _run_inner(
        self,
        backtest_id: str,
        config:      BacktestConfiguration,
        strategy:    BacktestStrategy,
        bars_data:   dict[str, list[BarEvent]],
        session:     BacktestSession,
        start_wall:  float,
    ) -> BacktestResult:

        # ── 1. Validate input ─────────────────────────────────────────────────
        if not bars_data:
            raise SimulationDataError("bars_data is empty")

        total_bars = sum(len(v) for v in bars_data.values())
        if total_bars < config.min_bars:
            raise InsufficientDataError(
                f"Need at least {config.min_bars} bars, got {total_bars}"
            )

        # ── 2. Build sorted timeline: [(ts, symbol, bar)] ─────────────────────
        market_sim = MarketSimulator()
        market_sim.load(bars_data)
        timeline   = market_sim.sorted_timeline()

        # ── 3. Apply corporate-action adjustments ─────────────────────────────
        # (corporate_actions can be wired externally; omitted by default)

        # ── 4. Initialise components ──────────────────────────────────────────
        first_ts   = timeline[0][0]
        last_ts    = timeline[-1][0]
        clock      = SimulationClock()
        clock.initialise(first_ts, last_ts)

        portfolio  = Portfolio(config.initial_capital)
        exec_sim   = ExecutionSimulator(config)

        session.start(total_bars=len(timeline))

        # ── 5. Notify strategy ────────────────────────────────────────────────
        if inspect.iscoroutinefunction(strategy.on_start):
            await strategy.on_start(config)
        else:
            strategy.on_start(config)

        # ── 6. Group timeline by timestamp ────────────────────────────────────
        grouped: list[tuple[float, dict[str, BarEvent]]] = []
        for ts, grp in groupby(timeline, key=lambda x: x[0]):
            bar_map: dict[str, BarEvent] = {sym: bar for (_, sym, bar) in grp}
            grouped.append((ts, bar_map))

        # ── 7. Main simulation loop ───────────────────────────────────────────
        # For NEXT_OPEN: orders submitted at bar T fill at bar T+1's open.
        # For all other models: orders fill on the same bar they were submitted.
        next_open_mode = (config.execution_model == ExecutionModel.NEXT_OPEN)

        for i, (ts, bar_map) in enumerate(grouped):
            clock.advance_to(ts)
            session.advance(i, ts)

            # Fill pending orders (from previous bar) with current prices
            fills = exec_sim.fill_pending(bar_map)
            for fill in fills:
                portfolio.apply_fill(fill)

            # Update portfolio mark-to-market
            prices = {sym: bar.close for sym, bar in bar_map.items()}
            portfolio.update_prices(prices, ts)

            # Get strategy signals
            snap    = portfolio.snapshot(ts)
            signals = None
            try:
                if inspect.iscoroutinefunction(strategy.on_bar):
                    signals = await strategy.on_bar(bar_map, snap)
                else:
                    signals = strategy.on_bar(bar_map, snap)
            except Exception as exc:
                _log.warning(
                    "[SimulationEngine] strategy.on_bar raised at bar %d: %s", i, exc
                )

            # Submit signals; if not NEXT_OPEN, fill immediately on same bar
            if signals:
                for signal in signals:
                    if signal.symbol in bar_map:
                        exec_sim.submit_signal(signal, portfolio, bar_map[signal.symbol])

                if not next_open_mode:
                    same_fills = exec_sim.fill_pending(bar_map)
                    for fill in same_fills:
                        portfolio.apply_fill(fill)

        # ── 8. Force-close all open positions at last prices ──────────────────
        last_bar_map = grouped[-1][1] if grouped else {}
        last_ts_val  = grouped[-1][0] if grouped else first_ts
        last_prices  = {sym: bar.close for sym, bar in last_bar_map.items()}
        portfolio.close_all_positions(last_prices, last_ts_val)

        # ── 9. Notify strategy of simulation end ──────────────────────────────
        final_snap = portfolio.snapshot(last_ts_val)
        if inspect.iscoroutinefunction(strategy.on_end):
            await strategy.on_end(final_snap)
        else:
            strategy.on_end(final_snap)

        session.end()

        # ── 10. Build result ──────────────────────────────────────────────────
        result = BacktestResult(
            backtest_id  = backtest_id,
            is_success   = True,
            equity_curve = portfolio.equity_curve,
            trade_log    = [t.to_dict() for t in portfolio.completed_trades],
            bar_count    = len(timeline),
            trade_count  = len(portfolio.completed_trades),
            duration_sec = time.perf_counter() - start_wall,
        )
        return result

    # ── Accessors ─────────────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        return {
            "runs":           self._runs,
            "failures":       self._failures,
            "success_rate":   (self._runs - self._failures) / self._runs if self._runs else 0.0,
        }
