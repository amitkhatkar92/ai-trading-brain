"""iios/investment/portfolio/risk/drawdown_forecast.py

Forward-looking drawdown probability and expected maximum loss over
specified horizons.
"""
from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List

from iios.investment.portfolio.risk.risk_types import (
    RiskPosition, portfolio_volatility, TRADING_DAYS,
)


@dataclass(frozen=True)
class DrawdownForecast:
    """Probabilistic drawdown forecast over 30d and 90d horizons."""

    result_id:    str   = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id: str   = ""

    # Expected maximum drawdown over forward horizons
    expected_max_dd_30d:    float = 0.0
    expected_max_dd_90d:    float = 0.0
    expected_max_dd_252d:   float = 0.0

    # Probability of drawdown exceeding thresholds (30d horizon)
    prob_dd_exceeds_5pct:   float = 0.0
    prob_dd_exceeds_10pct:  float = 0.0
    prob_dd_exceeds_20pct:  float = 0.0
    prob_dd_exceeds_30pct:  float = 0.0

    # Confidence in the forecast: lower with fewer positions
    forecast_confidence:    float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "expected_max_dd_30d":   round(self.expected_max_dd_30d, 4),
            "expected_max_dd_90d":   round(self.expected_max_dd_90d, 4),
            "expected_max_dd_252d":  round(self.expected_max_dd_252d, 4),
            "prob_dd_exceeds_5pct":  round(self.prob_dd_exceeds_5pct, 4),
            "prob_dd_exceeds_10pct": round(self.prob_dd_exceeds_10pct, 4),
            "prob_dd_exceeds_20pct": round(self.prob_dd_exceeds_20pct, 4),
            "forecast_confidence":   round(self.forecast_confidence, 4),
        }


def _prob_exceeds(horizon_vol: float, threshold: float) -> float:
    """Probability that max drawdown exceeds threshold.

    Under GBM, P(MaxDD > x) ≈ 2 × Φ(-x / σ_horizon).
    We use a simple normal approximation.
    """
    if horizon_vol <= 0:
        return 0.0
    z = threshold / horizon_vol
    # Approximation of 2 × (1 - Φ(z)) using erfc
    prob = math.erfc(z / math.sqrt(2.0))
    return round(min(prob, 1.0), 6)


def _mdd_from_vol(annual_vol: float, days: int) -> float:
    """Expected max drawdown proxy for given horizon."""
    if annual_vol <= 0 or days <= 1:
        return 0.0
    h_vol = annual_vol * math.sqrt(days / TRADING_DAYS)
    return min(1.0, h_vol * math.sqrt(2.0 * math.log(max(2, days))))


def forecast_drawdown(
    positions:    List[RiskPosition],
    portfolio_id: str = "",
) -> DrawdownForecast:
    if not positions:
        return DrawdownForecast(portfolio_id=portfolio_id)

    port_vol  = portfolio_volatility(positions)
    ann_vol   = port_vol * math.sqrt(TRADING_DAYS)
    vol_30d   = ann_vol * math.sqrt(30 / TRADING_DAYS)

    mdd_30  = _mdd_from_vol(ann_vol, 30)
    mdd_90  = _mdd_from_vol(ann_vol, 90)
    mdd_252 = _mdd_from_vol(ann_vol, 252)

    confidence = min(1.0, len(positions) / 10.0)

    return DrawdownForecast(
        portfolio_id           = portfolio_id,
        expected_max_dd_30d    = round(mdd_30, 6),
        expected_max_dd_90d    = round(mdd_90, 6),
        expected_max_dd_252d   = round(mdd_252, 6),
        prob_dd_exceeds_5pct   = _prob_exceeds(vol_30d, 0.05),
        prob_dd_exceeds_10pct  = _prob_exceeds(vol_30d, 0.10),
        prob_dd_exceeds_20pct  = _prob_exceeds(vol_30d, 0.20),
        prob_dd_exceeds_30pct  = _prob_exceeds(vol_30d, 0.30),
        forecast_confidence    = round(confidence, 4),
    )
