"""iios/investment/market/structure/zone_registry.py
Maintain and manage the active zone set.
"""
from __future__ import annotations

import logging
from dataclasses import replace
from typing import Dict, List, Optional

from iios.investment.market.structure.models import Zone, ZoneType

logger = logging.getLogger(__name__)


class ZoneRegistry:
    """In-memory registry of active support/resistance/supply/demand zones."""

    def __init__(self, max_zones: int = 50) -> None:
        self._max = max_zones
        self._zones: Dict[str, Zone] = {}

    def add(self, zone: Zone) -> None:
        if zone.zone_id in self._zones:
            return
        if len(self._zones) >= self._max:
            # Evict the oldest zone (smallest first_touch_index)
            oldest_id = min(
                self._zones.keys(),
                key=lambda zid: self._zones[zid].first_touch_index,
            )
            del self._zones[oldest_id]
        self._zones[zone.zone_id] = zone

    def remove(self, zone_id: str) -> None:
        self._zones.pop(zone_id, None)

    def get_all(self) -> List[Zone]:
        return list(self._zones.values())

    def get_by_type(self, zone_type: ZoneType) -> List[Zone]:
        return [z for z in self._zones.values() if z.zone_type == zone_type]

    def get_nearest_resistance(self, price: float) -> Optional[Zone]:
        candidates = [
            z for z in self._zones.values()
            if z.lower > price and not z.broken
        ]
        if not candidates:
            return None
        return min(candidates, key=lambda z: z.lower - price)

    def get_nearest_support(self, price: float) -> Optional[Zone]:
        candidates = [
            z for z in self._zones.values()
            if z.upper < price and not z.broken
        ]
        if not candidates:
            return None
        return min(candidates, key=lambda z: price - z.upper)

    def get_zones_around(self, price: float, pct: float = 0.02) -> List[Zone]:
        margin = price * pct
        return [
            z for z in self._zones.values()
            if z.lower <= price + margin and z.upper >= price - margin
        ]

    def mark_broken(self, zone_id: str, bar_index: int) -> None:
        if zone_id in self._zones:
            z = self._zones[zone_id]
            # Flip type: support → broken_support, resistance → broken_resistance
            if z.zone_type == ZoneType.SUPPORT:
                new_type = ZoneType.BROKEN_SUPPORT
            elif z.zone_type == ZoneType.RESISTANCE:
                new_type = ZoneType.BROKEN_RESISTANCE
            else:
                new_type = z.zone_type
            self._zones[zone_id] = replace(
                z,
                broken=True,
                broken_index=bar_index,
                zone_type=new_type,
            )

    def cleanup_old(self, current_index: int, max_age: int = 200) -> int:
        """Remove zones whose last touch is older than max_age bars. Returns count removed."""
        to_remove = [
            zid for zid, z in self._zones.items()
            if (current_index - z.last_touch_index) > max_age
        ]
        for zid in to_remove:
            del self._zones[zid]
        return len(to_remove)

    def merge_overlapping(self) -> int:
        """Merge zones that overlap significantly. Returns count merged."""
        zones = list(self._zones.values())
        merged_count = 0
        merged_ids: set = set()

        for i in range(len(zones)):
            if zones[i].zone_id in merged_ids:
                continue
            for j in range(i + 1, len(zones)):
                if zones[j].zone_id in merged_ids:
                    continue
                a, b = zones[i], zones[j]
                # Same type, overlapping
                if a.zone_type != b.zone_type:
                    continue
                overlap = min(a.upper, b.upper) - max(a.lower, b.lower)
                if overlap <= 0:
                    continue
                # If overlap > 50% of the smaller zone → merge
                smaller_width = min(a.width, b.width) or 1e-9
                if overlap / smaller_width > 0.5:
                    merged_upper = max(a.upper, b.upper)
                    merged_lower = min(a.lower, b.lower)
                    merged_touch = a.touch_count + b.touch_count
                    merged_zone = replace(
                        a,
                        upper=merged_upper,
                        lower=merged_lower,
                        touch_count=merged_touch,
                        first_touch_index=min(a.first_touch_index, b.first_touch_index),
                        last_touch_index=max(a.last_touch_index, b.last_touch_index),
                    )
                    self._zones[merged_zone.zone_id] = merged_zone
                    merged_ids.add(b.zone_id)
                    self._zones.pop(b.zone_id, None)
                    merged_count += 1

        return merged_count
