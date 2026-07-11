"""iios/investment/market/liquidity/volume_profile.py
Builds a VolumeProfile from a list of VolumeBar objects.
"""
from __future__ import annotations

import logging
import math
from typing import List

from iios.investment.market.liquidity.models import VolumeBar, VolumeProfile, VolumeTrend

logger = logging.getLogger(__name__)


class VolumeProfileAnalyzer:
    """
    Builds a VolumeProfile from a list of VolumeBar objects.
    Stateless — pure computation.
    """

    def analyze(self, bars: List[VolumeBar], window: int = 20) -> VolumeProfile:
        """
        Uses the last `window` VolumeBar items from `bars`.
        """
        if not bars:
            return VolumeProfile(
                period_bars=0, avg_volume=0.0, std_volume=0.0,
                median_volume=0.0, peak_volume=0.0, min_volume=0.0,
                recent_avg=0.0, volume_trend=VolumeTrend.STABLE,
                up_volume=0.0, down_volume=0.0, up_down_ratio=1.0,
            )

        window_bars = bars[-window:]
        volumes = [b.volume for b in window_bars]
        n = len(volumes)

        avg_volume = sum(volumes) / n
        variance = sum((v - avg_volume) ** 2 for v in volumes) / n
        std_volume = math.sqrt(variance)
        sorted_vols = sorted(volumes)
        mid = n // 2
        if n % 2 == 0 and n > 0:
            median_volume = (sorted_vols[mid - 1] + sorted_vols[mid]) / 2.0
        elif n > 0:
            median_volume = float(sorted_vols[mid])
        else:
            median_volume = 0.0
        peak_volume = max(volumes)
        min_volume = min(volumes)

        last_5 = volumes[-5:] if len(volumes) >= 5 else volumes
        last_20 = volumes
        last_5_avg = sum(last_5) / len(last_5)
        last_20_avg = sum(last_20) / len(last_20) if last_20 else 0.0

        # Determine volume trend
        if last_20_avg > 0 and last_5_avg > last_20_avg * 1.20:
            volume_trend = VolumeTrend.EXPANDING
        elif last_20_avg > 0 and last_5_avg < last_20_avg * 0.80:
            volume_trend = VolumeTrend.CONTRACTING
        elif last_20_avg > 0 and len(volumes) >= 1 and volumes[-1] > 2.5 * last_20_avg:
            volume_trend = VolumeTrend.SPIKING
        elif last_20_avg > 0 and len(volumes) >= 3 and all(
            v < 0.5 * last_20_avg for v in volumes[-3:]
        ):
            volume_trend = VolumeTrend.DRYING_UP
        else:
            volume_trend = VolumeTrend.STABLE

        up_volume = sum(b.volume for b in window_bars if b.is_up)
        down_volume = sum(b.volume for b in window_bars if not b.is_up)
        up_down_ratio = up_volume / max(down_volume, 1e-9)

        return VolumeProfile(
            period_bars=n,
            avg_volume=avg_volume,
            std_volume=std_volume,
            median_volume=median_volume,
            peak_volume=peak_volume,
            min_volume=min_volume,
            recent_avg=last_5_avg,
            volume_trend=volume_trend,
            up_volume=up_volume,
            down_volume=down_volume,
            up_down_ratio=up_down_ratio,
        )
