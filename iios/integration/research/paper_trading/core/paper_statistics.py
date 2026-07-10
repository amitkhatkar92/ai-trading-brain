"""core/paper_statistics.py — Aggregate performance statistics for a paper trading session."""
from __future__ import annotations

import statistics as _stats
from dataclasses import dataclass, field
from typing import Any, Optional

from iios.integration.research.paper_trading.paper_trading_constants import (
    TRADING_DAYS_PER_YEAR,
)


def _safe_div(num: float, den: float, default: float = 0.0) -> float:
    return num / den if den != 0.0 else default


@dataclass
class PaperStatistics:
    """
    Aggregate performance statistics for a completed paper trading session.

    All percentage values are fractions (e.g. 0.10 = 10 %).
    All monetary values use the account's currency.
    """

    # ── Capital ───────────────────────────────────────────────────────────────
    initial_capital:      float = 0.0
    final_equity:         float = 0.0
    total_return:         float = 0.0
    annualized_return:    float = 0.0

    # ── Risk ──────────────────────────────────────────────────────────────────
    volatility:           float = 0.0
    sharpe_ratio:         float = 0.0
    sortino_ratio:        float = 0.0
    calmar_ratio:         float = 0.0
    max_drawdown:         float = 0.0
    max_drawdown_duration: int  = 0
    value_at_risk_95:     float = 0.0

    # ── Trade metrics ─────────────────────────────────────────────────────────
    total_trades:         int   = 0
    winning_trades:       int   = 0
    losing_trades:        int   = 0
    win_rate:             float = 0.0
    profit_factor:        float = 0.0
    expectancy:           float = 0.0
    avg_win:              float = 0.0
    avg_loss:             float = 0.0
    largest_win:          float = 0.0
    largest_loss:         float = 0.0
    avg_trade_duration:   float = 0.0

    # ── Order metrics ─────────────────────────────────────────────────────────
    total_orders:         int   = 0
    filled_orders:        int   = 0
    rejected_orders:      int   = 0
    fill_rate:            float = 0.0

    # ── Cost metrics ─────────────────────────────────────────────────────────
    total_commission:     float = 0.0
    total_slippage:       float = 0.0

    # ── Session metrics ───────────────────────────────────────────────────────
    bar_count:            int   = 0

    # ── Factory ───────────────────────────────────────────────────────────────

    @classmethod
    def compute(
        cls,
        *,
        initial_capital:   float,
        equity_curve:      list[tuple[float, float]],
        trade_dicts:       list[dict[str, Any]],
        order_dicts:       list[dict[str, Any]],
        risk_free_rate:    float = 0.06,
        benchmark_returns: Optional[list[float]] = None,
    ) -> "PaperStatistics":
        """
        Compute all statistics from raw session data.

        Parameters
        ----------
        initial_capital  : starting capital
        equity_curve     : [(timestamp, equity_value), ...] ordered by time
        trade_dicts      : list of trade.to_dict() records
        order_dicts      : list of order.to_dict() records
        risk_free_rate   : annual risk-free rate (fraction)
        benchmark_returns: optional list of daily benchmark returns
        """
        stat = cls(initial_capital=initial_capital)
        stat.bar_count = len(equity_curve)

        # ── Equity & returns ──────────────────────────────────────────────────
        if equity_curve:
            values           = [v for _, v in equity_curve]
            stat.final_equity = values[-1]
            stat.total_return = _safe_div(
                stat.final_equity - initial_capital, initial_capital
            )

            daily_returns: list[float] = []
            for i in range(1, len(values)):
                prev = values[i - 1]
                if prev != 0.0:
                    daily_returns.append((values[i] - prev) / prev)

            if len(daily_returns) >= 2:
                stat.volatility = _stats.stdev(daily_returns) * (TRADING_DAYS_PER_YEAR ** 0.5)
                # Sharpe
                daily_rf        = risk_free_rate / TRADING_DAYS_PER_YEAR
                excess          = [r - daily_rf for r in daily_returns]
                ex_std          = _stats.stdev(excess)
                if ex_std > 0.0:
                    stat.sharpe_ratio = (sum(excess) / len(excess)) / ex_std * (TRADING_DAYS_PER_YEAR ** 0.5)
                # Sortino
                downside        = [r for r in daily_returns if r < daily_rf]
                if downside:
                    down_std        = (_stats.variance(downside) ** 0.5) * (TRADING_DAYS_PER_YEAR ** 0.5)
                    ann_ret         = (1 + sum(daily_returns) / len(daily_returns)) ** TRADING_DAYS_PER_YEAR - 1
                    stat.annualized_return = ann_ret
                    if down_std > 0.0:
                        stat.sortino_ratio = (ann_ret - risk_free_rate) / down_std
                else:
                    ann_ret                = (1 + sum(daily_returns) / len(daily_returns)) ** TRADING_DAYS_PER_YEAR - 1
                    stat.annualized_return = ann_ret
                # Max drawdown
                peak = values[0]
                max_dd = 0.0
                for v in values:
                    if v > peak:
                        peak = v
                    dd = _safe_div(peak - v, peak, 0.0)
                    if dd > max_dd:
                        max_dd = dd
                stat.max_drawdown = max_dd
                # Calmar
                if max_dd > 0.0:
                    stat.calmar_ratio = _safe_div(stat.annualized_return, max_dd)
                # VaR 95 %
                if len(daily_returns) >= 2:
                    sorted_r = sorted(daily_returns)
                    idx = max(0, int(len(sorted_r) * 0.05) - 1)
                    stat.value_at_risk_95 = abs(sorted_r[idx])
                # Drawdown duration
                peak_idx = 0
                peak_val = values[0]
                max_dur  = 0
                for i, v in enumerate(values):
                    if v >= peak_val:
                        peak_val = v
                        peak_idx = i
                    dur = i - peak_idx
                    if dur > max_dur:
                        max_dur = dur
                stat.max_drawdown_duration = max_dur

        # ── Trade statistics ──────────────────────────────────────────────────
        stat.total_trades  = len(trade_dicts)
        winners = [t for t in trade_dicts if t.get("net_pnl", 0.0) > 0]
        losers  = [t for t in trade_dicts if t.get("net_pnl", 0.0) < 0]
        stat.winning_trades = len(winners)
        stat.losing_trades  = len(losers)
        stat.win_rate       = _safe_div(len(winners), len(trade_dicts))
        wins_sum = sum(t["net_pnl"] for t in winners)
        loss_sum = abs(sum(t["net_pnl"] for t in losers))
        stat.profit_factor  = _safe_div(wins_sum, loss_sum, float("inf") if wins_sum > 0 else 0.0)
        stat.expectancy     = _safe_div(sum(t.get("net_pnl", 0.0) for t in trade_dicts), len(trade_dicts))
        stat.avg_win        = _safe_div(wins_sum, len(winners))
        stat.avg_loss       = _safe_div(loss_sum, len(losers))
        stat.largest_win    = max((t["net_pnl"] for t in winners), default=0.0)
        stat.largest_loss   = max((abs(t["net_pnl"]) for t in losers), default=0.0)
        durations           = [t.get("duration_sec", 0.0) for t in trade_dicts]
        stat.avg_trade_duration = _safe_div(sum(durations), len(durations))
        stat.total_commission   = sum(t.get("commission", 0.0) for t in trade_dicts)
        stat.total_slippage     = sum(t.get("slippage", 0.0) for t in trade_dicts)

        # ── Order statistics ──────────────────────────────────────────────────
        from iios.integration.research.paper_trading.paper_trading_constants import PaperOrderStatus
        stat.total_orders    = len(order_dicts)
        stat.filled_orders   = sum(1 for o in order_dicts if o.get("status") == PaperOrderStatus.FILLED.value)
        stat.rejected_orders = sum(1 for o in order_dicts if o.get("status") == PaperOrderStatus.REJECTED.value)
        stat.fill_rate       = _safe_div(stat.filled_orders, stat.total_orders)

        return stat

    def to_dict(self) -> dict[str, Any]:
        return {
            "initial_capital":       self.initial_capital,
            "final_equity":          self.final_equity,
            "total_return":          self.total_return,
            "annualized_return":     self.annualized_return,
            "volatility":            self.volatility,
            "sharpe_ratio":          self.sharpe_ratio,
            "sortino_ratio":         self.sortino_ratio,
            "calmar_ratio":          self.calmar_ratio,
            "max_drawdown":          self.max_drawdown,
            "max_drawdown_duration": self.max_drawdown_duration,
            "value_at_risk_95":      self.value_at_risk_95,
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
            "avg_trade_duration":    self.avg_trade_duration,
            "total_orders":          self.total_orders,
            "filled_orders":         self.filled_orders,
            "rejected_orders":       self.rejected_orders,
            "fill_rate":             self.fill_rate,
            "total_commission":      self.total_commission,
            "total_slippage":        self.total_slippage,
            "bar_count":             self.bar_count,
        }
