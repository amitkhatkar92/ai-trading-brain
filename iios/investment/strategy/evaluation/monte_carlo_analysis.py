"""iios/investment/strategy/evaluation/monte_carlo_analysis.py
Bootstrap Monte Carlo over the trade PnL distribution.
Deterministic when seeded; defaults to random seed.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from iios.investment.strategy.evaluation.trade import Trade
from iios.investment.strategy.evaluation.performance_statistics import (
    safe_mean, safe_std, percentile, profit_factor
)

_DEFAULT_SIMULATIONS = 1000
_MIN_TRADES = 5


@dataclass(frozen=True)
class MonteCarloReport:
    n_simulations:   int   = 0
    n_trades:        int   = 0

    # Simulated distribution of Sharpe ratios
    sharpe_p5:       float = 0.0
    sharpe_p50:      float = 0.0
    sharpe_p95:      float = 0.0

    # Simulated distribution of max drawdowns
    max_dd_p5:       float = 0.0
    max_dd_p50:      float = 0.0
    max_dd_p95:      float = 0.0

    # Simulated distribution of total returns
    total_return_p5:  float = 0.0
    total_return_p50: float = 0.0
    total_return_p95: float = 0.0

    # Robustness
    pct_positive_return: float = 0.0   # fraction of sims with > 0 return
    pct_sharpe_above_1:  float = 0.0   # fraction of sims with Sharpe > 1.0
    robustness_score:    float = 0.0   # composite 0–1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "n_simulations":       self.n_simulations,
            "sharpe_p5":           self.sharpe_p5,
            "sharpe_p50":          self.sharpe_p50,
            "sharpe_p95":          self.sharpe_p95,
            "max_dd_p5":           self.max_dd_p5,
            "max_dd_p50":          self.max_dd_p50,
            "max_dd_p95":          self.max_dd_p95,
            "total_return_p50":    self.total_return_p50,
            "pct_positive_return": self.pct_positive_return,
            "pct_sharpe_above_1":  self.pct_sharpe_above_1,
            "robustness_score":    self.robustness_score,
        }


class MonteCarloAnalyzer:

    def __init__(
        self,
        n_simulations: int = _DEFAULT_SIMULATIONS,
        seed: Optional[int] = None,
    ) -> None:
        self._n_sims = n_simulations
        self._seed = seed

    def analyze(
        self,
        trades: List[Trade],
        rf_per_period: float = 0.0,
        periods_per_year: int = 252,
    ) -> MonteCarloReport:
        n = len(trades)
        if n < _MIN_TRADES:
            return MonteCarloReport(n_simulations=self._n_sims, n_trades=n)

        rng = random.Random(self._seed)
        returns = [t.pnl_pct for t in trades]

        sim_sharpes: List[float] = []
        sim_max_dds: List[float] = []
        sim_total_returns: List[float] = []

        for _ in range(self._n_sims):
            sim_returns = rng.choices(returns, k=n)

            # Build simulated equity curve
            equity = 1.0
            peak = 1.0
            max_dd = 0.0
            for r in sim_returns:
                equity *= (1.0 + r)
                peak = max(peak, equity)
                dd = (peak - equity) / peak
                max_dd = max(max_dd, dd)

            total_ret = equity - 1.0
            sr = self._sharpe(sim_returns, rf_per_period, periods_per_year)

            sim_sharpes.append(sr)
            sim_max_dds.append(max_dd)
            sim_total_returns.append(total_ret)

        sorted_sr = sorted(sim_sharpes)
        sorted_dd = sorted(sim_max_dds)
        sorted_ret = sorted(sim_total_returns)

        pct_positive = sum(1 for r in sim_total_returns if r > 0.0) / self._n_sims
        pct_sharpe1 = sum(1 for s in sim_sharpes if s > 1.0) / self._n_sims

        # Composite robustness: blend pct_positive and pct_sharpe>1
        robustness = 0.6 * pct_positive + 0.4 * pct_sharpe1

        return MonteCarloReport(
            n_simulations=self._n_sims,
            n_trades=n,
            sharpe_p5=percentile(sorted_sr, 5.0),
            sharpe_p50=percentile(sorted_sr, 50.0),
            sharpe_p95=percentile(sorted_sr, 95.0),
            max_dd_p5=percentile(sorted_dd, 5.0),
            max_dd_p50=percentile(sorted_dd, 50.0),
            max_dd_p95=percentile(sorted_dd, 95.0),
            total_return_p5=percentile(sorted_ret, 5.0),
            total_return_p50=percentile(sorted_ret, 50.0),
            total_return_p95=percentile(sorted_ret, 95.0),
            pct_positive_return=pct_positive,
            pct_sharpe_above_1=pct_sharpe1,
            robustness_score=robustness,
        )

    @staticmethod
    def _sharpe(
        returns: List[float], rf: float, ppy: int
    ) -> float:
        excess = [r - rf for r in returns]
        m = safe_mean(excess)
        s = safe_std(excess)
        if s == 0.0:
            return 0.0
        return m / s * math.sqrt(ppy)
