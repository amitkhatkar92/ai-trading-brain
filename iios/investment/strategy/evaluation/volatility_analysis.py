"""iios/investment/strategy/evaluation/volatility_analysis.py
Volatility metrics: realised vol, downside dev, risk-adjusted return.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List

from iios.investment.strategy.evaluation.equity_curve import EquityCurve
from iios.investment.strategy.evaluation.performance_statistics import (
    safe_mean, safe_std, percentile
)


@dataclass(frozen=True)
class VolatilityMetrics:
    annualized_volatility: float    = 0.0   # period vol × √periods_per_year
    downside_deviation:    float    = 0.0   # std of negative excess returns
    upside_deviation:      float    = 0.0   # std of positive excess returns
    up_down_vol_ratio:     float    = 0.0   # upside / downside dev
    risk_adjusted_return:  float    = 0.0   # annualised return / ann. vol
    semi_variance:         float    = 0.0   # variance of below-mean returns
    skewness:              float    = 0.0
    excess_kurtosis:       float    = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "annualized_volatility":  self.annualized_volatility,
            "downside_deviation":     self.downside_deviation,
            "upside_deviation":       self.upside_deviation,
            "up_down_vol_ratio":      self.up_down_vol_ratio,
            "risk_adjusted_return":   self.risk_adjusted_return,
            "semi_variance":          self.semi_variance,
            "skewness":               self.skewness,
            "excess_kurtosis":        self.excess_kurtosis,
        }


class VolatilityAnalyzer:

    def analyze(
        self,
        curve: EquityCurve,
        ann_return: float,
        rf_per_period: float = 0.0,
        periods_per_year: int = 252,
    ) -> VolatilityMetrics:
        if curve.is_empty():
            return VolatilityMetrics()

        returns = curve.period_returns
        n = len(returns)
        if n < 2:
            return VolatilityMetrics()

        period_vol = safe_std(returns)
        ann_vol = period_vol * math.sqrt(periods_per_year)

        # Downside / upside relative to rf
        excess = [r - rf_per_period for r in returns]
        neg_excess = [e for e in excess if e < 0.0]
        pos_excess = [e for e in excess if e >= 0.0]

        down_dev = (
            math.sqrt(sum(e ** 2 for e in neg_excess) / len(neg_excess))
            if neg_excess else 0.0
        )
        up_dev = (
            math.sqrt(sum(e ** 2 for e in pos_excess) / len(pos_excess))
            if pos_excess else 0.0
        )
        up_down = up_dev / down_dev if down_dev > 0.0 else 0.0

        risk_adj = ann_return / ann_vol if ann_vol > 0.0 else 0.0

        # Semi-variance (below mean)
        m = safe_mean(returns)
        below = [r for r in returns if r < m]
        semi_var = sum((r - m) ** 2 for r in below) / n if below else 0.0

        # Skewness
        if n >= 3 and period_vol > 0.0:
            skew = (
                sum(((r - m) / period_vol) ** 3 for r in returns) / n
            )
        else:
            skew = 0.0

        # Excess kurtosis
        if n >= 4 and period_vol > 0.0:
            kurt = (
                sum(((r - m) / period_vol) ** 4 for r in returns) / n - 3.0
            )
        else:
            kurt = 0.0

        return VolatilityMetrics(
            annualized_volatility=ann_vol,
            downside_deviation=down_dev * math.sqrt(periods_per_year),
            upside_deviation=up_dev * math.sqrt(periods_per_year),
            up_down_vol_ratio=up_down,
            risk_adjusted_return=risk_adj,
            semi_variance=semi_var,
            skewness=skew,
            excess_kurtosis=kurt,
        )
