"""
risk_score_engine.py — iios.risk.assessment
=============================================
Composite risk score engine (0–100).

C11 Risk Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from .constants import (
    RISK_SCORE_HIGH,
    RISK_SCORE_LOW,
    RISK_SCORE_MEDIUM,
    VERSION,
)


class RiskScoreComponents:
    """Breakdown of the composite risk score into contributing factors."""
    __slots__ = ("var_score", "concentration_score", "stress_score",
                 "limit_score", "total_score", "risk_band")

    def __init__(
        self,
        var_score:           float,
        concentration_score: float,
        stress_score:        float,
        limit_score:         float,
    ) -> None:
        self.var_score           = var_score
        self.concentration_score = concentration_score
        self.stress_score        = stress_score
        self.limit_score         = limit_score
        self.total_score         = min(100.0, var_score + concentration_score + stress_score + limit_score)
        self.risk_band           = self._band(self.total_score)

    @staticmethod
    def _band(score: float) -> str:
        if score < RISK_SCORE_LOW:
            return "low"
        if score < RISK_SCORE_MEDIUM:
            return "medium"
        if score < RISK_SCORE_HIGH:
            return "high"
        return "critical"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "var_score":           self.var_score,
            "concentration_score": self.concentration_score,
            "stress_score":        self.stress_score,
            "limit_score":         self.limit_score,
            "total_score":         self.total_score,
            "risk_band":           self.risk_band,
        }


class RiskScoreEngine:
    """
    Composite risk score engine.

    Combines VaR, concentration, stress loss, and limit utilisation into
    a single 0–100 score.  Higher score = higher risk.

    Score bands:
      0–30  : low
      30–60 : medium
      60–80 : high
      80–100: critical
    """

    VERSION: str = VERSION

    # ------------------------------------------------------------------
    # Component scoring
    # ------------------------------------------------------------------

    def var_component(self, var_pct: float) -> float:
        """
        VaR contribution (0–40 points).

        var_pct = VaR as fraction of portfolio value.
        10% VaR → 40 points (maximum).
        """
        return min(40.0, var_pct * 400.0)

    def concentration_component(self, hhi: float) -> float:
        """
        HHI concentration contribution (0–20 points).

        HHI ranges 1/N (min) to 1.0 (single position).
        """
        return min(20.0, hhi * 20.0)

    def stress_component(self, worst_stress_loss_pct: float) -> float:
        """
        Worst-case stress loss contribution (0–30 points).

        30% stress loss → 30 points (maximum).
        """
        return min(30.0, worst_stress_loss_pct * 100.0)

    def limit_component(self, max_utilisation: float) -> float:
        """
        Limit utilisation contribution (0–10 points).

        max_utilisation = highest limit utilisation fraction.
        100% utilisation → 10 points.
        """
        return min(10.0, max_utilisation * 10.0)

    # ------------------------------------------------------------------
    # Composite score
    # ------------------------------------------------------------------

    def calculate(
        self,
        var_pct:                  float,
        hhi:                      float,
        worst_stress_loss_pct:    float,
        max_limit_utilisation:    float = 0.0,
    ) -> RiskScoreComponents:
        """
        Calculate the composite risk score.

        Parameters
        ----------
        var_pct :
            Historical VaR as fraction of portfolio value.
        hhi :
            Herfindahl-Hirschman Index (concentration).
        worst_stress_loss_pct :
            Worst-case stress scenario loss as fraction of portfolio.
        max_limit_utilisation :
            Highest limit utilisation fraction across all limits.
        """
        return RiskScoreComponents(
            var_score           = self.var_component(var_pct),
            concentration_score = self.concentration_component(hhi),
            stress_score        = self.stress_component(worst_stress_loss_pct),
            limit_score         = self.limit_component(max_limit_utilisation),
        )
