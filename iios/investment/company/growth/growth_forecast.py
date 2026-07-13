"""iios/investment/company/growth/growth_forecast.py
GrowthForecastProfile creation helper — thin wrapper over ForecastEngine.
"""
from __future__ import annotations

from typing import Optional

from iios.investment.company.growth.growth_profile import GrowthForecastProfile
from iios.investment.company.growth.forecast_engine import ForecastEngine
from iios.investment.company.growth.forecast_assumptions import ForecastAssumptions

# Expose a single convenience function for use by the primary engine
_engine = ForecastEngine()


def build_growth_forecast(
    revenue_cagr:       Optional[float] = None,
    eps_cagr:           Optional[float] = None,
    sustainability:     float = 50.0,
    eps_volatility:     Optional[float] = None,
    revenue_volatility: Optional[float] = None,
    history_depth:      int = 0,
    assumptions:        Optional[ForecastAssumptions] = None,
) -> GrowthForecastProfile:
    """Build a GrowthForecastProfile using the shared ForecastEngine instance."""
    return _engine.compute(
        revenue_cagr=revenue_cagr,
        eps_cagr=eps_cagr,
        sustainability=sustainability,
        eps_volatility=eps_volatility,
        revenue_volatility=revenue_volatility,
        history_depth=history_depth,
        assumptions=assumptions,
    )
