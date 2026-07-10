"""core/backtest_statistics.py — Aggregate performance statistics computed after a run."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class BacktestStatistics:
    """
    Computed once per BacktestResult by PerformanceEngine.
    All pct values are fractional (0.1 == 10 %).
    """

    # ── Return metrics ────────────────────────────────────────────────────────
    initial_capital:       float = 0.0
    final_equity:          float = 0.0
    net_profit:            float = 0.0
    total_return_pct:      float = 0.0
    annualized_return_pct: float = 0.0

    # ── Risk metrics ──────────────────────────────────────────────────────────
    volatility_pct:        float = 0.0
    sharpe_ratio:          float = 0.0
    sortino_ratio:         float = 0.0
    calmar_ratio:          float = 0.0
    max_drawdown_pct:      float = 0.0
    max_drawdown_duration: int   = 0    # bars
    recovery_factor:       float = 0.0

    # ── Trade statistics ──────────────────────────────────────────────────────
    total_trades:          int   = 0
    winning_trades:        int   = 0
    losing_trades:         int   = 0
    win_rate:              float = 0.0
    profit_factor:         float = 0.0
    expectancy:            float = 0.0   # avg net PnL per trade
    avg_win:               float = 0.0
    avg_loss:              float = 0.0
    avg_trade_duration_sec: float = 0.0
    largest_win:           float = 0.0
    largest_loss:          float = 0.0

    # ── Bar statistics ────────────────────────────────────────────────────────
    bar_count:             int   = 0
    trading_days:          int   = 0

    # ── Benchmark ─────────────────────────────────────────────────────────────
    benchmark_return_pct:  Optional[float] = None
    alpha:                 Optional[float] = None
    beta:                  Optional[float] = None

    # ── Factory ───────────────────────────────────────────────────────────────

    @classmethod
    def compute(
        cls,
        equity_curve: list[tuple[float, float]],
        trades:       list[dict[str, Any]],
        *,
        risk_free_rate: float = 0.06,
        benchmark_returns: Optional[list[float]] = None,
    ) -> "BacktestStatistics":
        """Compute all statistics from raw simulation outputs."""
        from iios.integration.research.backtesting.metrics.return_calculator   import (
            calculate_bar_returns, total_return, annualized_return,
        )
        from iios.integration.research.backtesting.metrics.drawdown_calculator import (
            max_drawdown, max_drawdown_duration_bars,
        )
        from iios.integration.research.backtesting.metrics.risk_metrics import (
            sharpe_ratio, sortino_ratio, calmar_ratio, volatility, compute_beta,
        )
        from iios.integration.research.backtesting.metrics.trade_statistics import (
            win_rate as wrate, profit_factor as pfactor,
            expectancy as expect, avg_win, avg_loss,
            largest_win, largest_loss, avg_trade_duration,
        )
        from iios.integration.research.backtesting.backtest_constants import TRADING_DAYS_PER_YEAR

        s = cls()

        if not equity_curve:
            return s

        initial = equity_curve[0][1]
        final   = equity_curve[-1][1]
        s.initial_capital = initial
        s.final_equity    = final
        s.net_profit      = final - initial
        s.total_return_pct = total_return(initial, final)

        bar_returns = calculate_bar_returns(equity_curve)
        s.bar_count    = len(equity_curve)
        s.trading_days = s.bar_count  # 1 bar ≈ 1 trading day

        s.annualized_return_pct = annualized_return(s.total_return_pct, s.trading_days)
        s.volatility_pct        = volatility(bar_returns)
        s.sharpe_ratio          = sharpe_ratio(bar_returns, risk_free_rate)
        s.sortino_ratio         = sortino_ratio(bar_returns, risk_free_rate)
        s.max_drawdown_pct      = max_drawdown(equity_curve)
        s.max_drawdown_duration = max_drawdown_duration_bars(equity_curve)
        s.calmar_ratio          = calmar_ratio(s.annualized_return_pct, s.max_drawdown_pct)
        s.recovery_factor       = (
            s.net_profit / (s.max_drawdown_pct * initial)
            if s.max_drawdown_pct > 0 else 0.0
        )

        if trades:
            s.total_trades    = len(trades)
            s.winning_trades  = sum(1 for t in trades if t.get("net_pnl", 0) > 0)
            s.losing_trades   = sum(1 for t in trades if t.get("net_pnl", 0) < 0)
            s.win_rate        = wrate(trades)
            s.profit_factor   = pfactor(trades)
            s.expectancy      = expect(trades)
            s.avg_win         = avg_win(trades)
            s.avg_loss        = avg_loss(trades)
            s.largest_win     = largest_win(trades)
            s.largest_loss    = largest_loss(trades)
            s.avg_trade_duration_sec = avg_trade_duration(trades)

        if benchmark_returns is not None:
            bench_total = 1.0
            for r in benchmark_returns:
                bench_total *= (1 + r)
            s.benchmark_return_pct = bench_total - 1.0
            s.beta  = compute_beta(bar_returns, benchmark_returns)
            mkt_ann = annualized_return(s.benchmark_return_pct, len(benchmark_returns))
            s.alpha = s.annualized_return_pct - (
                risk_free_rate + s.beta * (mkt_ann - risk_free_rate)
            )

        return s

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "initial_capital":       self.initial_capital,
            "final_equity":          self.final_equity,
            "net_profit":            self.net_profit,
            "total_return_pct":      self.total_return_pct,
            "annualized_return_pct": self.annualized_return_pct,
            "volatility_pct":        self.volatility_pct,
            "sharpe_ratio":          self.sharpe_ratio,
            "sortino_ratio":         self.sortino_ratio,
            "calmar_ratio":          self.calmar_ratio,
            "max_drawdown_pct":      self.max_drawdown_pct,
            "max_drawdown_duration": self.max_drawdown_duration,
            "recovery_factor":       self.recovery_factor,
            "total_trades":          self.total_trades,
            "winning_trades":        self.winning_trades,
            "losing_trades":         self.losing_trades,
            "win_rate":              self.win_rate,
            "profit_factor":         self.profit_factor,
            "expectancy":            self.expectancy,
            "avg_win":               self.avg_win,
            "avg_loss":              self.avg_loss,
            "largest_win":           self.largest_win,
            "largest_loss":          self.largest_loss,
            "avg_trade_duration_sec": self.avg_trade_duration_sec,
            "bar_count":             self.bar_count,
            "trading_days":          self.trading_days,
            "benchmark_return_pct":  self.benchmark_return_pct,
            "alpha":                 self.alpha,
            "beta":                  self.beta,
            "success_rate":          self.win_rate,  # alias
        }
