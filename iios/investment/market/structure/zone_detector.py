"""iios/investment/market/structure/zone_detector.py
Detect support/resistance zones from swing points and price clusters.
Pure price action — no indicators.
"""
from __future__ import annotations

import logging
from typing import List, Optional

from iios.investment.market.structure.models import (
    Bar,
    SwingPoint,
    SwingSequence,
    SwingStrength,
    SwingType,
    Zone,
    ZoneStrength,
    ZoneType,
)

logger = logging.getLogger(__name__)


class ZoneDetector:
    """Detect support/resistance and supply/demand zones from swing clusters."""

    def __init__(
        self,
        tolerance_multiplier: float = 1.5,
        min_touches: int = 2,
    ) -> None:
        self._tol_mult = tolerance_multiplier
        self._min_touches = min_touches

    # ── Public API ────────────────────────────────────────────────────────

    def detect_zones(
        self,
        bars: List[Bar],
        sequence: SwingSequence,
    ) -> List[Zone]:
        """Detect all active S/R zones from swing clusters."""
        if not bars:
            return []

        tolerance = self._avg_bar_range(bars) * self._tol_mult
        if tolerance <= 0:
            return []

        zones: List[Zone] = []

        # Resistance from swing highs
        highs = [s for s in sequence.highs if s.strength in (SwingStrength.MAJOR, SwingStrength.INTERMEDIATE)]
        if not highs:
            highs = sequence.highs
        high_clusters = self._cluster_swings(highs, tolerance)
        for cluster in high_clusters:
            if len(cluster) >= self._min_touches:
                z = self._build_zone(cluster, ZoneType.RESISTANCE, tolerance)
                zones.append(z)

        # Support from swing lows
        lows = [s for s in sequence.lows if s.strength in (SwingStrength.MAJOR, SwingStrength.INTERMEDIATE)]
        if not lows:
            lows = sequence.lows
        low_clusters = self._cluster_swings(lows, tolerance)
        for cluster in low_clusters:
            if len(cluster) >= self._min_touches:
                z = self._build_zone(cluster, ZoneType.SUPPORT, tolerance)
                zones.append(z)

        return zones

    def detect_supply_demand(
        self,
        bars: List[Bar],
        sequence: SwingSequence,
    ) -> List[Zone]:
        """Detect supply/demand zones: consolidation before a strong impulse.

        Supply = consolidation bars before a strong bearish move.
        Demand = consolidation bars before a strong bullish move.
        """
        if len(bars) < 10:
            return []

        zones: List[Zone] = []
        avg_range = self._avg_bar_range(bars)
        impulse_threshold = avg_range * 2.0  # strong move = 2× avg range

        for i in range(3, len(bars) - 1):
            bar = bars[i]
            # Strong bearish impulse → supply zone is the 2-3 bars before it
            if bar.range > impulse_threshold and bar.is_bearish:
                consol_bars = bars[max(0, i - 3) : i]
                if consol_bars:
                    high_b = max(b.high for b in consol_bars)
                    low_b = min(b.low for b in consol_bars)
                    touch_idx = consol_bars[0].index
                    z = Zone(
                        zone_id=f"SUPPLY_{high_b:.2f}_{touch_idx}",
                        zone_type=ZoneType.SUPPLY,
                        upper=high_b,
                        lower=low_b,
                        strength=ZoneStrength.MODERATE,
                        touch_count=1,
                        first_touch_index=touch_idx,
                        last_touch_index=bar.index,
                        first_touch_price=(high_b + low_b) / 2.0,
                        origin_swing_count=len(consol_bars),
                    )
                    zones.append(z)

            # Strong bullish impulse → demand zone is the 2-3 bars before it
            elif bar.range > impulse_threshold and bar.is_bullish:
                consol_bars = bars[max(0, i - 3) : i]
                if consol_bars:
                    high_b = max(b.high for b in consol_bars)
                    low_b = min(b.low for b in consol_bars)
                    touch_idx = consol_bars[0].index
                    z = Zone(
                        zone_id=f"DEMAND_{low_b:.2f}_{touch_idx}",
                        zone_type=ZoneType.DEMAND,
                        upper=high_b,
                        lower=low_b,
                        strength=ZoneStrength.MODERATE,
                        touch_count=1,
                        first_touch_index=touch_idx,
                        last_touch_index=bar.index,
                        first_touch_price=(high_b + low_b) / 2.0,
                        origin_swing_count=len(consol_bars),
                    )
                    zones.append(z)

        return zones

    # ── Private helpers ───────────────────────────────────────────────────

    def _cluster_swings(
        self,
        swings: List[SwingPoint],
        tolerance: float,
    ) -> List[List[SwingPoint]]:
        """Group nearby swings into clusters using single-linkage."""
        if not swings:
            return []

        sorted_swings = sorted(swings, key=lambda s: s.price)
        clusters: List[List[SwingPoint]] = []
        current_cluster: List[SwingPoint] = [sorted_swings[0]]

        for sw in sorted_swings[1:]:
            if sw.price - current_cluster[-1].price <= tolerance:
                current_cluster.append(sw)
            else:
                clusters.append(current_cluster)
                current_cluster = [sw]
        clusters.append(current_cluster)

        return clusters

    def _avg_bar_range(self, bars: List[Bar]) -> float:
        """Mean of (high - low) over bars. NOT ATR."""
        if not bars:
            return 0.0
        return sum(b.range for b in bars) / len(bars)

    def _build_zone(
        self,
        cluster: List[SwingPoint],
        zone_type: ZoneType,
        tolerance: float,
    ) -> Zone:
        prices = [s.price for s in cluster]
        mid_price = sum(prices) / len(prices)
        half_tol = tolerance / 2.0
        upper = mid_price + half_tol
        lower = mid_price - half_tol

        touch_count = len(cluster)
        first = min(cluster, key=lambda s: s.index)
        last = max(cluster, key=lambda s: s.index)

        strength = (
            ZoneStrength.MAJOR
            if touch_count >= 4
            else ZoneStrength.MODERATE
            if touch_count >= 2
            else ZoneStrength.MINOR
        )

        zone_id = f"{zone_type.value.upper()}_{mid_price:.2f}_{first.index}"
        return Zone(
            zone_id=zone_id,
            zone_type=zone_type,
            upper=upper,
            lower=lower,
            strength=strength,
            touch_count=touch_count,
            first_touch_index=first.index,
            last_touch_index=last.index,
            first_touch_price=first.price,
            origin_swing_count=len(cluster),
        )
