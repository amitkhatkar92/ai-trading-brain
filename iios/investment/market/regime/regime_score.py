"""iios/investment/market/regime/regime_score.py
Regime quality scoring with letter-grade output.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from iios.investment.market.market_constants import (
    TrendDirection,
    VolatilityLevel,
)
from iios.investment.market.regime.models import RegimeObservation, RegimeType

_VOL_CONSISTENCY_SCORE: Dict[VolatilityLevel, float] = {
    VolatilityLevel.VERY_LOW: 80.0,
    VolatilityLevel.LOW:      85.0,
    VolatilityLevel.MODERATE: 90.0,
    VolatilityLevel.HIGH:     70.0,
    VolatilityLevel.EXTREME:  50.0,
}


@dataclass
class RegimeScore:
    """Multi-dimensional regime quality score."""

    overall:           float   # 0-100 weighted composite
    trend_score:       float   # 0-100
    volatility_score:  float   # 0-100
    structure_score:   float   # 0-100
    persistence_score: float   # 0-100
    stability_score:   float   # 0-100

    @property
    def grade(self) -> str:
        """Letter grade based on overall score."""
        if self.overall >= 80:
            return "A"
        if self.overall >= 65:
            return "B"
        if self.overall >= 50:
            return "C"
        if self.overall >= 35:
            return "D"
        return "F"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall":           self.overall,
            "trend_score":       self.trend_score,
            "volatility_score":  self.volatility_score,
            "structure_score":   self.structure_score,
            "persistence_score": self.persistence_score,
            "stability_score":   self.stability_score,
            "grade":             self.grade,
        }


class RegimeScorer:
    """
    Score weights:
    - trend_score:       0.30
    - volatility_score:  0.15
    - structure_score:   0.25
    - persistence_score: 0.20
    - stability_score:   0.10
    """

    _W_TREND:       float = 0.30
    _W_VOL:         float = 0.15
    _W_STRUCTURE:   float = 0.25
    _W_PERSISTENCE: float = 0.20
    _W_STABILITY:   float = 0.10

    def score(
        self,
        obs: RegimeObservation,
        regime: RegimeType,
        bars_in_regime: int,
        transition_prob: float,
        stability_score: float = 0.5,
    ) -> RegimeScore:
        trend_s       = self._trend_score(obs)
        vol_s         = _VOL_CONSISTENCY_SCORE.get(obs.volatility, 70.0)
        structure_s   = obs.quality_score
        persistence_s = min(
            100.0,
            (1.0 - transition_prob) * 100.0 + min(20.0, bars_in_regime * 0.5),
        )
        stability_s   = stability_score * 100.0

        overall = (
            self._W_TREND       * trend_s
            + self._W_VOL       * vol_s
            + self._W_STRUCTURE * structure_s
            + self._W_PERSISTENCE * persistence_s
            + self._W_STABILITY * stability_s
        )
        overall = max(0.0, min(100.0, overall))

        return RegimeScore(
            overall=overall,
            trend_score=trend_s,
            volatility_score=vol_s,
            structure_score=structure_s,
            persistence_score=persistence_s,
            stability_score=stability_s,
        )

    @staticmethod
    def _trend_score(obs: RegimeObservation) -> float:
        if obs.trend_confirmed and obs.trend_leg_count >= 2:
            return min(100.0, 50.0 + min(30.0, obs.trend_leg_count * 8.0))
        if obs.trend_direction != TrendDirection.UNDEFINED:
            return 30.0
        return 10.0
