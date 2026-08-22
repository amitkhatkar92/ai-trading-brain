"""
risk_var_engine.py — iios.risk.assessment
==========================================
Value at Risk (VaR) calculation engine.

Implements:
  - Historical simulation VaR
  - Parametric (variance-covariance) VaR
  - Component VaR

All calculations are deterministic and explainable.

C11 Risk Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import math
import statistics
from typing import Any, Dict, List, Optional

from .constants import (
    DEFAULT_CONFIDENCE_LEVEL,
    DEFAULT_EWMA_DECAY,
    DEFAULT_VAR_CONFIDENCE_LEVELS,
    DEFAULT_VAR_HORIZON_DAYS,
    MIN_RETURNS_FOR_VAR,
    VERSION,
)
from .exceptions import RiskCalculationError
from .risk_assessment_response import VaRReport

# Standard normal quantiles — deterministic lookup table
_Z_SCORES: Dict[float, float] = {
    0.90: 1.2816,
    0.95: 1.6449,
    0.99: 2.3263,
    0.999: 3.0902,
}


def _z_score(confidence: float) -> float:
    """Return the standard normal quantile for the given confidence level."""
    if confidence in _Z_SCORES:
        return _Z_SCORES[confidence]
    # Fallback: linear interpolation between known values
    # This is deterministic and avoids scipy dependency
    lower_conf = max(c for c in _Z_SCORES if c <= confidence) if any(c <= confidence for c in _Z_SCORES) else 0.90
    return _Z_SCORES[lower_conf]


class RiskVaREngine:
    """
    Value at Risk calculation engine.

    Supports historical simulation and parametric (normal distribution)
    approaches.  All methods are pure functions of their inputs —
    no state is mutated, results are fully reproducible.
    """

    VERSION: str = VERSION

    # ------------------------------------------------------------------
    # Historical simulation VaR
    # ------------------------------------------------------------------

    def calculate_historical_var(
        self,
        returns:          List[float],
        portfolio_value:  float,
        confidence_level: float = DEFAULT_CONFIDENCE_LEVEL,
        horizon_days:     int   = DEFAULT_VAR_HORIZON_DAYS,
    ) -> float:
        """
        Historical simulation VaR (absolute currency amount).

        Sorts the return series, takes the percentile at (1-confidence),
        and scales by sqrt(horizon) per the square-root-of-time rule.

        Returns 0.0 when fewer than :data:`~.constants.MIN_RETURNS_FOR_VAR`
        observations are available.
        """
        if len(returns) < MIN_RETURNS_FOR_VAR:
            return 0.0
        sorted_r = sorted(returns)
        idx      = max(0, int(len(sorted_r) * (1.0 - confidence_level)) - 1)
        daily_var_pct   = -sorted_r[idx]
        scaled_var_pct  = daily_var_pct * math.sqrt(horizon_days)
        return max(0.0, portfolio_value * scaled_var_pct)

    # ------------------------------------------------------------------
    # Parametric VaR
    # ------------------------------------------------------------------

    def calculate_parametric_var(
        self,
        returns:          List[float],
        portfolio_value:  float,
        confidence_level: float = DEFAULT_CONFIDENCE_LEVEL,
        horizon_days:     int   = DEFAULT_VAR_HORIZON_DAYS,
    ) -> float:
        """
        Parametric (variance-covariance) VaR assuming normal returns.

        VaR = portfolio_value × (−μ + z × σ) × sqrt(horizon)

        Returns 0.0 when fewer than 2 returns are available.
        """
        if len(returns) < 2:
            return 0.0
        mu    = statistics.mean(returns)
        sigma = statistics.stdev(returns)
        z     = _z_score(confidence_level)
        daily_var_pct = max(0.0, -mu + z * sigma)
        scaled        = daily_var_pct * math.sqrt(horizon_days)
        return max(0.0, portfolio_value * scaled)

    # ------------------------------------------------------------------
    # Component VaR
    # ------------------------------------------------------------------

    def calculate_component_var(
        self,
        positions:        Dict[str, float],
        portfolio_value:  float,
        portfolio_var:    float,
    ) -> Dict[str, float]:
        """
        Allocate portfolio VaR proportionally to position weights.

        This is a simplified marginal/component allocation (assuming
        equal correlation across positions).  Returns a dict of
        position_id → component VaR amount.
        """
        if portfolio_value <= 0 or not positions:
            return {}
        total_abs_weight = sum(abs(w) for w in positions.values())
        if total_abs_weight == 0:
            return {}
        return {
            pos_id: portfolio_var * abs(weight) / total_abs_weight
            for pos_id, weight in positions.items()
        }

    # ------------------------------------------------------------------
    # EWMA-adjusted VaR
    # ------------------------------------------------------------------

    def calculate_ewma_vol(
        self,
        returns:    List[float],
        decay:      float = DEFAULT_EWMA_DECAY,
    ) -> float:
        """
        EWMA (Exponentially Weighted Moving Average) daily volatility.

        Uses the RiskMetrics standard decay factor (λ = 0.94 by default).
        Returns annualised volatility.
        """
        if len(returns) < 2:
            return 0.0
        ewma_var = returns[-1] ** 2
        for r in reversed(returns[:-1]):
            ewma_var = decay * ewma_var + (1.0 - decay) * r ** 2
        daily_vol = math.sqrt(ewma_var)
        return daily_vol * math.sqrt(252)  # annualised

    # ------------------------------------------------------------------
    # Full report builder
    # ------------------------------------------------------------------

    def build_var_report(
        self,
        assessment_id:    str,
        portfolio_id:     str,
        returns:          List[float],
        portfolio_value:  float,
        positions:        Dict[str, float],
        confidence_level: float = DEFAULT_CONFIDENCE_LEVEL,
        horizon_days:     int   = DEFAULT_VAR_HORIZON_DAYS,
    ) -> VaRReport:
        """Build a complete :class:`~.risk_assessment_response.VaRReport`."""
        if portfolio_value <= 0:
            raise RiskCalculationError(
                f"Portfolio value must be positive, got {portfolio_value}",
                engine="VaREngine",
            )
        hist_var  = self.calculate_historical_var(
            returns, portfolio_value, confidence_level, horizon_days
        )
        param_var = self.calculate_parametric_var(
            returns, portfolio_value, confidence_level, horizon_days
        )
        comp_var  = self.calculate_component_var(
            positions, portfolio_value, hist_var
        )
        return VaRReport.create(
            assessment_id    = assessment_id,
            portfolio_id     = portfolio_id,
            confidence_level = confidence_level,
            horizon_days     = horizon_days,
            historical_var   = hist_var,
            portfolio_value  = portfolio_value,
            returns_used     = len(returns),
            parametric_var   = param_var,
            component_var    = comp_var,
        )

    def calculate_multi_confidence_var(
        self,
        returns:         List[float],
        portfolio_value: float,
        horizon_days:    int = DEFAULT_VAR_HORIZON_DAYS,
    ) -> Dict[float, float]:
        """Calculate historical VaR at multiple standard confidence levels."""
        return {
            cl: self.calculate_historical_var(returns, portfolio_value, cl, horizon_days)
            for cl in DEFAULT_VAR_CONFIDENCE_LEVELS
        }
