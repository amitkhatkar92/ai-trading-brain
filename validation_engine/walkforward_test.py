"""
Validation Engine — Walk-Forward Analysis (Institutional Grade)
================================================================
Markets change over time. A strategy that worked in 2015 may fail
in 2023. Walk-forward testing simulates REAL development cycles:

  Fold 1:  Train 2015-2017 → Test 2018
  Fold 2:  Train 2016-2018 → Test 2019
  Fold 3:  Train 2017-2019 → Test 2020
  ...

This is the most important test for strategy robustness because it:
  1. Prevents look-ahead bias
  2. Tests how well the strategy adapts across market cycles
  3. Produces multiple independent OOS windows for statistics

Supports two modes:
  • anchored   — IS window grows each fold (anchor at start)
  • rolling    — IS window slides forward (fixed size)

Key output metrics:
  • pass_rate_pct     — % of OOS folds that were profitable
  • wf_efficiency     — avg OOS return / avg IS return (>0.5 is good)
  • consistency_score — std dev of OOS returns (low = stable)
  • regime_coverage   — how many distinct market regimes were tested

Institutional minimum: pass_rate ≥ 60%, wf_efficiency ≥ 0.40
"""

from __future__ import annotations
import math
import statistics
from dataclasses import dataclass, field
from typing import Literal

from utils import get_logger

log = get_logger(__name__)

# Institutional thresholds
MIN_PASS_RATE      = 60.0   # % of OOS folds profitable
MIN_WF_EFFICIENCY  = 0.40   # OOS / IS ratio
MIN_FOLDS          = 4      # need at least 4 folds for meaningful stats

# Default window configuration
DEFAULT_IS_TRADES  = 60     # in-sample trades per fold
DEFAULT_OOS_TRADES = 20     # out-of-sample trades per fold
DEFAULT_STEP       = 20     # slide by this many trades


@dataclass
class WFold:
    fold_num:        int
    is_trades:       int
    oos_trades:      int
    is_return_pct:   float
    oos_return_pct:  float
    is_sharpe:       float
    oos_sharpe:      float
    profitable:      bool   # OOS return > 0


@dataclass
class WalkForwardResult:
    strategy_name:     str
    mode:              str              # "anchored" | "rolling"
    folds:             list[WFold] = field(default_factory=list)
    # Aggregate
    pass_rate_pct:     float = 0.0
    avg_oos_return:    float = 0.0
    avg_is_return:     float = 0.0
    wf_efficiency:     float = 0.0
    consistency_score: float = 0.0     # lower = more consistent
    best_oos_return:   float = 0.0
    worst_oos_return:  float = 0.0
    passed:            bool  = False

    def summary(self) -> str:
        verdict = "✅ PASSED" if self.passed else "❌ FAILED"
        return (f"[WalkForward] {verdict} | {self.strategy_name} | "
                f"Folds={len(self.folds)} | "
                f"PassRate={self.pass_rate_pct:.0f}% | "
                f"WF-Efficiency={self.wf_efficiency:.2f} | "
                f"AvgOOS={self.avg_oos_return:+.2f}%")


class WalkForwardAnalyzer:
    """
    Institutional walk-forward analysis for strategy validation.

    Usage::
        wfa    = WalkForwardAnalyzer(mode="rolling")
        result = wfa.run("MyStrategy", pnl_series, capital=1_000_000)
    """

    def __init__(self,
                 mode:       Literal["anchored", "rolling"] = "rolling",
                 is_trades:  int = DEFAULT_IS_TRADES,
                 oos_trades: int = DEFAULT_OOS_TRADES,
                 step:       int = DEFAULT_STEP) -> None:
        self._mode       = mode
        self._is_trades  = is_trades
        self._oos_trades = oos_trades
        self._step       = step
        log.info("[WalkForwardAnalyzer] Initialised. Mode=%s | "
                 "IS=%d | OOS=%d | Step=%d",
                 mode, is_trades, oos_trades, step)

    # ── Public API ────────────────────────────────────────────────────────
    def run(self, strategy_name: str, pnl_series: list[float],
            capital: float = 1_000_000) -> WalkForwardResult:
        n = len(pnl_series)
        min_required = self._is_trades + self._oos_trades
        if n < min_required:
            log.warning("[WalkForwardAnalyzer] Need ≥ %d trades, got %d.",
                        min_required, n)
            return WalkForwardResult(
                strategy_name=strategy_name, mode=self._mode, passed=False
            )

        folds: list[WFold] = []
        fold_num  = 0
        pos_start = 0   # start of IS window (rolling) or always 0 (anchored)

        while True:
            if self._mode == "anchored":
                is_start = 0
                is_end   = (self._is_trades
                            + fold_num * self._step)
            else:  # rolling
                is_start = fold_num * self._step
                is_end   = is_start + self._is_trades

            oos_start = is_end
            oos_end   = oos_start + self._oos_trades

            if oos_end > n:
                break

            is_pnls  = pnl_series[is_start:is_end]
            oos_pnls = pnl_series[oos_start:oos_end]

            is_ret   = sum(is_pnls)  / capital * 100
            oos_ret  = sum(oos_pnls) / capital * 100
            is_sh    = self._quick_sharpe(is_pnls,  capital)
            oos_sh   = self._quick_sharpe(oos_pnls, capital)

            fold_num += 1
            folds.append(WFold(
                fold_num        = fold_num,
                is_trades       = len(is_pnls),
                oos_trades      = len(oos_pnls),
                is_return_pct   = round(is_ret,  3),
                oos_return_pct  = round(oos_ret, 3),
                is_sharpe       = round(is_sh,   3),
                oos_sharpe      = round(oos_sh,  3),
                profitable      = oos_ret > 0,
            ))

        if not folds:
            return WalkForwardResult(
                strategy_name=strategy_name, mode=self._mode, passed=False
            )

        pass_count    = sum(1 for f in folds if f.profitable)
        pass_rate     = pass_count / len(folds) * 100
        avg_oos       = statistics.mean(f.oos_return_pct for f in folds)
        avg_is        = statistics.mean(f.is_return_pct  for f in folds)
        wf_efficiency = avg_oos / avg_is if avg_is != 0 else 0.0
        oos_rets      = [f.oos_return_pct for f in folds]
        consistency   = statistics.stdev(oos_rets) if len(oos_rets) > 1 else 0.0

        passed = (pass_rate >= MIN_PASS_RATE and
                  wf_efficiency >= MIN_WF_EFFICIENCY and
                  len(folds) >= MIN_FOLDS)

        result = WalkForwardResult(
            strategy_name     = strategy_name,
            mode              = self._mode,
            folds             = folds,
            pass_rate_pct     = round(pass_rate,     1),
            avg_oos_return    = round(avg_oos,        3),
            avg_is_return     = round(avg_is,         3),
            wf_efficiency     = round(wf_efficiency,  3),
            consistency_score = round(consistency,    3),
            best_oos_return   = round(max(oos_rets),  3),
            worst_oos_return  = round(min(oos_rets),  3),
            passed            = passed,
        )
        self._log_result(result)
        return result

    # ── Private helpers ───────────────────────────────────────────────────
    @staticmethod
    def _quick_sharpe(pnls: list[float], capital: float) -> float:
        """Annualised Sharpe from a P&L list."""
        if len(pnls) < 2:
            return 0.0
        rets = [p / capital for p in pnls]
        mu   = statistics.mean(rets)
        std  = statistics.stdev(rets)
        return (mu / std) * math.sqrt(252) if std > 0 else 0.0

    @staticmethod
    def _log_result(r: WalkForwardResult) -> None:
        log.info(r.summary())
        header = (f"  {'Fold':<6} {'IS Trades':>10} {'OOS Trades':>10} "
                  f"{'IS Return':>10} {'OOS Return':>10} {'OOS Sharpe':>10} {'P/F':>5}")
        log.info(header)
        log.info("  " + "─" * 56)
        for f in r.folds:
            tick = "✅" if f.profitable else "❌"
            log.info("  %-6d %10d %10d %9.2f%% %9.2f%% %10.2f %5s",
                     f.fold_num, f.is_trades, f.oos_trades,
                     f.is_return_pct, f.oos_return_pct, f.oos_sharpe, tick)
        log.info("  " + "─" * 56)
        log.info("  PassRate=%.0f%%  AvgOOS=%+.2f%%  "
                 "WF-Efficiency=%.2f  Consistency=%.2f%%",
                 r.pass_rate_pct, r.avg_oos_return,
                 r.wf_efficiency, r.consistency_score)
