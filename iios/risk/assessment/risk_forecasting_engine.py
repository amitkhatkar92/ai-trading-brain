"""
risk_forecasting_engine.py — iios.risk.assessment
===================================================
EWMA-based risk forecasting engine.

Produces forward estimates of VaR, volatility, and return for multiple
time horizons using Exponentially Weighted Moving Average (EWMA).

C11 Risk Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import math
import statistics
from typing import Dict, List, Optional

from .constants import (
    DEFAULT_CONFIDENCE_LEVEL,
    DEFAULT_EWMA_DECAY,
    DEFAULT_RISK_FREE_RATE,
    FORECAST_HORIZON_DAYS,
    ForecastHorizon,
    VERSION,
)
from .exceptions import RiskForecastError
from .risk_assessment_response import RiskForecast
from .risk_var_engine import _z_score


class RiskForecastingEngine:
    """
    EWMA-based risk forecasting engine.

    Projects risk metrics across Day, Week, Month, and Quarter horizons.
    All calculations are deterministic and explainable.
    """

    VERSION: str = VERSION

    # ------------------------------------------------------------------
    # EWMA volatility forecast
    # ------------------------------------------------------------------

    def forecast_ewma_volatility(
        self,
        returns:    List[float],
        horizon_days: int,
        decay:      float = DEFAULT_EWMA_DECAY,
    ) -> float:
        """
        Forecast annualised volatility over a given horizon using EWMA.

        Applies square-root-of-time scaling for multi-day horizons.
        """
        if len(returns) < 2:
            return 0.0
        # Compute EWMA daily variance
        ewma_var = returns[-1] ** 2
        for r in reversed(returns[:-1]):
            ewma_var = decay * ewma_var + (1.0 - decay) * r ** 2
        daily_vol = math.sqrt(ewma_var)
        # Scale to horizon, then annualise
        horizon_vol = daily_vol * math.sqrt(horizon_days)
        annual_vol  = daily_vol * math.sqrt(252)
        return annual_vol

    # ------------------------------------------------------------------
    # Return forecast
    # ------------------------------------------------------------------

    def forecast_return(
        self,
        returns:      List[float],
        portfolio_value: float,
        horizon_days: int,
        decay:        float = DEFAULT_EWMA_DECAY,
    ) -> float:
        """
        EWMA-weighted expected return forecast over the horizon.

        Uses EWMA weights to give more importance to recent observations.
        Scales by sqrt(horizon) for multi-period estimates.
        """
        if not returns:
            return 0.0
        n      = len(returns)
        weights = [(1.0 - decay) * (decay ** i) for i in range(n)]
        total_w = sum(weights)
        if total_w == 0:
            return 0.0
        ewma_return = sum(w * r for w, r in zip(weights, reversed(returns))) / total_w
        return portfolio_value * ewma_return * horizon_days

    # ------------------------------------------------------------------
    # VaR forecast
    # ------------------------------------------------------------------

    def forecast_var(
        self,
        returns:          List[float],
        portfolio_value:  float,
        horizon_days:     int,
        confidence_level: float = DEFAULT_CONFIDENCE_LEVEL,
        decay:            float = DEFAULT_EWMA_DECAY,
    ) -> float:
        """
        Forward VaR forecast using EWMA volatility.

        VaR = portfolio_value × (z × σ_horizon − μ_horizon)
        """
        if len(returns) < 2:
            return 0.0
        ewma_var = returns[-1] ** 2
        for r in reversed(returns[:-1]):
            ewma_var = decay * ewma_var + (1.0 - decay) * r ** 2
        daily_vol     = math.sqrt(ewma_var)
        daily_mu      = statistics.mean(returns)
        horizon_vol   = daily_vol * math.sqrt(horizon_days)
        horizon_mu    = daily_mu * horizon_days
        z             = _z_score(confidence_level)
        var_pct       = max(0.0, -horizon_mu + z * horizon_vol)
        return portfolio_value * var_pct

    # ------------------------------------------------------------------
    # Single horizon forecast
    # ------------------------------------------------------------------

    def build_forecast(
        self,
        assessment_id:    str,
        portfolio_id:     str,
        returns:          List[float],
        portfolio_value:  float,
        horizon:          ForecastHorizon,
        confidence_level: float = DEFAULT_CONFIDENCE_LEVEL,
        decay:            float = DEFAULT_EWMA_DECAY,
    ) -> RiskForecast:
        """Build a :class:`~.risk_assessment_response.RiskForecast` for one horizon."""
        if portfolio_value <= 0:
            raise RiskForecastError(
                f"Portfolio value must be positive, got {portfolio_value}",
                horizon=horizon.value,
            )
        horizon_days = FORECAST_HORIZON_DAYS[horizon]
        fcast_var    = self.forecast_var(
            returns, portfolio_value, horizon_days, confidence_level, decay
        )
        fcast_vol    = self.forecast_ewma_volatility(returns, horizon_days, decay)
        fcast_ret    = self.forecast_return(returns, portfolio_value, horizon_days, decay)

        return RiskForecast.create(
            assessment_id       = assessment_id,
            portfolio_id        = portfolio_id,
            horizon             = horizon,
            horizon_days        = horizon_days,
            forecast_var        = fcast_var,
            forecast_volatility = fcast_vol,
            forecast_return     = fcast_ret,
            portfolio_value     = portfolio_value,
            ewma_decay          = decay,
        )

    # ------------------------------------------------------------------
    # All horizons
    # ------------------------------------------------------------------

    def build_all_forecasts(
        self,
        assessment_id:    str,
        portfolio_id:     str,
        returns:          List[float],
        portfolio_value:  float,
        confidence_level: float = DEFAULT_CONFIDENCE_LEVEL,
        decay:            float = DEFAULT_EWMA_DECAY,
    ) -> List[RiskForecast]:
        """Build forecasts for all four standard horizons."""
        return [
            self.build_forecast(
                assessment_id, portfolio_id, returns, portfolio_value,
                horizon, confidence_level, decay,
            )
            for horizon in ForecastHorizon
        ]
