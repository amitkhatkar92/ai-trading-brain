"""iios/investment/company/growth/forecast_scenarios.py
Bull/base/bear scenario generation for growth forecasts.
"""
from __future__ import annotations

from typing import Optional, Tuple

from iios.investment.company.growth.forecast_assumptions import ForecastAssumptions
from iios.investment.company.growth.growth_statistics import mean_reversion_estimate, clamp


def generate_scenarios(
    historical_cagr:   Optional[float],
    sustainability:    float,              # 0-100
    assumptions:       ForecastAssumptions,
    long_run_mean:     float,
) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    """
    Returns (bear, base, bull) growth estimates.
    Base uses mean-reversion blending.
    Bull/bear are symmetric multiplicative adjustments from base.
    """
    base = mean_reversion_estimate(
        historical_cagr=historical_cagr,
        long_run_mean=long_run_mean,
        weight=1.0 - assumptions.mean_reversion_weight,
    )
    if base is None:
        return None, None, None

    # Sustainability penalty — low sustainability compresses the base toward conservative
    sustainability_factor = clamp(sustainability / 100.0, 0.3, 1.0)
    base_adjusted = base * sustainability_factor + long_run_mean * (1.0 - sustainability_factor)

    bull = base_adjusted * assumptions.bull_multiplier
    bear = base_adjusted * assumptions.bear_multiplier

    return bear, base_adjusted, bull
