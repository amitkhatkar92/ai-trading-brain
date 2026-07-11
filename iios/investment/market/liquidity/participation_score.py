"""iios/investment/market/liquidity/participation_score.py
Computes participation score and bias from VolumeBar + context.
"""
from __future__ import annotations

import logging
from typing import Tuple

from iios.investment.market.liquidity.models import VolumeBar, ParticipationBias

logger = logging.getLogger(__name__)


class ParticipationScoreCalculator:
    """
    Computes participation score (0-100) and bias from VolumeBar + context.
    Stateless — pure computation.
    """

    def calculate(
        self,
        vbar: VolumeBar,
        relative_volume: float,
    ) -> Tuple[float, float, float, float, ParticipationBias, float]:
        """
        Returns (buying_participation, selling_participation,
                 institutional_est, retail_est, bias, score).
        """
        buying_participation = vbar.close_position
        selling_participation = 1.0 - vbar.close_position

        # Institutional estimate proxy
        institutional_est = min(1.0, relative_volume / 2.5)
        if vbar.body_pct > 0.6 and relative_volume > 1.5:
            institutional_est = min(1.0, institutional_est * 1.3)

        retail_est = max(0.0, 1.0 - institutional_est * 0.8)

        participation_balance = buying_participation - selling_participation  # -1 to 1

        if participation_balance > 0.6:
            bias = ParticipationBias.STRONG_BUY
        elif participation_balance > 0.2:
            bias = ParticipationBias.BUY
        elif participation_balance >= -0.2:
            bias = ParticipationBias.NEUTRAL
        elif participation_balance >= -0.6:
            bias = ParticipationBias.SELL
        else:
            bias = ParticipationBias.STRONG_SELL

        # Score 0-100
        base = abs(participation_balance) * 50 + 50
        score_multiplier = min(1.0, relative_volume / 1.5)
        score = max(0.0, min(100.0, base * score_multiplier))

        return (
            buying_participation,
            selling_participation,
            institutional_est,
            retail_est,
            bias,
            score,
        )
