"""iios/investment/strategy/evaluation/tail_risk.py
Tail-risk metrics: VaR, Expected Shortfall (CVaR), tail ratio.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List

from iios.investment.strategy.evaluation.equity_curve import EquityCurve
from iios.investment.strategy.evaluation.performance_statistics import (
    percentile, safe_mean
)


@dataclass(frozen=True)
class TailRiskMetrics:
    var_95: float             = 0.0   # Value-at-Risk at 95 % confidence
    var_99: float             = 0.0   # Value-at-Risk at 99 % confidence
    cvar_95: float            = 0.0   # Expected Shortfall at 95 % (CVaR)
    cvar_99: float            = 0.0   # Expected Shortfall at 99 %
    tail_ratio: float         = 0.0   # 95th pct / abs(5th pct)
    gain_to_pain: float       = 0.0   # sum(returns) / sum(abs(neg returns))
    worst_return: float       = 0.0
    best_return: float        = 0.0
    pct_negative_periods: float = 0.0 # fraction of periods with negative return

    def to_dict(self) -> Dict[str, Any]:
        return {
            "var_95":                self.var_95,
            "var_99":                self.var_99,
            "cvar_95":               self.cvar_95,
            "cvar_99":               self.cvar_99,
            "tail_ratio":            self.tail_ratio,
            "gain_to_pain":          self.gain_to_pain,
            "worst_return":          self.worst_return,
            "best_return":           self.best_return,
            "pct_negative_periods":  self.pct_negative_periods,
        }


class TailRiskAnalyzer:

    def analyze(self, curve: EquityCurve) -> TailRiskMetrics:
        if curve.is_empty():
            return TailRiskMetrics()

        returns = curve.period_returns
        n = len(returns)
        if n < 5:
            return TailRiskMetrics()

        sorted_r = sorted(returns)

        # VaR: percentile loss (negative value = loss)
        var95 = percentile(sorted_r, 5.0)   # 5th percentile
        var99 = percentile(sorted_r, 1.0)   # 1st percentile

        # CVaR (Expected Shortfall): mean of tail beyond VaR
        tail95 = [r for r in sorted_r if r <= var95]
        tail99 = [r for r in sorted_r if r <= var99]
        cvar95 = safe_mean(tail95) if tail95 else var95
        cvar99 = safe_mean(tail99) if tail99 else var99

        # Tail ratio
        p95 = percentile(sorted_r, 95.0)
        p5 = abs(percentile(sorted_r, 5.0))
        tail_ratio = abs(p95) / p5 if p5 > 0.0 else 0.0

        # Gain-to-pain
        total = sum(returns)
        pain = sum(abs(r) for r in returns if r < 0.0)
        g2p = total / pain if pain > 0.0 else (math.inf if total > 0.0 else 0.0)
        if not math.isfinite(g2p):
            g2p = 0.0

        neg_count = sum(1 for r in returns if r < 0.0)

        return TailRiskMetrics(
            var_95=var95,
            var_99=var99,
            cvar_95=cvar95,
            cvar_99=cvar99,
            tail_ratio=tail_ratio,
            gain_to_pain=g2p,
            worst_return=sorted_r[0],
            best_return=sorted_r[-1],
            pct_negative_periods=neg_count / n,
        )
