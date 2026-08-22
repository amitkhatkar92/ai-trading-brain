"""
risk_expected_shortfall_engine.py — iios.risk.assessment
==========================================================
Expected Shortfall (CVaR) calculation engine.

ES = E[Loss | Loss > VaR_α]

All calculations are deterministic.

C11 Risk Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import math
import statistics
from typing import List

from .constants import (
    DEFAULT_CONFIDENCE_LEVEL,
    MIN_RETURNS_FOR_VAR,
    VERSION,
)
from .exceptions import RiskCalculationError
from .risk_assessment_response import ExpectedShortfallReport
from .risk_var_engine import RiskVaREngine, _z_score


class RiskExpectedShortfallEngine:
    """
    Expected Shortfall (Conditional VaR) calculation engine.

    ES is the expected loss given that the loss exceeds VaR at the
    specified confidence level.  ES ≥ VaR always holds, making it
    a coherent risk measure.
    """

    VERSION: str = VERSION

    def __init__(self) -> None:
        self._var_engine = RiskVaREngine()

    # ------------------------------------------------------------------
    # Historical simulation ES
    # ------------------------------------------------------------------

    def calculate_historical_es(
        self,
        returns:          List[float],
        portfolio_value:  float,
        confidence_level: float = DEFAULT_CONFIDENCE_LEVEL,
    ) -> float:
        """
        Historical simulation Expected Shortfall.

        Averages losses strictly beyond the VaR quantile.

        Returns 0.0 when fewer than :data:`~.constants.MIN_RETURNS_FOR_VAR`
        observations are available.
        """
        if len(returns) < MIN_RETURNS_FOR_VAR:
            return 0.0
        sorted_r  = sorted(returns)
        cutoff    = max(1, int(len(sorted_r) * (1.0 - confidence_level)))
        tail      = sorted_r[:cutoff]
        if not tail:
            return 0.0
        es_pct = -sum(tail) / len(tail)
        return max(0.0, portfolio_value * es_pct)

    # ------------------------------------------------------------------
    # Parametric ES
    # ------------------------------------------------------------------

    def calculate_parametric_es(
        self,
        returns:          List[float],
        portfolio_value:  float,
        confidence_level: float = DEFAULT_CONFIDENCE_LEVEL,
    ) -> float:
        """
        Parametric ES assuming normally distributed returns.

        ES = portfolio × (σ × φ(z) / (1 − α) − μ)

        where φ is the standard normal PDF and z is the quantile.
        """
        if len(returns) < 2:
            return 0.0
        mu    = statistics.mean(returns)
        sigma = statistics.stdev(returns)
        z     = _z_score(confidence_level)
        # Standard normal PDF: φ(z) = (1/√2π)·e^(−z²/2)
        phi_z  = math.exp(-0.5 * z * z) / math.sqrt(2 * math.pi)
        alpha  = 1.0 - confidence_level
        es_pct = max(0.0, sigma * phi_z / alpha - mu)
        return max(0.0, portfolio_value * es_pct)

    # ------------------------------------------------------------------
    # Maximum drawdown
    # ------------------------------------------------------------------

    def calculate_max_drawdown(self, returns: List[float]) -> float:
        """
        Maximum drawdown from a cumulative return series.

        Returns the peak-to-trough decline as a positive fraction.
        """
        if len(returns) < 2:
            return 0.0
        peak     = 1.0
        value    = 1.0
        max_dd   = 0.0
        for r in returns:
            value = value * (1.0 + r)
            if value > peak:
                peak = value
            dd = (peak - value) / peak if peak > 0 else 0.0
            if dd > max_dd:
                max_dd = dd
        return max_dd

    # ------------------------------------------------------------------
    # Full report builder
    # ------------------------------------------------------------------

    def build_es_report(
        self,
        assessment_id:    str,
        portfolio_id:     str,
        returns:          List[float],
        portfolio_value:  float,
        confidence_level: float = DEFAULT_CONFIDENCE_LEVEL,
    ) -> ExpectedShortfallReport:
        """Build a complete :class:`~.risk_assessment_response.ExpectedShortfallReport`."""
        if portfolio_value <= 0:
            raise RiskCalculationError(
                f"Portfolio value must be positive, got {portfolio_value}",
                engine="ESEngine",
            )
        hist_es  = self.calculate_historical_es(returns, portfolio_value, confidence_level)
        param_es = self.calculate_parametric_es(returns, portfolio_value, confidence_level)
        var_ref  = self._var_engine.calculate_historical_var(
            returns, portfolio_value, confidence_level
        )
        return ExpectedShortfallReport.create(
            assessment_id    = assessment_id,
            portfolio_id     = portfolio_id,
            confidence_level = confidence_level,
            es_historical    = hist_es,
            portfolio_value  = portfolio_value,
            returns_used     = len(returns),
            es_parametric    = param_es,
            var_reference    = var_ref,
        )
