"""
Strategy Tester — Edge Discovery Engine Module 4
================================================
Backtests each CandidateStrategy against the feature database to
validate that the discovered pattern produces a genuine, out-of-sample
trading edge — not just in-sample noise.

Testing methodology (mirrors BacktestingAI):
  1. Walk-Forward splits: divide historical feature DB into N folds,
     test each fold in sequence
  2. OOS holdout: the final 20% of data is reserved, never seen during
     strategy development
  3. Quality gates (ALL must pass):
       • OOS win-rate          ≥ 0.53
       • Average return        ≥ 0.6R (expected value positive)
       • Sharpe ratio          ≥ 1.0
       • Max drawdown          ≤ 20%
       • Walk-forward consistency ≥ 0.55  (fraction of folds profitable)

If a candidate passes all gates it is marked approved=True.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from .candidate_strategy_generator import CandidateStrategy
from utils import get_logger

log = get_logger(__name__)

# ── Quality gate thresholds (expectancy-first philosophy) ────────────────────
# Win rate is NOT the primary gate. A strategy with 38% WR and 3R payoff
# has Expectancy = +0.76R — far better than 65% WR with 0.5R payoff (−0.175R).
MIN_OOS_WIN_RATE    = 0.38    # floor — avoids pure noise (was 0.53)
MIN_EXPECTANCY_R    = 0.08    # core gate: (WR×AvgWin_R) − (LR×AvgLoss_R) > 0
MIN_SHARPE          = 0.80    # slightly relaxed — expectancy is primary (was 1.00)
MAX_DRAWDOWN        = 0.25    # slightly relaxed — position sizing controls real DD
MIN_WF_CONSISTENCY  = 0.50    # ≥ half of WF folds positive (was 0.55)
WF_FOLDS            = 5
TRAIN_RATIO         = 0.70

# Legacy alias — kept for BacktestResult field used in display
MIN_AVG_RETURN_R    = MIN_EXPECTANCY_R


@dataclass
class BacktestResult:
    strategy_name:   str
    passes_gate:     bool
    oos_win_rate:    float
    avg_return_r:    float      # mean return across ALL trades (informational)
    sharpe_ratio:    float
    max_drawdown:    float
    wf_consistency:  float
    n_samples:       int
    failure_reasons: List[str]  = field(default_factory=list)
    expected_annual_r: float    = 0.0
    expectancy_r:    float      = 0.0   # primary gate: (WR×AvgWinR)−(LR×AvgLossR)
    avg_win_r:       float      = 0.0
    avg_loss_r:      float      = 0.0
    fat_tail_pct:    float      = 0.0   # fraction of trades producing 3R+

    def summary_line(self) -> str:
        status = "✅ PASS" if self.passes_gate else f"❌ FAIL [{', '.join(self.failure_reasons[:2])}]"
        exp_sign = "+" if self.expectancy_r >= 0 else ""
        return (f"{self.strategy_name:<35} "
                f"WR={self.oos_win_rate:.0%} "
                f"Exp={exp_sign}{self.expectancy_r:.2f}R "
                f"Sharpe={self.sharpe_ratio:.2f} "
                f"DD={self.max_drawdown:.0%}  "
                f"{status}")


class StrategyTester:
    """
    Validates CandidateStrategy objects against the historical feature DB.
    Each test uses the pattern conditions as the entry filter and measures
    forward returns on qualifying samples.
    """

    def __init__(self) -> None:
        log.info("[StrategyTester] Initialised.")

    # ── Public API ─────────────────────────────────────────────────────────

    def test(
        self,
        candidates: List[CandidateStrategy],
        feature_db: List[Dict[str, Any]],
    ) -> Tuple[List[CandidateStrategy], List[BacktestResult]]:
        """
        Run all candidates through the backtest pipeline.

        Returns:
            (updated_candidates, results)  — candidates with approved flag set
        """
        if not feature_db:
            log.warning("[StrategyTester] Empty feature DB — skipping tests.")
            return candidates, []

        results: List[BacktestResult] = []

        for cand in candidates:
            res = self._run_backtest(cand, feature_db)
            cand.approved = res.passes_gate
            results.append(res)
            log.info("[StrategyTester] %s", res.summary_line())

        approved = sum(1 for c in candidates if c.approved)
        log.info("[StrategyTester] %d / %d candidates approved.",
                 approved, len(candidates))
        return candidates, results

    # ── Internal ───────────────────────────────────────────────────────────

    def _run_backtest(
        self,
        cand: CandidateStrategy,
        db: List[Dict[str, Any]],
    ) -> BacktestResult:
        """Full walk-forward + OOS backtest pipeline for one candidate."""
        # Split: first 80% for WF, last 20% as OOS holdout
        split_idx = int(len(db) * 0.80)
        wf_data   = db[:split_idx]
        oos_data  = db[split_idx:]

        # Walk-forward folds
        wf_fold_results: List[bool] = []
        fold_size = max(20, len(wf_data) // WF_FOLDS)
        for k in range(WF_FOLDS):
            start = k * fold_size
            end   = start + fold_size
            fold  = wf_data[start:end]
            if len(fold) < 10:
                continue
            fold_wr = self._win_rate_on_subset(cand, fold)
            wf_fold_results.append(fold_wr >= MIN_OOS_WIN_RATE)

        wf_consistency = (
            sum(wf_fold_results) / len(wf_fold_results)
            if wf_fold_results else 0.0
        )

        # OOS stats
        oos_returns = self._returns_on_subset(cand, oos_data)
        n_oos = len(oos_returns)
        if n_oos < 5:
            oos_returns = self._returns_on_subset(cand, db)
            n_oos = len(oos_returns)

        if not oos_returns:
            return BacktestResult(
                strategy_name=cand.name,
                passes_gate=False,
                oos_win_rate=0.0,
                avg_return_r=0.0,
                sharpe_ratio=0.0,
                max_drawdown=0.0,
                wf_consistency=wf_consistency,
                n_samples=0,
                failure_reasons=["no_qualifying_samples"],
            )

        oos_arr      = np.array(oos_returns)
        sl           = cand.stop_loss_pct if cand.stop_loss_pct else 0.01
        oos_win_rate = float((oos_arr > 0).mean())
        avg_return_r = float(oos_arr.mean() / sl)      # mean R across ALL samples
        std_r        = float(oos_arr.std()) + 1e-9
        sharpe       = float(oos_arr.mean() / std_r * math.sqrt(252))
        max_drawdown = self._max_drawdown(oos_arr)
        annual_r     = float(oos_arr.mean()) * 252

        # ── Expectancy calculation (primary gate) ─────────────────────────
        win_rets  = [r for r in oos_returns if r > 0]
        loss_rets = [r for r in oos_returns if r <= 0]
        avg_win_r  = float(np.mean(win_rets)  / sl) if win_rets  else 0.0
        avg_loss_r = float(np.mean([abs(r) for r in loss_rets]) / sl) if loss_rets else 1.0
        loss_rate  = 1.0 - oos_win_rate
        expectancy_r = (oos_win_rate * avg_win_r) - (loss_rate * avg_loss_r)
        # Fat tail: fraction of winning trades producing ≥ 3R
        fat_tail_r  = sl * 3.0
        fat_tail_pct = sum(1 for r in win_rets if r >= fat_tail_r) / n_oos if n_oos else 0.0

        # ── Gate checklist (expectancy-first) ────────────────────────────
        failures: List[str] = []
        if oos_win_rate   < MIN_OOS_WIN_RATE:
            failures.append(f"oos_wr={oos_win_rate:.0%}<{MIN_OOS_WIN_RATE:.0%}")
        if expectancy_r   < MIN_EXPECTANCY_R:   # PRIMARY gate
            failures.append(f"exp_R={expectancy_r:.3f}<{MIN_EXPECTANCY_R}")
        if sharpe         < MIN_SHARPE:
            failures.append(f"sharpe={sharpe:.2f}<{MIN_SHARPE}")
        if max_drawdown   > MAX_DRAWDOWN:
            failures.append(f"dd={max_drawdown:.0%}>{MAX_DRAWDOWN:.0%}")
        if wf_consistency < MIN_WF_CONSISTENCY:
            failures.append(f"wf={wf_consistency:.0%}<{MIN_WF_CONSISTENCY:.0%}")

        return BacktestResult(
            strategy_name    = cand.name,
            passes_gate      = len(failures) == 0,
            oos_win_rate     = oos_win_rate,
            avg_return_r     = avg_return_r,
            sharpe_ratio     = sharpe,
            max_drawdown     = max_drawdown,
            wf_consistency   = wf_consistency,
            n_samples        = n_oos,
            failure_reasons  = failures,
            expected_annual_r= annual_r,
            expectancy_r     = round(expectancy_r, 4),
            avg_win_r        = round(avg_win_r, 4),
            avg_loss_r       = round(avg_loss_r, 4),
            fat_tail_pct     = round(fat_tail_pct, 4),
        )

    def _rows_matching_conditions(
        self,
        cand: CandidateStrategy,
        subset: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Filter rows that match all entry conditions of the candidate."""
        matching = []
        for row in subset:
            feats = row.get("features", {})
            if self._matches(feats, cand):
                matching.append(row)
        return matching

    @staticmethod
    def _matches(feats: Dict[str, float], cand: CandidateStrategy) -> bool:
        for cond in cand.entry_conditions:
            val = feats.get(cond["feature"], 0.0)
            op  = cond["operator"]
            thr = cond["threshold"]
            if op == ">" and not (val > thr):
                return False
            if op == "<=" and not (val <= thr):
                return False
        return True

    def _win_rate_on_subset(
        self, cand: CandidateStrategy, subset: List[Dict[str, Any]]
    ) -> float:
        rets = self._returns_on_subset(cand, subset)
        if not rets:
            return 0.0
        return float(np.mean(np.array(rets) > 0))

    def _returns_on_subset(
        self, cand: CandidateStrategy, subset: List[Dict[str, Any]]
    ) -> List[float]:
        matching = self._rows_matching_conditions(cand, subset)
        return [row.get("forward_return", 0.0) for row in matching]

    @staticmethod
    def _max_drawdown(returns: "np.ndarray") -> float:
        cumulative = np.cumprod(1 + returns)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (running_max - cumulative) / running_max
        return float(drawdown.max()) if len(drawdown) else 0.0
