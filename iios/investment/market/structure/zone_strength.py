"""iios/investment/market/structure/zone_strength.py
Calculate zone strength from price action factors. No indicators.
"""
from __future__ import annotations

import logging
from typing import List, Tuple

from iios.investment.market.structure.models import Bar, Zone, ZoneStrength, ZoneType

logger = logging.getLogger(__name__)


class ZoneStrengthCalculator:
    """Evaluate zone strength from pure price-action factors."""

    def calculate(
        self,
        zone: Zone,
        bars: List[Bar],
    ) -> Tuple[ZoneStrength, float]:
        """Return (strength_enum, score 0-100)."""
        score = 0.0

        # Factor 1: touch count (0-40 points)
        touch_score = min(zone.touch_count / 5.0, 1.0) * 40.0
        score += touch_score

        # Factor 2: zone age — bars the zone has existed (0-20 points)
        age = zone.last_touch_index - zone.first_touch_index
        age_score = min(age / 100.0, 1.0) * 20.0
        score += age_score

        # Factor 3: zone tightness — narrower zone = cleaner level (0-20 points)
        if bars:
            avg_range = sum(b.range for b in bars) / len(bars)
            if avg_range > 0:
                width_ratio = zone.width / avg_range
                # Tighter = better; ratio < 1 is very tight, > 3 is wide
                tightness_score = max(0.0, (1.0 - width_ratio / 3.0)) * 20.0
                score += tightness_score

        # Factor 4: retested and held (0-20 points)
        if zone.retested_after_break:
            score += 20.0
        elif zone.touch_count >= 3:
            score += 10.0

        score = max(0.0, min(100.0, score))

        if score >= 70:
            strength = ZoneStrength.MAJOR
        elif score >= 40:
            strength = ZoneStrength.MODERATE
        else:
            strength = ZoneStrength.MINOR

        return strength, score

    def update_zone_after_touch(self, zone: Zone, bar: Bar) -> Zone:
        """Return a new Zone with touch_count incremented and last_touch updated."""
        from dataclasses import replace

        return replace(
            zone,
            touch_count=zone.touch_count + 1,
            last_touch_index=bar.index,
        )

    def check_broken(
        self,
        zone: Zone,
        bar: Bar,
        close_pct_threshold: float = 0.003,
    ) -> bool:
        """True if bar closes clearly beyond the zone.

        Support broken: close < zone.lower - zone.width * 0.5
        Resistance broken: close > zone.upper + zone.width * 0.5
        """
        margin = max(zone.width * 0.5, zone.lower * close_pct_threshold)
        if zone.zone_type in (ZoneType.SUPPORT, ZoneType.DEMAND):
            return bar.close < zone.lower - margin
        if zone.zone_type in (ZoneType.RESISTANCE, ZoneType.SUPPLY):
            return bar.close > zone.upper + margin
        # For FLIP zones, check both directions
        return (
            bar.close < zone.lower - margin or bar.close > zone.upper + margin
        )
