"""
risk_exposure_engine.py — iios.risk.assessment
================================================
Exposure analysis engine — gross, net, long/short breakdown.

C11 Risk Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .constants import VERSION
from .exceptions import RiskCalculationError
from .risk_assessment_response import ExposureReport


class RiskExposureEngine:
    """
    Exposure analysis engine.

    Calculates gross exposure, net exposure, long/short breakdown,
    and per-position exposure contributions.

    All methods are pure functions.  No policy evaluation.  No execution.
    """

    VERSION: str = VERSION

    # ------------------------------------------------------------------
    # Core exposure calculations
    # ------------------------------------------------------------------

    def calculate_gross_exposure(
        self,
        positions:       Dict[str, float],
        portfolio_value: float,
    ) -> float:
        """
        Gross exposure = sum of absolute position values.

        Gross exposure > portfolio_value indicates leverage.
        """
        return sum(abs(w) * portfolio_value for w in positions.values())

    def calculate_net_exposure(
        self,
        positions:       Dict[str, float],
        portfolio_value: float,
    ) -> float:
        """
        Net exposure = (long exposure) − (short exposure).
        """
        long_exp  = sum(w  * portfolio_value for w in positions.values() if w > 0)
        short_exp = sum(abs(w) * portfolio_value for w in positions.values() if w < 0)
        return long_exp - short_exp

    def calculate_leverage(
        self,
        positions:       Dict[str, float],
        portfolio_value: float,
    ) -> float:
        """Leverage ratio = gross exposure / portfolio value."""
        if portfolio_value <= 0:
            return 0.0
        return self.calculate_gross_exposure(positions, portfolio_value) / portfolio_value

    def calculate_net_exposure_pct(
        self,
        positions:       Dict[str, float],
        portfolio_value: float,
    ) -> float:
        """Net exposure as a fraction of portfolio value."""
        if portfolio_value <= 0:
            return 0.0
        return self.calculate_net_exposure(positions, portfolio_value) / portfolio_value

    # ------------------------------------------------------------------
    # Top exposures
    # ------------------------------------------------------------------

    def top_exposures(
        self,
        positions:       Dict[str, float],
        portfolio_value: float,
        n:               int = 5,
    ) -> List[Tuple[str, float]]:
        """
        Return the top-N positions by absolute exposure, sorted descending.
        """
        exposures = [
            (pos_id, abs(w) * portfolio_value)
            for pos_id, w in positions.items()
        ]
        exposures.sort(key=lambda x: x[1], reverse=True)
        return exposures[:n]

    # ------------------------------------------------------------------
    # Capital at risk
    # ------------------------------------------------------------------

    def calculate_capital_at_risk(
        self,
        portfolio_value:  float,
        var_95:           float,
        available_capital: float,
    ) -> Dict[str, float]:
        """
        Capital at risk metrics.

        Returns dict with:
          - capital_at_risk: VaR as fraction of capital
          - capital_buffer:  available_capital − var_95
          - capital_utilisation: var_95 / available_capital
        """
        if available_capital <= 0:
            return {"capital_at_risk": 0.0, "capital_buffer": 0.0, "capital_utilisation": 0.0}
        return {
            "capital_at_risk":     var_95,
            "capital_buffer":      available_capital - var_95,
            "capital_utilisation": var_95 / available_capital,
        }

    # ------------------------------------------------------------------
    # Report builder
    # ------------------------------------------------------------------

    def build_exposure_report(
        self,
        assessment_id:   str,
        portfolio_id:    str,
        portfolio_value: float,
        positions:       Dict[str, float],
    ) -> ExposureReport:
        """Build a complete :class:`~.risk_assessment_response.ExposureReport`."""
        if portfolio_value <= 0:
            raise RiskCalculationError(
                f"Portfolio value must be positive, got {portfolio_value}",
                engine="ExposureEngine",
            )
        return ExposureReport.create(
            assessment_id   = assessment_id,
            portfolio_id    = portfolio_id,
            portfolio_value = portfolio_value,
            positions       = positions,
        )
