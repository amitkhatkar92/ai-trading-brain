"""iios/investment/company/growth/forecast_engine.py
Orchestrates growth forecast generation.
"""
from __future__ import annotations

from typing import List, Optional

from iios.investment.company.growth.growth_profile import GrowthForecastProfile
from iios.investment.company.growth.forecast_assumptions import ForecastAssumptions
from iios.investment.company.growth.forecast_scenarios import generate_scenarios
from iios.investment.company.growth.forecast_confidence import compute_forecast_confidence


class ForecastEngine:
    """
    Generates forward-looking growth estimates (revenue and EPS)
    across bull, base, and bear scenarios.
    """

    def compute(
        self,
        revenue_cagr:       Optional[float] = None,   # historical revenue CAGR
        eps_cagr:           Optional[float] = None,   # historical EPS CAGR
        sustainability:     float = 50.0,             # 0-100
        eps_volatility:     Optional[float] = None,
        revenue_volatility: Optional[float] = None,
        history_depth:      int = 0,
        assumptions:        Optional[ForecastAssumptions] = None,
    ) -> GrowthForecastProfile:
        if assumptions is None:
            assumptions = ForecastAssumptions.default()

        explanation: List[str] = []
        profile = GrowthForecastProfile(forecast_horizon_years=assumptions.horizon_years)

        # ── Confidence ───────────────────────────────────────────────────────────
        confidence = compute_forecast_confidence(
            history_depth=history_depth,
            has_eps_cagr=eps_cagr is not None,
            has_revenue_cagr=revenue_cagr is not None,
            sustainability=sustainability,
            eps_volatility=eps_volatility,
            revenue_volatility=revenue_volatility,
        )
        profile.forecast_confidence = confidence

        if confidence < assumptions.min_confidence_to_forecast:
            explanation.append(
                f"Insufficient data confidence ({confidence:.2f}) to generate forecast"
            )
            profile.forecast_basis = "no_forecast"
            profile.explanation    = explanation
            return profile

        # ── Revenue scenarios ────────────────────────────────────────────────────
        bear_r, base_r, bull_r = generate_scenarios(
            historical_cagr=revenue_cagr,
            sustainability=sustainability,
            assumptions=assumptions,
            long_run_mean=assumptions.long_run_revenue_growth,
        )
        profile.base_revenue_growth = base_r
        profile.bull_revenue_growth = bull_r
        profile.bear_revenue_growth = bear_r

        # ── EPS scenarios ────────────────────────────────────────────────────────
        bear_e, base_e, bull_e = generate_scenarios(
            historical_cagr=eps_cagr,
            sustainability=sustainability,
            assumptions=assumptions,
            long_run_mean=assumptions.long_run_eps_growth,
        )
        profile.base_eps_growth = base_e
        profile.bull_eps_growth = bull_e
        profile.bear_eps_growth = bear_e

        # ── Basis ─────────────────────────────────────────────────────────────────
        profile.forecast_basis = "historical_extrapolation_with_mean_reversion"

        if base_r is not None:
            explanation.append(f"Base revenue growth forecast: {base_r:.1%}")
        if base_e is not None:
            explanation.append(f"Base EPS growth forecast: {base_e:.1%}")
        explanation.append(
            f"Forecast confidence: {confidence:.2f}, horizon: {assumptions.horizon_years}yr"
        )

        profile.explanation = explanation
        return profile
