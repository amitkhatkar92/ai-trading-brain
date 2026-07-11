"""iios/investment/market/liquidity/liquidity_confidence.py
Computes overall liquidity confidence and execution readiness.
"""
from __future__ import annotations

import logging

from iios.investment.market.liquidity.models import (
    LiquidityProfile, ParticipationSnapshot, OrderFlowSnapshot,
)

logger = logging.getLogger(__name__)


class LiquidityConfidenceCalculator:
    """
    Computes overall liquidity confidence and execution readiness.
    Stateless.
    """

    def calculate_confidence(
        self,
        liquidity_profile: LiquidityProfile,
        participation: ParticipationSnapshot,
        volume_quality: float,
        has_active_events: bool,
        shock_event: bool,
    ) -> float:
        base = liquidity_profile.liquidity_confidence

        if shock_event:
            base *= 0.50
        if has_active_events:
            base *= 0.85
        if volume_quality < 30.0:
            base *= 0.70
        elif volume_quality > 70.0:
            base *= 1.10
        if participation.participation_confidence > 0.75:
            base += 0.05

        return max(0.05, min(0.95, base))

    def execution_readiness(
        self,
        liquidity_profile: LiquidityProfile,
        order_flow: OrderFlowSnapshot,
        volume_quality: float,
        shock_event: bool,
    ) -> float:
        """
        How ready is the market for trade execution right now? 0-1.
        """
        base = (
            liquidity_profile.availability * 0.40
            + liquidity_profile.stability * 0.30
            + (volume_quality / 100.0) * 0.20
            + 0.10
        )

        if shock_event:
            base *= 0.30
        elif liquidity_profile.availability < 0.3:
            base *= 0.60

        return max(0.05, min(0.95, base))
