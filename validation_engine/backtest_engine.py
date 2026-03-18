"""
Validation Engine — Backtest Engine
=====================================
In-Sample (IS) and Out-of-Sample (OOS) backtesting.

Splits a P&L / trade series into training and testing windows,
computes full statistics on each, and flags overfitting when
OOS performance degrades beyond acceptable thresholds.

Degradation rules (institutional standards):
  • Sharpe degradation     > 40%  → overfitting warning
  • Sharpe degradation     > 60%  → overfitting failure
  • Win-rate drop          > 15pp → overfitting warning
  • Profit-factor collapse < 1.0  → overfitting failure

Usage::
    engine = BacktestEngine(is_ratio=0.70)
    result = engine.run(strategy_name, pnl_series, capital)
    # result.oos_sharpe, result.is_sharpe, result.overfitting_flag
"""

from __future__ import annotations
import math
import statistics
from dataclasses import dataclass, field
from typing import Optional

from utils import get_logger

log = get_logger(__name__)

# Default IS/OOS split
DEFAULT_IS_RATIO = 0.70   # 70% in-sample, 30% out-of-sample

# Degradation thresholds
SHARPE_DEGRADE_WARN  = 0.40   # >40% drop = warning
SHARPE_DEGRADE_FAIL  = 0.60   # >60% drop = fail
WINRATE_DROP_WARN    = 15.0   # >15pp drop = warning
PF_OOS_MIN           = 1.0    # OOS profit factor must stay > 1.0

# Minimum quality gates
MIN_IS_SHARPE        = 1.2
MIN_IS_PROFIT_FACTOR = 1.5
MAX_IS_DRAWDOWN_PCT  = 20.0


@dataclass
class PeriodStats:
    """Statistics for one period (IS or OOS)."""
    period:       str       # "in_sample" | "out_of_sample"
    n_trades:     int       = 0
    total_pnl:    float     = 0.0
    return_pct:   float     = 0.0
    sharpe:       float     = 0.0
    sortino:      float     = 0.0
    profit_factor:float     = 0.0
    win_rate:     float     = 0.0
    max_dd_pct:   float     = 0.0
    avg_win:      float     = 0.0
    avg_loss:     float     = 0.0
    expectancy:   float     = 0.0

    def summary_line(self) -> str:
        label = "In-Sample   " if self.period == "in_sample" else "Out-of-Sample"
        return (f"  {label}  Sharpe={self.sharpe:+.2f}  "
                f"PF={self.profit_factor:.2f}  "
                f"WinRate={self.win_rate:.0f}%  "
                f"MaxDD={self.max_dd_pct:.1f}%  "
                f"Return={self.return_pct:+.2f}%")


@dataclass
class BacktestResult:
    strategy_name:    str
    is_stats:         Optional[PeriodStats] = None
    oos_stats:        Optional[PeriodStats] = None
    sharpe_degrade:   float = 0.0     # fraction drop IS→OOS
    winrate_drop:     float = 0.0     # pp drop
    overfitting_flag: str   = "PASS"  # "PASS" | "WARNING" | "FAIL"
    is_quality_gate:  bool  = True    # does IS pass minimum quality?
    notes:            list  = field(default_factory=list)

    def passed(self) -> bool:
        return self.is_quality_gate and self.overfitting_flag != "FAIL"


class BacktestEngine:
    """
    Runs IS/OOS backtesting on a trade P&L series.

    The series is a list of P&L values (one per trade, in order).
    Real signal functions are not evaluated here — the assumption is
    that signals have already been generated and P&Ls collected.
    """

    def __init__(self, is_ratio: float = DEFAULT_IS_RATIO) -> None:
        self._is_ratio = is_ratio
        log.info("[BacktestEngine] Initialised. IS ratio=%.0f%% | "
                 "OOS ratio=%.0f%%",
                 is_ratio * 100, (1 - is_ratio) * 100)

    # ── Public API ────────────────────────────────────────────────────────
    def run(self, strategy_name: str, pnl_series: list[float],
            capital: float = 1_000_000) -> BacktestResult:
        """
        Parameters
        ----------
        strategy_name : str
        pnl_series    : list of per-trade P&L values in chronological order
        capital       : starting capital for return % calculation
        """
        n = len(pnl_series)
        if n < 10:
            log.warning("[BacktestEngine] %s: insufficient data (%d trades).",
                        strategy_name, n)
            return BacktestResult(
                strategy_name=strategy_name,
                notes=["Insufficient data (< 10 trades)"],
                is_quality_gate=False,
                overfitting_flag="FAIL",
            )

        split     = int(n * self._is_ratio)
        is_pnls   = pnl_series[:split]
        oos_pnls  = pnl_series[split:]

        is_stats  = self._compute_stats("in_sample",    is_pnls,  capital)
        oos_stats = self._compute_stats("out_of_sample", oos_pnls, capital)

        # Quality gate on IS
        is_quality = (
            is_stats.sharpe       >= MIN_IS_SHARPE and
            is_stats.profit_factor>= MIN_IS_PROFIT_FACTOR and
            is_stats.max_dd_pct   <= MAX_IS_DRAWDOWN_PCT
        )

        # Degradation
        sharpe_degrade = 0.0
        if is_stats.sharpe > 0:
            sharpe_degrade = max(0.0,
                (is_stats.sharpe - oos_stats.sharpe) / is_stats.sharpe)
        winrate_drop = max(0.0, is_stats.win_rate - oos_stats.win_rate)

        # Overfitting verdict
        notes: list[str] = []
        if not is_quality:
            if is_stats.sharpe < MIN_IS_SHARPE:
                notes.append(f"IS Sharpe={is_stats.sharpe:.2f} < {MIN_IS_SHARPE} "
                              f"(minimum threshold)")
            if is_stats.profit_factor < MIN_IS_PROFIT_FACTOR:
                notes.append(f"IS ProfitFactor={is_stats.profit_factor:.2f} < "
                              f"{MIN_IS_PROFIT_FACTOR}")
            if is_stats.max_dd_pct > MAX_IS_DRAWDOWN_PCT:
                notes.append(f"IS MaxDD={is_stats.max_dd_pct:.1f}% > "
                              f"{MAX_IS_DRAWDOWN_PCT}%")

        if sharpe_degrade >= SHARPE_DEGRADE_FAIL:
            overfitting_flag = "FAIL"
            notes.append(f"Sharpe degradation={sharpe_degrade:.0%} ≥ "
                         f"{SHARPE_DEGRADE_FAIL:.0%} — OVERFITTING DETECTED")
        elif sharpe_degrade >= SHARPE_DEGRADE_WARN or winrate_drop >= WINRATE_DROP_WARN:
            overfitting_flag = "WARNING"
            notes.append(f"Sharpe degradation={sharpe_degrade:.0%} or "
                         f"WinRate drop={winrate_drop:.1f}pp — monitor closely")
        elif oos_stats.profit_factor < PF_OOS_MIN:
            overfitting_flag = "FAIL"
            notes.append(f"OOS ProfitFactor={oos_stats.profit_factor:.2f} < 1.0 "
                         f"— strategy loses money out-of-sample")
        else:
            overfitting_flag = "PASS"
            notes.append(f"IS→OOS degradation acceptable "
                         f"(Sharpe: {is_stats.sharpe:.2f}→{oos_stats.sharpe:.2f})")

        result = BacktestResult(
            strategy_name    = strategy_name,
            is_stats         = is_stats,
            oos_stats        = oos_stats,
            sharpe_degrade   = round(sharpe_degrade, 3),
            winrate_drop     = round(winrate_drop, 1),
            overfitting_flag = overfitting_flag,
            is_quality_gate  = is_quality,
            notes            = notes,
        )

        self._log_result(result)
        return result

    # ── Private helpers ───────────────────────────────────────────────────
    @staticmethod
    def _compute_stats(period: str, pnls: list[float],
                       capital: float) -> PeriodStats:
        n = len(pnls)
        if n == 0:
            return PeriodStats(period=period)

        total_pnl   = sum(pnls)
        return_pct  = total_pnl / capital * 100
        wins        = [p for p in pnls if p > 0]
        losses      = [p for p in pnls if p <= 0]
        win_rate    = len(wins) / n * 100
        avg_win     = statistics.mean(wins)   if wins   else 0.0
        avg_loss    = statistics.mean(losses) if losses else 0.0
        gross_profit= sum(wins)
        gross_loss  = abs(sum(losses)) if losses else 1e-9
        pf          = gross_profit / gross_loss

        # Sharpe (annualised, per-trade proxy)
        daily_rets  = [p / capital for p in pnls]
        sharpe = sortino = 0.0
        if len(daily_rets) > 1:
            mu    = statistics.mean(daily_rets)
            sigma = statistics.stdev(daily_rets)
            if sigma > 0:
                sharpe = (mu / sigma) * math.sqrt(252)
            neg   = [r for r in daily_rets if r < 0]
            ddev  = math.sqrt(sum(r**2 for r in neg) / n) if neg else 1e-9
            sortino = (mu / ddev) * math.sqrt(252) if ddev > 0 else 0.0

        # Max drawdown
        equity = capital
        peak   = capital
        max_dd = 0.0
        for p in pnls:
            equity += p
            peak = max(peak, equity)
            dd   = (peak - equity) / peak * 100
            max_dd = max(max_dd, dd)

        # Expectancy
        wr      = win_rate / 100
        expec   = wr * avg_win - (1 - wr) * abs(avg_loss)

        return PeriodStats(
            period        = period,
            n_trades      = n,
            total_pnl     = round(total_pnl,    2),
            return_pct    = round(return_pct,   3),
            sharpe        = round(sharpe,        3),
            sortino       = round(sortino,       3),
            profit_factor = round(pf,            3),
            win_rate      = round(win_rate,      1),
            max_dd_pct    = round(max_dd,        2),
            avg_win       = round(avg_win,       2),
            avg_loss      = round(avg_loss,      2),
            expectancy    = round(expec,         2),
        )

    @staticmethod
    def _log_result(r: BacktestResult) -> None:
        verdict_sym = {"PASS": "✅", "WARNING": "⚠️", "FAIL": "❌"}.get(
            r.overfitting_flag, "?")
        log.info("[BacktestEngine] %s %s | %s",
                 verdict_sym, r.strategy_name, r.overfitting_flag)
        if r.is_stats:
            log.info(r.is_stats.summary_line())
        if r.oos_stats:
            log.info(r.oos_stats.summary_line())
        for note in r.notes:
            log.info("  ↳ %s", note)
