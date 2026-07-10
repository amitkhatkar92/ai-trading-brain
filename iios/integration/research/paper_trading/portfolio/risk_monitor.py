"""portfolio/risk_monitor.py — Real-time risk threshold monitoring."""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from iios.integration.research.paper_trading.paper_trading_constants import (
    DEFAULT_DAILY_LOSS_LIMIT,
    DEFAULT_MAX_DRAWDOWN_LIMIT,
    MAX_POSITION_CONCENTRATION,
    MIN_CASH_BUFFER,
)
from iios.integration.research.paper_trading.core.paper_account import PaperAccount
from iios.integration.research.paper_trading.core.paper_portfolio import PaperPortfolio


@dataclass
class RiskBreachEvent:
    """A single risk limit breach detected during monitoring."""
    rule_name:    str
    breach_value: float
    limit_value:  float
    timestamp:    float
    severity:     str   # "warning" or "critical"
    message:      str


class RiskMonitor:
    """
    Monitors portfolio risk thresholds during a paper trading session.

    Raises warning / critical breaches when:
    - A single position exceeds *max_position_concentration* of total equity
    - Portfolio drawdown from peak exceeds *max_drawdown_pct*
    - Daily loss exceeds *max_daily_loss_pct*
    - Cash drops below *min_cash_buffer* fraction of equity
    """

    def __init__(
        self,
        *,
        max_position_concentration: float = MAX_POSITION_CONCENTRATION,
        max_drawdown_pct:           float = DEFAULT_MAX_DRAWDOWN_LIMIT,
        max_daily_loss_pct:         float = DEFAULT_DAILY_LOSS_LIMIT,
        min_cash_buffer:            float = MIN_CASH_BUFFER,
    ) -> None:
        self._max_concentration = max_position_concentration
        self._max_drawdown      = max_drawdown_pct
        self._max_daily_loss    = max_daily_loss_pct
        self._min_cash_buffer   = min_cash_buffer
        self._peak_equity:  float = 0.0
        self._daily_start:  float = 0.0
        self._total_breaches: int = 0
        self._kill_triggered: bool = False

    # ── Main check ────────────────────────────────────────────────────────────

    def check(
        self,
        account:   PaperAccount,
        portfolio: PaperPortfolio,
    ) -> list[RiskBreachEvent]:
        """Return a list of risk breach events detected at this moment."""
        breaches: list[RiskBreachEvent] = []
        equity   = account.equity(portfolio.total_market_value())
        now      = time.time()

        # Track peak equity
        if equity > self._peak_equity:
            self._peak_equity = equity

        # ── Concentration check ───────────────────────────────────────────────
        if equity > 0.0:
            for symbol, pos in portfolio.positions.items():
                concentration = pos.market_value / equity
                if concentration > self._max_concentration:
                    severity = "critical" if concentration > self._max_concentration * 1.5 else "warning"
                    breaches.append(RiskBreachEvent(
                        rule_name    = "position_concentration",
                        breach_value = concentration,
                        limit_value  = self._max_concentration,
                        timestamp    = now,
                        severity     = severity,
                        message      = (
                            f"{symbol} concentration {concentration:.1%} "
                            f"exceeds limit {self._max_concentration:.1%}"
                        ),
                    ))

        # ── Drawdown check ────────────────────────────────────────────────────
        if self._peak_equity > 0.0:
            drawdown = (self._peak_equity - equity) / self._peak_equity
            if drawdown > self._max_drawdown:
                breaches.append(RiskBreachEvent(
                    rule_name    = "max_drawdown",
                    breach_value = drawdown,
                    limit_value  = self._max_drawdown,
                    timestamp    = now,
                    severity     = "critical",
                    message      = (
                        f"Drawdown {drawdown:.1%} exceeds limit {self._max_drawdown:.1%}"
                    ),
                ))
                self._kill_triggered = True

        # ── Daily loss check ──────────────────────────────────────────────────
        if self._daily_start > 0.0 and self._daily_start != equity:
            daily_loss_pct = (self._daily_start - equity) / self._daily_start
            if daily_loss_pct > self._max_daily_loss:
                breaches.append(RiskBreachEvent(
                    rule_name    = "daily_loss",
                    breach_value = daily_loss_pct,
                    limit_value  = self._max_daily_loss,
                    timestamp    = now,
                    severity     = "critical",
                    message      = (
                        f"Daily loss {daily_loss_pct:.1%} exceeds limit {self._max_daily_loss:.1%}"
                    ),
                ))
                self._kill_triggered = True

        # ── Cash buffer check ─────────────────────────────────────────────────
        if equity > 0.0:
            cash_ratio = account.cash / equity
            if cash_ratio < self._min_cash_buffer:
                breaches.append(RiskBreachEvent(
                    rule_name    = "cash_buffer",
                    breach_value = cash_ratio,
                    limit_value  = self._min_cash_buffer,
                    timestamp    = now,
                    severity     = "warning",
                    message      = (
                        f"Cash ratio {cash_ratio:.1%} below minimum {self._min_cash_buffer:.1%}"
                    ),
                ))

        self._total_breaches += len(breaches)
        return breaches

    def is_kill_switch_triggered(
        self, account: PaperAccount, portfolio: PaperPortfolio
    ) -> bool:
        self.check(account, portfolio)
        return self._kill_triggered

    def set_daily_start_equity(self, equity: float) -> None:
        """Record the equity at the start of the current day for daily loss tracking."""
        self._daily_start = equity

    def reset_kill_switch(self) -> None:
        self._kill_triggered = False

    def stats(self) -> dict[str, Any]:
        return {
            "peak_equity":              self._peak_equity,
            "total_breaches":           self._total_breaches,
            "kill_triggered":           self._kill_triggered,
            "max_position_concentration": self._max_concentration,
            "max_drawdown_pct":         self._max_drawdown,
            "max_daily_loss_pct":       self._max_daily_loss,
            "min_cash_buffer":          self._min_cash_buffer,
        }
