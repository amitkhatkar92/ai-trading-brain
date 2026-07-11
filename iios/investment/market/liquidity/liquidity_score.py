"""iios/investment/market/liquidity/liquidity_score.py
Computes overall liquidity intelligence score (0-100) from all sub-scores.
"""
from __future__ import annotations

import logging
from typing import Optional, TYPE_CHECKING

from iios.investment.market.liquidity.models import (
    LiquidityProfile, ParticipationSnapshot, VolumeProfile,
)

if TYPE_CHECKING:
    from iios.investment.market.regime.models import RegimeType

logger = logging.getLogger(__name__)


class LiquidityScoreCalculator:
    """
    Computes overall liquidity intelligence score (0-100) from all sub-scores.
    Stateless.
    """

    def calculate(
        self,
        liquidity_profile: LiquidityProfile,
        participation: ParticipationSnapshot,
        volume_quality: float,
        volume_profile: VolumeProfile,
        regime: Optional["RegimeType"] = None,
    ) -> float:
        # Normalize up_down_ratio to [0,1] range
        udr = volume_profile.up_down_ratio
        udr_score = (udr / (1.0 + udr)) * 100.0

        base = (
            liquidity_profile.quality * 0.35
            + participation.participation_score * 0.25
            + volume_quality * 0.25
            + udr_score * 0.15
        )

        if regime is not None:
            from iios.investment.market.regime.models import RegimeType
            regime_val = regime.value if hasattr(regime, "value") else str(regime)
            if regime_val in (RegimeType.VOLATILE.value, RegimeType.CRISIS.value):
                base *= 0.80
            elif regime_val in (RegimeType.CALM.value, RegimeType.RANGING.value):
                base *= 1.10
            elif regime_val == RegimeType.EXPANSION.value:
                base *= 1.05

        return max(0.0, min(100.0, base))
