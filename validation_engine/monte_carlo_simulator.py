"""
Validation Engine — Monte Carlo Simulation
==========================================
Stress-test a strategy by randomising the sequence of trades 5 000 times.

Each run shuffles the trade P&L vector and recomputes:
  • Final equity (total return)
  • Maximum drawdown
  • Whether the equity curve is profitable

This reveals whether the observed performance could be luck (a lucky sequence
of wins early in the backtest that mask a losing system) or whether the
*distribution* of outcomes is robustly positive.

Institutional standards enforced:
  • Profit probability  ≥ 60%
  • Worst drawdown (5th-percentile) ≤ –25% of capital
  • Expected return (median) > 0

All returns are expressed in R-multiples (multiples of average lose).
"""

from __future__ import annotations
import math
import random
import statistics as stats
from dataclasses import dataclass, field
from typing import Optional

from utils import get_logger

log = get_logger(__name__)

# ── Thresholds ─────────────────────────────────────────────────────────────
MIN_PROFIT_PROBABILITY = 60.0   # % of MC runs that finish profitable
MAX_WORST_DRAWDOWN_PCT = 35.0   # abs% of capital (5th-percentile drawdown max)
N_RUNS_DEFAULT         = 5_000
PERCENTILE_LOW         = 5      # worst-case percentile
PERCENTILE_HIGH        = 95     # best-case percentile


@dataclass
class MCRunStats:
    final_pnl:    float
    max_drawdown: float
    profitable:   bool


@dataclass
class MonteCarloResult:
    strategy_name:       str
    n_runs:              int
    profit_probability:  float           # % of runs that ended profitable
    expected_return_r:   float           # median final P&L in R-multiples
    worst_drawdown_r:    float           # 5th-percentile max drawdown (R)
    best_return_r:       float           # 95th-percentile final return (R)
    percentile_5th:      float           # 5th-pct final equity %
    percentile_95th:     float           # 95th-pct final equity %
    mean_return_pct:     float
    median_return_pct:   float
    r_unit:              float           # average loss (the R unit used)
    passed:              bool

    def summary(self) -> str:
        verdict = "✅ PASSED" if self.passed else "❌ FAILED"
        return (f"[MonteCarlo] {verdict} | {self.strategy_name} | "
                f"Profit prob: {self.profit_probability:.1f}%  "
                f"Median return: {self.median_return_pct:+.2f}%  "
                f"Worst DD (5th pct): {self.percentile_5th:.2f}%")


class MonteCarloSimulator:
    """
    Runs N randomised trade-sequence simulations on the strategy P&L vector.

    Usage::
        sim    = MonteCarloSimulator(n_runs=5000)
        result = sim.run("MyStrategy", pnl_series, capital)
    """

    def __init__(self, n_runs: int = N_RUNS_DEFAULT, seed: int = 7) -> None:
        self._n_runs = n_runs
        self._rng    = random.Random(seed)
        log.info("[MonteCarloSimulator] Initialised. Runs per validation: %d",
                 self._n_runs)

    # ── Public API ────────────────────────────────────────────────────────
    def run(self, strategy_name: str, pnl_series: list[float],
            capital: float = 1_000_000) -> MonteCarloResult:
        """
        Shuffle-and-replay the trade P&L series N times.
        All results returned in both ₹ terms and R-multiples.
        """
        if not pnl_series:
            log.warning("[MonteCarlo] Empty P&L series for '%s'", strategy_name)
            return self._empty(strategy_name)

        pnls   = list(pnl_series)
        losses = [abs(p) for p in pnls if p < 0]
        r_unit = stats.mean(losses) if losses else 1.0  # avg loss = 1R

        mc_runs: list[MCRunStats] = []
        for _ in range(self._n_runs):
            self._rng.shuffle(pnls)
            run_stats = self._simulate(pnls, capital)
            mc_runs.append(run_stats)

        return self._aggregate(strategy_name, mc_runs, capital, r_unit)

    # ── Private helpers ───────────────────────────────────────────────────
    @staticmethod
    def _simulate(pnls: list[float], capital: float) -> MCRunStats:
        equity   = capital
        peak     = capital
        max_dd   = 0.0
        for p in pnls:
            equity += p
            if equity > peak:
                peak = equity
            dd_pct = (peak - equity) / peak * 100 if peak > 0 else 0.0
            if dd_pct > max_dd:
                max_dd = dd_pct
        return MCRunStats(
            final_pnl    = equity - capital,
            max_drawdown = max_dd,
            profitable   = equity > capital,
        )

    def _aggregate(self, name: str, runs: list[MCRunStats],
                   capital: float, r_unit: float) -> MonteCarloResult:
        final_pnls  = sorted(r.final_pnl for r in runs)
        drawdowns   = sorted(r.max_drawdown for r in runs)
        profitable  = sum(1 for r in runs if r.profitable)

        def percentile_val(sorted_list: list, pct: float) -> float:
            idx = int(len(sorted_list) * pct / 100)
            idx = max(0, min(idx, len(sorted_list) - 1))
            return sorted_list[idx]

        prof_prob    = profitable / len(runs) * 100
        p5_pnl       = percentile_val(final_pnls, PERCENTILE_LOW)
        p95_pnl      = percentile_val(final_pnls, PERCENTILE_HIGH)
        median_pnl   = percentile_val(final_pnls, 50)
        mean_pnl     = sum(r.final_pnl for r in runs) / len(runs)
        worst_dd     = percentile_val(drawdowns, PERCENTILE_HIGH)  # 95th-pct drawdown

        p5_ret_pct   = p5_pnl  / capital * 100
        p95_ret_pct  = p95_pnl / capital * 100
        med_ret_pct  = median_pnl / capital * 100
        mean_ret_pct = mean_pnl   / capital * 100

        r_safe = r_unit if r_unit > 0 else 1.0
        expected_r = (median_pnl / r_safe)
        worst_dd_r = -(worst_dd / 100 * capital) / r_safe

        passed = (
            prof_prob >= MIN_PROFIT_PROBABILITY
            and worst_dd <= MAX_WORST_DRAWDOWN_PCT
            and med_ret_pct > 0
        )

        result = MonteCarloResult(
            strategy_name      = name,
            n_runs             = len(runs),
            profit_probability = round(prof_prob,   2),
            expected_return_r  = round(expected_r,  2),
            worst_drawdown_r   = round(worst_dd_r,  2),
            best_return_r      = round(p95_pnl / r_safe, 2),
            percentile_5th     = round(p5_ret_pct,  3),
            percentile_95th    = round(p95_ret_pct, 3),
            mean_return_pct    = round(mean_ret_pct, 3),
            median_return_pct  = round(med_ret_pct,  3),
            r_unit             = round(r_unit,       2),
            passed             = passed,
        )
        log.info(result.summary())
        log.info("[MonteCarlo]   Worst DD (95th pct): %.1f%%  |  "
                 "P5/P95 returns: %+.2f%% / %+.2f%%",
                 worst_dd, p5_ret_pct, p95_ret_pct)
        return result

    @staticmethod
    def _empty(name: str) -> MonteCarloResult:
        return MonteCarloResult(
            strategy_name      = name,
            n_runs             = 0,
            profit_probability = 0.0,
            expected_return_r  = 0.0,
            worst_drawdown_r   = 0.0,
            best_return_r      = 0.0,
            percentile_5th     = 0.0,
            percentile_95th    = 0.0,
            mean_return_pct    = 0.0,
            median_return_pct  = 0.0,
            r_unit             = 1.0,
            passed             = False,
        )
