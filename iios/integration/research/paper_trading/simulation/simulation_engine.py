"""simulation/simulation_engine.py — Core paper trading simulation loop."""
from __future__ import annotations

import inspect
import logging
from dataclasses import dataclass, field
from typing import Any, Optional, Protocol, runtime_checkable

from iios.integration.research.paper_trading.paper_trading_constants import (
    DEFAULT_RISK_FREE_RATE,
    FillModel,
    OrderSide,
    PaperOrderType,
    TimeInForce,
    DEFAULT_COMMISSION_PCT,
    DEFAULT_SLIPPAGE_PCT,
)
from iios.integration.research.paper_trading.core.paper_account    import PaperAccount
from iios.integration.research.paper_trading.core.paper_order      import PaperOrder
from iios.integration.research.paper_trading.core.paper_session    import PaperSession
from iios.integration.research.paper_trading.core.paper_statistics import PaperStatistics
from iios.integration.research.paper_trading.core.paper_trade      import PaperTrade
from iios.integration.research.paper_trading.market.market_simulator import MarketSimulator, PriceBar
from iios.integration.research.paper_trading.execution.slippage_model   import SlippageModel
from iios.integration.research.paper_trading.execution.commission_model import CommissionModel
from iios.integration.research.paper_trading.execution.latency_model    import LatencyModel
from iios.integration.research.paper_trading.execution.fill_simulator   import FillResult, FillSimulator
from iios.integration.research.paper_trading.execution.execution_simulator import ExecutionSimulator
from iios.integration.research.paper_trading.portfolio.portfolio_simulator  import PortfolioSimulator
from iios.integration.research.paper_trading.orders.order_book              import OrderBook
from iios.integration.research.paper_trading.reporting.simulation_report    import SimulationReport

_log = logging.getLogger(__name__)


# ── Strategy protocol ─────────────────────────────────────────────────────────

@dataclass
class OrderSignal:
    """
    An instruction from a strategy to place an order.

    Provide either *quantity* (absolute number of shares/contracts) or
    *size_pct* (fraction of current total equity, 0.0–1.0).
    If both are set, *quantity* takes precedence.
    """
    symbol:      str
    side:        OrderSide
    order_type:  PaperOrderType        = PaperOrderType.MARKET
    quantity:    Optional[float]        = None
    size_pct:    Optional[float]        = None
    limit_price: Optional[float]        = None
    stop_price:  Optional[float]        = None
    tif:         TimeInForce            = TimeInForce.DAY
    metadata:    dict[str, Any]         = field(default_factory=dict)


@runtime_checkable
class PaperTradingStrategy(Protocol):
    """
    Interface that all paper trading strategies must implement.

    Strategies are plugged in via duck typing — no inheritance required.
    """
    strategy_id: str
    name:        str

    def on_session_start(self, account: PaperAccount, config: dict) -> None:
        ...

    def on_bar(
        self,
        bars:           dict[str, PriceBar],
        portfolio_view: dict[str, Any],
    ) -> list[OrderSignal]:
        ...

    def on_session_end(
        self,
        account:        PaperAccount,
        portfolio_view: dict[str, Any],
    ) -> None:
        ...


# ── Session result ────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class PaperSessionResult:
    """Outcome of a completed paper trading session."""
    session:    PaperSession
    account:    PaperAccount
    stats:      PaperStatistics
    report:     dict[str, Any]
    trade_log:  list[PaperTrade]
    fill_log:   list[FillResult]


# ── Simulation engine ─────────────────────────────────────────────────────────

class SimulationEngine:
    """
    Core paper trading simulation loop.

    For each bar in the timeline:
    1. Update prices and mark-to-market positions.
    2. Fill pending orders from the previous bar.
    3. Call ``strategy.on_bar()`` to get new signals.
    4. Convert signals to orders and submit them.
    5. Record equity in the performance tracker.
    6. At the end, force-close all remaining positions.
    """

    def __init__(
        self,
        *,
        commission_pct: float = DEFAULT_COMMISSION_PCT,
        slippage_pct:   float = DEFAULT_SLIPPAGE_PCT,
        fill_model:     FillModel = FillModel.NEXT_OPEN,
    ) -> None:
        self._commission_pct = commission_pct
        self._slippage_pct   = slippage_pct
        self._fill_model     = fill_model

    async def run(
        self,
        session_id:        str,
        account:           PaperAccount,
        config:            dict[str, Any],
        strategy:          PaperTradingStrategy,
        bars_data:         dict[str, list[PriceBar]],
        *,
        risk_free_rate:    float                  = DEFAULT_RISK_FREE_RATE,
        benchmark_returns: Optional[list[float]] = None,
    ) -> PaperSessionResult:
        """Run a complete paper trading session."""

        # ── Build components ──────────────────────────────────────────────────
        slip_model  = SlippageModel(self._slippage_pct)
        comm_model  = CommissionModel(self._commission_pct)
        lat_model   = LatencyModel()
        filler      = FillSimulator(slip_model, comm_model, lat_model, self._fill_model)
        exec_sim    = ExecutionSimulator(filler)
        port_sim    = PortfolioSimulator(account)
        order_book  = OrderBook()
        market_sim  = MarketSimulator()
        market_sim.load(bars_data)

        # Build paper session
        session = PaperSession.create(
            account_id    = account.account_id,
            strategy_id   = strategy.strategy_id,
            strategy_name = strategy.name,
            session_id    = session_id,
        )

        # Collect fills across the session
        all_fills:  list[FillResult] = []

        # ── Session start ─────────────────────────────────────────────────────
        timeline = market_sim.sorted_timeline()
        session.start(len(timeline))
        _on_start = strategy.on_session_start
        if inspect.iscoroutinefunction(_on_start):
            await _on_start(account, config)  # type: ignore[misc]
        else:
            _on_start(account, config)

        # ── Main loop ─────────────────────────────────────────────────────────
        for bar_index, (ts, sym, bar) in enumerate(timeline):
            session.advance(bar_index, ts)

            # Collect bars at this timestamp
            bars_at_ts: dict[str, PriceBar] = {}
            for _, s, b in [e for e in timeline if e[0] == ts]:
                bars_at_ts[s] = b

            # Update prices
            prices = {s: b.close for s, b in bars_at_ts.items()}
            port_sim.update_prices(prices, ts)

            # Fill pending orders
            fills = exec_sim.process_bar(bars_at_ts)
            for fill in fills:
                all_fills.append(fill)
                port_sim.process_fill(fill, ts)
                order_book.update(exec_sim.get_order(fill.order_id))

            # Call strategy
            portfolio_view = {
                "cash":        account.cash,
                "equity":      port_sim.total_equity(),
                "positions":   {
                    sym: pos.to_dict()
                    for sym, pos in port_sim._portfolio.positions.items()
                },
                "bar_index":   bar_index,
                "timestamp":   ts,
            }
            _on_bar = strategy.on_bar
            if inspect.iscoroutinefunction(_on_bar):
                signals: list[OrderSignal] = await _on_bar(bars_at_ts, portfolio_view)  # type: ignore[misc]
            else:
                signals = _on_bar(bars_at_ts, portfolio_view)

            # Convert signals → orders
            for sig in (signals or []):
                qty = self._resolve_quantity(sig, port_sim.total_equity())
                if qty <= 0.0:
                    continue
                order = PaperOrder.create(
                    account_id  = account.account_id,
                    session_id  = session_id,
                    symbol      = sig.symbol,
                    side        = sig.side,
                    order_type  = sig.order_type,
                    quantity    = qty,
                    limit_price = sig.limit_price,
                    stop_price  = sig.stop_price,
                    tif         = sig.tif,
                    metadata    = sig.metadata,
                )
                exec_sim.submit_order(order)
                order_book.add(order)

        # ── Session end: force-close all positions ────────────────────────────
        latest_prices = market_sim.latest_prices()
        last_ts       = timeline[-1][0] if timeline else 0.0
        eod_trades    = port_sim.close_all(latest_prices, last_ts)

        _on_end = strategy.on_session_end
        if inspect.iscoroutinefunction(_on_end):
            await _on_end(account, {})  # type: ignore[misc]
        else:
            _on_end(account, {})

        session.end()

        # ── Compute statistics ─────────────────────────────────────────────────
        all_trades    = port_sim.completed_trades()
        equity_curve  = port_sim.equity_curve()
        all_orders    = order_book.all_orders()

        stats = PaperStatistics.compute(
            initial_capital   = account.initial_capital,
            equity_curve      = equity_curve,
            trade_dicts       = [t.to_dict() for t in all_trades],
            order_dicts       = [o.to_dict() for o in all_orders],
            risk_free_rate    = risk_free_rate,
            benchmark_returns = benchmark_returns,
        )
        stats.bar_count = len(timeline)

        # ── Build report ───────────────────────────────────────────────────────
        reporter = SimulationReport()
        report   = reporter.build(
            session      = session,
            stats        = stats,
            account      = account,
            equity_curve = equity_curve,
            trade_log    = all_trades,
            orders       = all_orders,
        )

        return PaperSessionResult(
            session   = session,
            account   = account,
            stats     = stats,
            report    = report,
            trade_log = all_trades,
            fill_log  = all_fills,
        )

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _resolve_quantity(signal: OrderSignal, equity: float) -> float:
        if signal.quantity is not None and signal.quantity > 0.0:
            return signal.quantity
        if signal.size_pct is not None and signal.size_pct > 0.0:
            return signal.size_pct * equity
        return 0.0
