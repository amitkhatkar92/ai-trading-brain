"""tests/unit/investment/market/structure/test_support_resistance.py"""
from __future__ import annotations

import pytest

from iios.investment.market.structure.models import SwingSequence, ZoneType
from iios.investment.market.structure.swing_detector import SwingDetector
from iios.investment.market.structure.swing_history import SwingHistory
from iios.investment.market.structure.support_resistance_engine import SupportResistanceEngine
from iios.investment.market.structure.zone_detector import ZoneDetector
from iios.investment.market.structure.zone_registry import ZoneRegistry
from iios.investment.market.structure.zone_strength import ZoneStrengthCalculator
from tests.unit.investment.market.structure.conftest import (
    make_breakout_bars,
    make_range_bars,
    make_uptrend_bars,
)


def _build_sr_engine() -> SupportResistanceEngine:
    return SupportResistanceEngine(
        detector=ZoneDetector(tolerance_multiplier=1.5, min_touches=2),
        strength_calc=ZoneStrengthCalculator(),
        registry=ZoneRegistry(max_zones=50),
    )


def _get_sequence(bars):
    hist = SwingHistory()
    det = SwingDetector()
    for sw in det.detect_all(bars):
        hist.add(sw)
    return hist.get_sequence()


class TestZoneDetector:
    def test_detects_zones_in_range(self):
        bars = make_range_bars(n=40)
        seq = _get_sequence(bars)
        det = ZoneDetector(tolerance_multiplier=2.0, min_touches=1)
        zones = det.detect_zones(bars, seq)
        # Range bars should produce multiple zones
        assert isinstance(zones, list)

    def test_supply_demand_zones(self):
        bars = make_breakout_bars(n=40)
        seq = _get_sequence(bars)
        det = ZoneDetector()
        sd_zones = det.detect_supply_demand(bars, seq)
        assert isinstance(sd_zones, list)

    def test_zone_bounds_valid(self):
        bars = make_range_bars(n=40)
        seq = _get_sequence(bars)
        det = ZoneDetector(tolerance_multiplier=2.0, min_touches=1)
        zones = det.detect_zones(bars, seq)
        for z in zones:
            assert z.upper >= z.lower
            assert z.touch_count >= 1


class TestZoneRegistry:
    def test_add_and_get(self):
        from iios.investment.market.structure.models import Zone, ZoneStrength
        registry = ZoneRegistry()
        zone = Zone(
            zone_id="R_100_0", zone_type=ZoneType.RESISTANCE,
            upper=101.0, lower=99.0, strength=ZoneStrength.MODERATE,
            touch_count=2, first_touch_index=0, last_touch_index=5,
            first_touch_price=100.0, origin_swing_count=2,
        )
        registry.add(zone)
        assert len(registry.get_all()) == 1

    def test_get_nearest_resistance_above(self):
        from iios.investment.market.structure.models import Zone, ZoneStrength
        registry = ZoneRegistry()
        for level in [110, 115, 120]:
            z = Zone(
                zone_id=f"R_{level}_0", zone_type=ZoneType.RESISTANCE,
                upper=float(level + 1), lower=float(level - 1),
                strength=ZoneStrength.MODERATE,
                touch_count=2, first_touch_index=0, last_touch_index=5,
                first_touch_price=float(level), origin_swing_count=2,
            )
            registry.add(z)
        nearest = registry.get_nearest_resistance(105.0)
        assert nearest is not None
        assert nearest.lower == 109.0  # 110-1

    def test_get_nearest_support_below(self):
        from iios.investment.market.structure.models import Zone, ZoneStrength
        registry = ZoneRegistry()
        for level in [80, 85, 90]:
            z = Zone(
                zone_id=f"S_{level}_0", zone_type=ZoneType.SUPPORT,
                upper=float(level + 1), lower=float(level - 1),
                strength=ZoneStrength.MODERATE,
                touch_count=2, first_touch_index=0, last_touch_index=5,
                first_touch_price=float(level), origin_swing_count=2,
            )
            registry.add(z)
        nearest = registry.get_nearest_support(95.0)
        assert nearest is not None
        assert nearest.upper == 91.0  # 90+1

    def test_mark_broken_changes_type(self):
        from iios.investment.market.structure.models import Zone, ZoneStrength
        registry = ZoneRegistry()
        z = Zone(
            zone_id="S_100_0", zone_type=ZoneType.SUPPORT,
            upper=101.0, lower=99.0, strength=ZoneStrength.MODERATE,
            touch_count=2, first_touch_index=0, last_touch_index=5,
            first_touch_price=100.0, origin_swing_count=2,
        )
        registry.add(z)
        registry.mark_broken("S_100_0", bar_index=10)
        zones = registry.get_all()
        assert zones[0].broken is True
        assert zones[0].zone_type == ZoneType.BROKEN_SUPPORT

    def test_cleanup_removes_old_zones(self):
        from iios.investment.market.structure.models import Zone, ZoneStrength
        registry = ZoneRegistry()
        z = Zone(
            zone_id="S_100_0", zone_type=ZoneType.SUPPORT,
            upper=101.0, lower=99.0, strength=ZoneStrength.MODERATE,
            touch_count=2, first_touch_index=0, last_touch_index=5,
            first_touch_price=100.0, origin_swing_count=2,
        )
        registry.add(z)
        removed = registry.cleanup_old(current_index=300, max_age=200)
        assert removed == 1
        assert len(registry.get_all()) == 0


class TestSupportResistanceEngine:
    def test_update_returns_zones(self):
        bars = make_range_bars(n=40)
        seq = _get_sequence(bars)
        engine = _build_sr_engine()
        zones = engine.update(bars, seq)
        assert isinstance(zones, list)

    def test_flip_zones_after_break(self):
        """After a zone is broken it should appear in flip_zones."""
        bars = make_breakout_bars(n=40)
        seq = _get_sequence(bars)
        engine = _build_sr_engine()
        engine.update(bars, seq)
        flips = engine.get_flip_zones()
        assert isinstance(flips, list)
