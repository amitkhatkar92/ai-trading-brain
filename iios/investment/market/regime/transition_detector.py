"""iios/investment/market/regime/transition_detector.py
Detects regime transition signals from consecutive observations.
"""
from __future__ import annotations

import logging
import time
from typing import Optional

from iios.investment.market.market_constants import VolatilityLevel
from iios.investment.market.regime.models import (
    RegimeObservation,
    RegimeType,
    TransitionEvent,
    TransitionType,
)

logger = logging.getLogger(__name__)

# Ordinal severity: higher = more volatile
_VOL_SEVERITY = {
    VolatilityLevel.VERY_LOW: 0,
    VolatilityLevel.LOW:      1,
    VolatilityLevel.MODERATE: 2,
    VolatilityLevel.HIGH:     3,
    VolatilityLevel.EXTREME:  4,
}


class TransitionDetector:
    """Stateless detector of regime transition signals."""

    def detect(
        self,
        obs: RegimeObservation,
        prev_obs: Optional[RegimeObservation],
        current_regime: RegimeType,
        bars_in_regime: int,
    ) -> Optional[TransitionEvent]:
        """
        Detect transition signals from consecutive observations.
        Returns None if no signal detected.
        """
        if prev_obs is None:
            return None

        # 1. EMERGING_TREND
        if prev_obs.in_consolidation and not obs.in_consolidation and obs.has_active_breakout:
            to_regime = RegimeType.BULL if obs.breakout_bullish else RegimeType.BEAR
            return TransitionEvent(
                transition_type=TransitionType.EMERGING_TREND,
                from_regime=current_regime,
                to_regime=to_regime,
                probability=0.70,
                confidence=0.65,
                trigger="consolidation_breakout",
                bars_since_signal=0,
                confirmed=False,
                timestamp=time.time(),
            )

        # 2. TREND_FAILURE
        if current_regime in (RegimeType.BULL, RegimeType.BEAR):
            in_exhaustion  = obs.trend_phase in ("exhaustion", "correction")
            bull_failure   = (
                current_regime == RegimeType.BULL
                and in_exhaustion
                and obs.structure_phase == "distribution"
            )
            bear_failure   = (
                current_regime == RegimeType.BEAR
                and in_exhaustion
                and obs.structure_phase == "accumulation"
            )
            if bull_failure:
                return TransitionEvent(
                    transition_type=TransitionType.TREND_FAILURE,
                    from_regime=current_regime,
                    to_regime=RegimeType.DISTRIBUTION,
                    probability=0.65,
                    confidence=0.60,
                    trigger="bull_exhaustion_distribution",
                    bars_since_signal=0,
                    confirmed=False,
                    timestamp=time.time(),
                )
            if bear_failure:
                return TransitionEvent(
                    transition_type=TransitionType.TREND_FAILURE,
                    from_regime=current_regime,
                    to_regime=RegimeType.ACCUMULATION,
                    probability=0.65,
                    confidence=0.60,
                    trigger="bear_exhaustion_accumulation",
                    bars_since_signal=0,
                    confirmed=False,
                    timestamp=time.time(),
                )

        # 3. REVERSAL
        if obs.trend_phase == "reversal":
            to_regime = self._inverse_regime(current_regime)
            return TransitionEvent(
                transition_type=TransitionType.REVERSAL,
                from_regime=current_regime,
                to_regime=to_regime,
                probability=0.60,
                confidence=0.55,
                trigger="trend_phase_reversal",
                bars_since_signal=0,
                confirmed=False,
                timestamp=time.time(),
            )

        # 4. VOLATILITY_EXPANSION
        prev_sev = _VOL_SEVERITY.get(prev_obs.volatility, 2)
        curr_sev = _VOL_SEVERITY.get(obs.volatility, 2)
        if curr_sev - prev_sev >= 2:
            return TransitionEvent(
                transition_type=TransitionType.VOLATILITY_EXPANSION,
                from_regime=current_regime,
                to_regime=RegimeType.VOLATILE,
                probability=0.75,
                confidence=0.70,
                trigger=f"vol_jump_{prev_obs.volatility.value}_to_{obs.volatility.value}",
                bars_since_signal=0,
                confirmed=False,
                timestamp=time.time(),
            )

        # 5. VOLATILITY_COMPRESSION
        if prev_sev - curr_sev >= 2:
            return TransitionEvent(
                transition_type=TransitionType.VOLATILITY_COMPRESSION,
                from_regime=current_regime,
                to_regime=RegimeType.CALM,
                probability=0.75,
                confidence=0.70,
                trigger=f"vol_drop_{prev_obs.volatility.value}_to_{obs.volatility.value}",
                bars_since_signal=0,
                confirmed=False,
                timestamp=time.time(),
            )

        # 6. REGIME_PERSISTENCE
        if (
            bars_in_regime > 50
            and obs.trend_direction == prev_obs.trend_direction
            and obs.volatility     == prev_obs.volatility
            and obs.in_consolidation == prev_obs.in_consolidation
        ):
            return TransitionEvent(
                transition_type=TransitionType.REGIME_PERSISTENCE,
                from_regime=current_regime,
                to_regime=current_regime,
                probability=0.85,
                confidence=0.80,
                trigger="regime_persistence",
                bars_since_signal=0,
                confirmed=True,
                timestamp=time.time(),
            )

        return None

    @staticmethod
    def _inverse_regime(regime: RegimeType) -> RegimeType:
        _inverses = {
            RegimeType.BULL:         RegimeType.BEAR,
            RegimeType.BEAR:         RegimeType.BULL,
            RegimeType.EXPANSION:    RegimeType.CONTRACTION,
            RegimeType.CONTRACTION:  RegimeType.EXPANSION,
            RegimeType.DISTRIBUTION: RegimeType.ACCUMULATION,
            RegimeType.ACCUMULATION: RegimeType.DISTRIBUTION,
        }
        return _inverses.get(regime, RegimeType.TRANSITION)
