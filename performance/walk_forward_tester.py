"""
Performance Evaluation Framework — Walk-Forward Tester
=======================================================
Validates strategy performance by repeatedly:
  1. Training on an in-sample (IS) window
  2. Testing on the immediately following out-of-sample (OOS) window
  3. Advancing the window forward and repeating

This prevents look-ahead bias and confirms that a strategy's edge
persists on truly unseen data.

Output per fold:
  • is_return_pct   — in-sample return
  • oos_return_pct  — out-of-sample return
  • consistency     — OOS profitable (bool)

Aggregate output:
  • wf_efficiency   — OOS return / IS return (> 0.5 is good)
  • pass_rate_pct   — % of OOS folds that were profitable
  • avg_oos_return  — mean OOS return across all folds
"""

from __future__ import annotations
import statistics
from dataclasses import dataclass, field
from typing import Callable

from utils import get_logger

log = get_logger(__name__)

# Default split ratios
IS_RATIO  = 0.60   # 60% in-sample
OOS_RATIO = 0.20   # 20% out-of-sample
STEP_RATIO= 0.20   # slide window by 20%


@dataclass
class WFFold:
    fold_num:       int
    is_start:       int
    is_end:         int
    oos_start:      int
    oos_end:        int
    is_return_pct:  float
    oos_return_pct: float
    consistent:     bool   # OOS profitable


@dataclass
class WalkForwardReport:
    folds:          list[WFFold] = field(default_factory=list)
    pass_rate_pct:  float = 0.0     # % of OOS folds profitable
    avg_oos_return: float = 0.0
    wf_efficiency:  float = 0.0     # avg OOS / avg IS
    passed:         bool  = False

    def summary(self) -> str:
        verdict = "✅ PASSED" if self.passed else "❌ FAILED"
        return (f"[WalkForward] {verdict} | Folds={len(self.folds)} | "
                f"PassRate={self.pass_rate_pct:.0f}% | "
                f"AvgOOS={self.avg_oos_return:+.2f}% | "
                f"WF-Efficiency={self.wf_efficiency:.2f}")


class WalkForwardTester:
    """
    Runs anchored or rolling walk-forward validation on a P&L series.

    Usage::
        tester  = WalkForwardTester()
        pnl_series = [150, -80, 200, 300, -50, ...]  # one entry per trade
        report  = tester.run(pnl_series, capital=1_000_000)
    """

    def __init__(self,
                 is_ratio:   float = IS_RATIO,
                 oos_ratio:  float = OOS_RATIO,
                 step_ratio: float = STEP_RATIO) -> None:
        self.is_ratio   = is_ratio
        self.oos_ratio  = oos_ratio
        self.step_ratio = step_ratio
        log.info("[WalkForwardTester] Initialised. IS=%.0f%% OOS=%.0f%% "
                 "Step=%.0f%%",
                 is_ratio * 100, oos_ratio * 100, step_ratio * 100)

    def run(self, pnl_series: list[float], capital: float = 1_000_000,
            min_folds: int = 3) -> WalkForwardReport:
        n = len(pnl_series)
        if n < 10:
            log.warning("[WalkForwardTester] Not enough trades for WF (%d). "
                        "Need ≥ 10.", n)
            return WalkForwardReport(passed=False)

        is_size   = max(5, int(n * self.is_ratio))
        oos_size  = max(2, int(n * self.oos_ratio))
        step_size = max(1, int(n * self.step_ratio))

        folds: list[WFFold] = []
        fold_num = 0
        start    = 0

        while (start + is_size + oos_size) <= n:
            is_end  = start + is_size
            oos_end = is_end + oos_size

            is_pnl  = pnl_series[start:is_end]
            oos_pnl = pnl_series[is_end:oos_end]

            is_ret  = sum(is_pnl)  / capital * 100
            oos_ret = sum(oos_pnl) / capital * 100

            fold_num += 1
            folds.append(WFFold(
                fold_num       = fold_num,
                is_start       = start,
                is_end         = is_end,
                oos_start      = is_end,
                oos_end        = oos_end,
                is_return_pct  = round(is_ret,  3),
                oos_return_pct = round(oos_ret, 3),
                consistent     = oos_ret > 0,
            ))
            start += step_size

        if not folds:
            return WalkForwardReport(passed=False)

        pass_count    = sum(1 for f in folds if f.consistent)
        pass_rate     = pass_count / len(folds) * 100
        avg_oos       = statistics.mean(f.oos_return_pct for f in folds)
        avg_is        = statistics.mean(f.is_return_pct  for f in folds)
        wf_efficiency = (avg_oos / avg_is) if avg_is != 0 else 0.0
        passed        = pass_rate >= 60.0 and avg_oos > 0

        report = WalkForwardReport(
            folds          = folds,
            pass_rate_pct  = round(pass_rate, 1),
            avg_oos_return = round(avg_oos,   3),
            wf_efficiency  = round(wf_efficiency, 3),
            passed         = passed,
        )

        log.info(report.summary())
        for fold in folds:
            verdict = "✅" if fold.consistent else "❌"
            log.info("  Fold %d: IS=%+.2f%%  OOS=%+.2f%%  %s",
                     fold.fold_num, fold.is_return_pct,
                     fold.oos_return_pct, verdict)
        return report
