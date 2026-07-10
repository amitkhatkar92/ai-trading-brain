"""portfolio/portfolio_simulator.py — Ties CashManager, PositionManager, RiskMonitor, and PerformanceTracker together."""
from __future__ import annotations

from typing import Any

from iios.integration.research.paper_trading.core.paper_account   import PaperAccount
from iios.integration.research.paper_trading.core.paper_portfolio import PaperPortfolio, PortfolioSnapshot
from iios.integration.research.paper_trading.core.paper_trade     import PaperTrade
from iios.integration.research.paper_trading.execution.fill_simulator  import FillResult
from iios.integration.research.paper_trading.portfolio.cash_manager    import CashManager
from iios.integration.research.paper_trading.portfolio.position_manager import PositionManager
from iios.integration.research.paper_trading.portfolio.risk_monitor    import RiskMonitor, RiskBreachEvent
from iios.integration.research.paper_trading.portfolio.performance_tracker import PerformanceTracker


class PortfolioSimulator:
    """
    High-level coordinator for a single paper trading session's portfolio.

    On each ``process_fill()``:
    1. Cash is debited/credited by the fill's net cost.
    2. PositionManager opens/updates/closes positions.
    3. RiskMonitor checks thresholds.

    On each ``update_prices()``:
    1. Open positions are mark-to-market'd.
    2. PerformanceTracker records the current equity.
    """

    def __init__(
        self,
        account:           PaperAccount,
        *,
        risk_monitor:      RiskMonitor | None = None,
    ) -> None:
        self._account   = account
        self._cash_mgr  = CashManager(account.initial_capital)
        self._pos_mgr   = PositionManager(account.account_id, account.account_id)
        self._risk      = risk_monitor or RiskMonitor()
        self._perf      = PerformanceTracker()
        # We keep a lightweight portfolio object for reporting / risk checks
        self._portfolio = PaperPortfolio.create(
            account_id = account.account_id,
            session_id = account.account_id,
        )

    # ── Fill processing ───────────────────────────────────────────────────────

    def process_fill(
        self, fill: FillResult, timestamp: float
    ) -> tuple[PaperTrade | None, list[RiskBreachEvent]]:
        """
        Apply a fill: update cash, positions, and risk checks.

        Returns (completed_trade_or_None, risk_breach_events).
        """
        # Update cash
        net = fill.net_cost()
        if net > 0.0:
            self._cash_mgr.debit(net, f"fill_{fill.order_id}")
        else:
            self._cash_mgr.credit(abs(net), f"fill_{fill.order_id}")

        # Sync account cash
        self._account.cash = self._cash_mgr.balance()

        # Update positions
        trade = self._pos_mgr.apply_fill(fill)
        if trade is not None:
            self._perf.record_trade(trade)

        # Sync portfolio positions for risk check
        self._sync_portfolio(timestamp)

        # Risk check
        breaches = self._risk.check(self._account, self._portfolio)

        return trade, breaches

    # ── Price updates ─────────────────────────────────────────────────────────

    def update_prices(self, prices: dict[str, float], timestamp: float) -> None:
        """Mark-to-market all positions and record equity in the performance tracker."""
        self._pos_mgr.update_prices(prices, timestamp)
        self._sync_portfolio(timestamp)
        equity = self._account.cash + self._pos_mgr.total_market_value()
        self._perf.update(equity, timestamp)

    # ── Forced close ─────────────────────────────────────────────────────────

    def close_all(
        self, prices: dict[str, float], timestamp: float
    ) -> list[PaperTrade]:
        """Force-close all open positions (end-of-session)."""
        trades = self._pos_mgr.close_all(prices, timestamp)
        for t in trades:
            self._perf.record_trade(t)
            credit = t.exit_price * t.quantity - t.commission
            self._cash_mgr.credit(credit, f"eod_close_{t.symbol}")
        self._account.cash = self._cash_mgr.balance()
        self._sync_portfolio(timestamp)
        equity = self._account.cash
        self._perf.update(equity, timestamp)
        return trades

    # ── Queries ───────────────────────────────────────────────────────────────

    def portfolio_value(self) -> float:
        return self._pos_mgr.total_market_value()

    def total_equity(self) -> float:
        return self._account.cash + self.portfolio_value()

    def snapshot(self, timestamp: float) -> PortfolioSnapshot:
        return self._portfolio.snapshot(timestamp, self._account.cash)

    def completed_trades(self) -> list[PaperTrade]:
        return self._pos_mgr.completed_trades()

    def equity_curve(self) -> list[tuple[float, float]]:
        return self._perf.equity_curve()

    def performance(self) -> dict[str, Any]:
        return self._perf.stats()

    # ── Private helpers ───────────────────────────────────────────────────────

    def _sync_portfolio(self, timestamp: float) -> None:
        """Rebuild the lightweight portfolio's positions dict from PositionManager."""
        self._portfolio.positions = {
            pos.symbol: pos for pos in self._pos_mgr.open_positions()
        }
        self._portfolio.updated_at = timestamp

    def stats(self) -> dict[str, Any]:
        return {
            "cash":           self._account.cash,
            "portfolio_value": self.portfolio_value(),
            "total_equity":   self.total_equity(),
            "open_positions": len(self._pos_mgr.open_positions()),
            "completed_trades": len(self._pos_mgr.completed_trades()),
            "performance":    self._perf.stats(),
            "risk":           self._risk.stats(),
        }
