"""iios/investment/portfolio/performance/performance_forecast.py

Forward-looking performance forecasting (conviction-based proxies).
"""
from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from iios.investment.portfolio.performance.performance_types import (
    RISK_FREE_RATE_ANNUAL, TRADING_DAYS, PerformancePosition,
    portfolio_expected_return, portfolio_vol_proxy,
)


@dataclass(frozen=True)
class PerformanceForecast:
    """Forward-looking portfolio performance forecast."""

    result_id:           str   = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:        str   = ""

    # Expected returns
    expected_return_30d: float = 0.0
    expected_return_90d: float = 0.0
    expected_return_1y:  float = 0.0

    # Probability of positive return
    prob_positive_30d:   float = 0.0
    prob_positive_90d:   float = 0.0
    prob_positive_1y:    float = 0.0

    # Expected ratios
    expected_sharpe:     float = 0.0
    expected_vol:        float = 0.0

    confidence_score:    float = 0.0   # based on conviction stability
    is_reliable:         bool  = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "expected_return_30d": round(self.expected_return_30d, 4),
            "expected_return_90d": round(self.expected_return_90d, 4),
            "expected_return_1y":  round(self.expected_return_1y, 4),
            "prob_positive_30d":   round(self.prob_positive_30d, 4),
            "prob_positive_1y":    round(self.prob_positive_1y, 4),
            "expected_sharpe":     round(self.expected_sharpe, 4),
            "confidence_score":    round(self.confidence_score, 4),
        }


def forecast_performance(
    positions:         List[PerformancePosition],
    current_sharpe:    float = 0.0,
    portfolio_vol:     Optional[float] = None,
    portfolio_id:      str   = "",
) -> PerformanceForecast:
    """
    Estimate forward-looking performance metrics.

    All forecasts are conviction-based proxies — not market predictions.
    """
    if not positions:
        return PerformanceForecast(portfolio_id=portfolio_id)

    n   = len(positions)
    vol = portfolio_vol if portfolio_vol is not None else portfolio_vol_proxy(positions)
    if vol <= 0:
        vol = 0.10

    exp_annual = portfolio_expected_return(positions)
    if abs(exp_annual) < 1e-10:
        exp_annual = RISK_FREE_RATE_ANNUAL + 0.02   # minimal fallback

    # Period returns (simple scaling)
    ret_30d = exp_annual * (30 / 365)
    ret_90d = exp_annual * (90 / 365)
    ret_1y  = exp_annual

    # Vol scaled to period
    vol_30d = vol * math.sqrt(30 / 252)
    vol_90d = vol * math.sqrt(90 / 252)

    # Probability of positive return using log-normal approximation
    # P(R>0) ≈ Φ(μ/σ) for period horizon
    def _prob_pos(mean: float, sigma: float) -> float:
        if sigma <= 1e-10:
            return 1.0 if mean > 0 else 0.0
        z = mean / sigma
        return _cdf_approx(z)

    prob_30d = _prob_pos(ret_30d, vol_30d)
    prob_90d = _prob_pos(ret_90d, vol_90d)
    prob_1y  = _prob_pos(ret_1y, vol)

    # Expected Sharpe (blend current with forward expectation)
    exp_excess  = exp_annual - RISK_FREE_RATE_ANNUAL
    exp_sharpe  = exp_excess / vol if vol > 1e-10 else 0.0
    # Blend: 60% current, 40% expectation-based
    blended_sharpe = 0.60 * current_sharpe + 0.40 * exp_sharpe

    # Confidence: stability of conviction
    convictions = [p.conviction for p in positions]
    avg_conv    = sum(convictions) / n
    conv_std    = math.sqrt(sum((c - avg_conv) ** 2 for c in convictions) / n)
    confidence  = max(0.0, min(1.0, avg_conv * (1.0 - conv_std)))

    return PerformanceForecast(
        portfolio_id         = portfolio_id,
        expected_return_30d  = round(ret_30d, 4),
        expected_return_90d  = round(ret_90d, 4),
        expected_return_1y   = round(ret_1y, 4),
        prob_positive_30d    = round(prob_30d, 4),
        prob_positive_90d    = round(prob_90d, 4),
        prob_positive_1y     = round(prob_1y, 4),
        expected_sharpe      = round(blended_sharpe, 4),
        expected_vol         = round(vol, 4),
        confidence_score     = round(confidence, 4),
        is_reliable          = confidence >= 0.50 and n >= 5,
    )


def _cdf_approx(z: float) -> float:
    """
    Approximation of the standard normal CDF Φ(z).
    Abramowitz & Stegun approximation.
    """
    if z < -6:
        return 0.0
    if z > 6:
        return 1.0
    t = 1.0 / (1.0 + 0.2316419 * abs(z))
    poly = t * (0.319381530
         + t * (-0.356563782
         + t * (1.781477937
         + t * (-1.821255978
         + t *  1.330274429))))
    base = 1.0 - (1.0 / math.sqrt(2 * math.pi)) * math.exp(-0.5 * z * z) * poly
    return base if z >= 0 else 1.0 - base
