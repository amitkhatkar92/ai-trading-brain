"""iios/investment/market/liquidity/liquidity_profile.py
Computes LiquidityProfile from a rolling window of VolumeBar objects.
"""
from __future__ import annotations

import logging
import math
from typing import List

from iios.investment.market.liquidity.models import VolumeBar, LiquidityProfile

logger = logging.getLogger(__name__)


class LiquidityProfileAnalyzer:
    """
    Computes LiquidityProfile from a rolling window of VolumeBar objects.
    Stateless — pure computation.
    """

    def analyze(
        self,
        vbars: List[VolumeBar],
        avg_volume: float,
        max_historical_volume: float,
    ) -> LiquidityProfile:
        if not vbars:
            return LiquidityProfile(
                availability=0.0, stability=0.0, depth=0.0,
                concentration=1.0, fragmentation=0.0,
                quality=0.0, liquidity_confidence=0.05,
            )

        latest = vbars[-1]
        latest_rv = latest.relative_volume

        # availability: 0 when rv=0.3, 1 when rv>=2.0
        availability = min(1.0, max(0.0, (latest_rv - 0.3) / 1.7))

        # stability: based on last 20 volumes
        volumes = [b.volume for b in vbars[-20:]]
        mean_vol = sum(volumes) / len(volumes) if volumes else 1e-9
        variance = sum((v - mean_vol) ** 2 for v in volumes) / len(volumes) if volumes else 0.0
        std_vol = math.sqrt(variance)
        stability = max(0.0, 1.0 - min(1.0, std_vol / max(mean_vol, 1e-9)))

        # depth: latest volume vs max historical
        depth = min(1.0, max(0.0, latest.volume / max(max_historical_volume, 1e-9)))

        # concentration: peak / sum of last 10
        last_10 = [b.volume for b in vbars[-10:]]
        sum_10 = sum(last_10)
        peak_recent = max(last_10) if last_10 else 0.0
        concentration = min(1.0, peak_recent / max(sum_10, 1e-9))

        fragmentation = 1.0 - concentration

        # quality (0-100)
        quality = (
            availability * 30.0
            + stability * 25.0
            + depth * 20.0
            + fragmentation * 15.0
            + (1.0 - concentration) * 10.0
        ) * 1.0  # sub-scores already [0,1], multiply by weights sum to 100

        quality = max(0.0, min(100.0, quality))

        liquidity_confidence = min(0.95, availability * 0.5 + stability * 0.3 + 0.2)

        return LiquidityProfile(
            availability=availability,
            stability=stability,
            depth=depth,
            concentration=concentration,
            fragmentation=fragmentation,
            quality=quality,
            liquidity_confidence=liquidity_confidence,
        )
