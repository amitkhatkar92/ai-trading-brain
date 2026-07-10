"""iios/investment/market/regime/regime_confidence.py
Multi-factor regime confidence calculator.
"""
from __future__ import annotations

from iios.investment.market.market_constants import TrendDirection
from iios.investment.market.regime.models import RegimeObservation, RegimeType


class RegimeConfidenceCalculator:
    """
    Calculates regime confidence from four weighted factors.

    Factor weights:
    - structure quality (obs.quality_score / 100): 0.30
    - trend alignment (confirmation + leg count):  0.30
    - duration (saturates at 20 bars):             0.20
    - persistence (1 - transition_probability):    0.20

    Returns float in [0.10, 0.98].
    """

    _W_QUALITY:     float = 0.30
    _W_TREND:       float = 0.30
    _W_DURATION:    float = 0.20
    _W_PERSISTENCE: float = 0.20

    def calculate(
        self,
        obs: RegimeObservation,
        regime: RegimeType,
        bars_in_regime: int,
        transition_probability: float,
    ) -> float:
        q = self._quality_factor(obs)
        t = self._trend_factor(obs)
        d = self._duration_factor(bars_in_regime)
        p = self._persistence_factor(transition_probability)

        raw = (
            self._W_QUALITY     * q
            + self._W_TREND     * t
            + self._W_DURATION  * d
            + self._W_PERSISTENCE * p
        )
        return max(0.10, min(0.98, raw))

    def _quality_factor(self, obs: RegimeObservation) -> float:
        return obs.quality_score / 100.0

    def _trend_factor(self, obs: RegimeObservation) -> float:
        if obs.trend_confirmed and obs.trend_leg_count >= 3:
            return 1.0
        if obs.trend_confirmed and obs.trend_leg_count >= 2:
            return 0.85
        if obs.trend_confirmed:
            return 0.70
        if obs.trend_direction != TrendDirection.UNDEFINED:
            return 0.50
        return 0.20

    def _duration_factor(self, bars_in_regime: int) -> float:
        return min(bars_in_regime, 20) / 20.0

    def _persistence_factor(self, transition_probability: float) -> float:
        return max(0.0, min(1.0, 1.0 - transition_probability))
