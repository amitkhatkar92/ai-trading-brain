"""iios/investment/market/structure/support_resistance_engine.py
Main S/R engine coordinating zone detection, strength, and registry.
"""
from __future__ import annotations

import logging
from typing import List, Optional

from iios.investment.market.structure.models import (
    Bar,
    SwingSequence,
    Zone,
    ZoneType,
)
from iios.investment.market.structure.zone_detector import ZoneDetector
from iios.investment.market.structure.zone_registry import ZoneRegistry
from iios.investment.market.structure.zone_strength import ZoneStrengthCalculator

logger = logging.getLogger(__name__)


class SupportResistanceEngine:
    """Coordinate zone detection, strength assessment, and registry management."""

    def __init__(
        self,
        detector: ZoneDetector,
        strength_calc: ZoneStrengthCalculator,
        registry: ZoneRegistry,
    ) -> None:
        self._detector = detector
        self._strength = strength_calc
        self._registry = registry

    def update(
        self,
        bars: List[Bar],
        sequence: SwingSequence,
    ) -> List[Zone]:
        """Refresh all zones — detect new ones, check for breaks, update strengths."""
        if not bars:
            return self._registry.get_all()

        current_bar = bars[-1]
        current_idx = current_bar.index

        # 1. Detect S/R and supply/demand zones
        sr_zones = self._detector.detect_zones(bars, sequence)
        sd_zones = self._detector.detect_supply_demand(bars, sequence)

        for zone in sr_zones + sd_zones:
            strength_enum, _ = self._strength.calculate(zone, bars)
            from dataclasses import replace as dc_replace
            zone = dc_replace(zone, strength=strength_enum)
            self._registry.add(zone)

        # 2. Check existing zones for breaks
        for zone in self._registry.get_all():
            if not zone.broken:
                if self._strength.check_broken(zone, current_bar):
                    self._registry.mark_broken(zone.zone_id, current_idx)
                else:
                    # Check if price is touching the zone
                    if zone.lower <= current_bar.close <= zone.upper:
                        updated = self._strength.update_zone_after_touch(zone, current_bar)
                        self._registry.remove(zone.zone_id)
                        self._registry.add(updated)

        # 3. Clean up old zones
        self._registry.cleanup_old(current_idx)

        return self._registry.get_all()

    def get_nearest_resistance(self, price: float) -> Optional[Zone]:
        return self._registry.get_nearest_resistance(price)

    def get_nearest_support(self, price: float) -> Optional[Zone]:
        return self._registry.get_nearest_support(price)

    def get_all_zones(self) -> List[Zone]:
        return self._registry.get_all()

    def get_supply_zones(self) -> List[Zone]:
        return self._registry.get_by_type(ZoneType.SUPPLY)

    def get_demand_zones(self) -> List[Zone]:
        return self._registry.get_by_type(ZoneType.DEMAND)

    def get_flip_zones(self) -> List[Zone]:
        """Broken support = new resistance. Broken resistance = new support."""
        broken_support = self._registry.get_by_type(ZoneType.BROKEN_SUPPORT)
        broken_resistance = self._registry.get_by_type(ZoneType.BROKEN_RESISTANCE)
        flip = self._registry.get_by_type(ZoneType.FLIP)
        return broken_support + broken_resistance + flip
