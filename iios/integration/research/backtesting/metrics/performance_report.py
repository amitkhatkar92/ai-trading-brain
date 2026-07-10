"""metrics/performance_report.py — Structured performance report from statistics."""
from __future__ import annotations

from typing import Any, Optional

from iios.integration.research.backtesting.core.backtest_statistics import BacktestStatistics
from iios.integration.research.backtesting.metrics.return_calculator import (
    monthly_returns,
    annual_returns,
)
from iios.integration.research.backtesting.metrics.drawdown_calculator import drawdown_periods


class PerformanceReport:
    """
    Builds a structured performance report dict from BacktestStatistics
    and optional raw artefacts.
    """

    def build(
        self,
        stats:        BacktestStatistics,
        equity_curve: list[tuple[float, float]],
        trade_log:    list[dict[str, Any]],
        *,
        include_monthly:     bool = True,
        include_annual:      bool = True,
        include_dd_periods:  bool = True,
        dd_threshold:        float = 0.05,
    ) -> dict[str, Any]:
        """
        Construct a complete performance report dict.

        All keys are stable — downstream consumers can rely on them.
        """
        report: dict[str, Any] = {
            "summary":    self._summary(stats),
            "risk":       self._risk(stats),
            "trades":     self._trades(stats, trade_log),
        }

        if include_monthly:
            report["monthly_returns"] = monthly_returns(equity_curve)

        if include_annual:
            report["annual_returns"] = annual_returns(equity_curve)

        if include_dd_periods:
            report["drawdown_periods"] = drawdown_periods(equity_curve, dd_threshold)

        return report

    # ── Sections ──────────────────────────────────────────────────────────────

    def _summary(self, s: BacktestStatistics) -> dict[str, Any]:
        return {
            "initial_capital":       s.initial_capital,
            "final_equity":          s.final_equity,
            "net_profit":            s.net_profit,
            "total_return_pct":      round(s.total_return_pct * 100, 4),
            "annualized_return_pct": round(s.annualized_return_pct * 100, 4),
            "bar_count":             s.bar_count,
            "trading_days":          s.trading_days,
        }

    def _risk(self, s: BacktestStatistics) -> dict[str, Any]:
        return {
            "volatility_pct":        round(s.volatility_pct * 100, 4),
            "sharpe_ratio":          round(s.sharpe_ratio, 4),
            "sortino_ratio":         round(s.sortino_ratio, 4),
            "calmar_ratio":          round(s.calmar_ratio, 4),
            "max_drawdown_pct":      round(s.max_drawdown_pct * 100, 4),
            "max_drawdown_duration": s.max_drawdown_duration,
            "recovery_factor":       round(s.recovery_factor, 4),
            "benchmark_return_pct":  (
                round(s.benchmark_return_pct * 100, 4)
                if s.benchmark_return_pct is not None else None
            ),
            "alpha":  round(s.alpha, 4) if s.alpha is not None else None,
            "beta":   round(s.beta,  4) if s.beta  is not None else None,
        }

    def _trades(self, s: BacktestStatistics, trade_log: list[dict[str, Any]]) -> dict[str, Any]:
        from iios.integration.research.backtesting.metrics.trade_statistics import (
            max_consecutive_wins, max_consecutive_losses, trade_return_distribution,
        )
        return {
            "total_trades":           s.total_trades,
            "winning_trades":         s.winning_trades,
            "losing_trades":          s.losing_trades,
            "win_rate":               round(s.win_rate * 100, 2),
            "profit_factor":          round(s.profit_factor, 4),
            "expectancy":             round(s.expectancy, 4),
            "avg_win":                round(s.avg_win, 4),
            "avg_loss":               round(s.avg_loss, 4),
            "largest_win":            round(s.largest_win, 4),
            "largest_loss":           round(s.largest_loss, 4),
            "avg_trade_duration_sec": round(s.avg_trade_duration_sec, 2),
            "max_consecutive_wins":   max_consecutive_wins(trade_log),
            "max_consecutive_losses": max_consecutive_losses(trade_log),
            "distribution":           trade_return_distribution(trade_log),
        }
