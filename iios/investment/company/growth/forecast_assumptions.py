"""iios/investment/company/growth/forecast_assumptions.py
Forecast assumption parameters.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class ForecastAssumptions:
    """
    Tunable parameters for growth forecasting.
    Callers can customise these per-company or sector.
    """
    horizon_years:          int   = 3         # forecast horizon
    mean_reversion_weight:  float = 0.40      # weight toward long-run mean (0-1)
    long_run_revenue_growth: float = 0.08     # long-run mean revenue growth assumption
    long_run_eps_growth:    float  = 0.10     # long-run mean EPS growth assumption
    bull_multiplier:        float = 1.35      # bull-case = base * bull_multiplier
    bear_multiplier:        float = 0.65      # bear-case = base * bear_multiplier
    min_confidence_to_forecast: float = 0.20  # below this confidence, don't forecast

    @classmethod
    def default(cls) -> "ForecastAssumptions":
        return cls()
