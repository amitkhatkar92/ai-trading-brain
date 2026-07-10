"""tests/unit/investment/market/structure/test_breakout_engine.py"""
from __future__ import annotations

import pytest

from iios.investment.market.structure.breakout_classifier import BreakoutClassifier
from iios.investment.market.structure.breakout_engine import BreakoutEngine
from iios.investment.market.structure.breakout_statistics import BreakoutStatistics
from iios.investment.market.structure.false_breakout import FalseBreakoutDetector
from iios.investment.market.structure.models import (
    Bar,
    BreakoutStatus,
    BreakoutType,
    Zone,
    ZoneStrength,
    ZoneType,
)
from iios.investment.market.structure.zone_registry import ZoneRegistry
from tests.unit.investment.market.structure.conftest import (
    make_breakout_bars,
    make_range_bars,
)


def _make_zone(level: float, zone_type: ZoneType) -> Zone:
    return Zone(
        zone_id=f"{zone_type.value}_{level:.2f}_0",
        zone_type=zone_type,
        upper=level + 1.0,
        lower=level - 1.0,
        strength=ZoneStrength.MODERATE,
        touch_count=3,
        first_touch_index=0,
        last_touch_index=10,
        first_touch_price=level,
        origin_swing_count=3,
    )


def _make_bar(idx: int, close: float, vol: float = 120_000.0) -> Bar:
    return Bar(
        index=idx, timestamp=float(idx),
        open=close - 0.5, high=close + 0.5,
        low=close - 1.0, close=close,
        volume=vol,
    )


def _build_engine(zones=None) -> BreakoutEngine:
    registry = ZoneRegistry()
    if zones:
        for z in zones:
            registry.add(z)
    return BreakoutEngine(
        classifier=BreakoutClassifier(),
        false_detector=FalseBreakoutDetector(lookback_bars=3),
        stats=BreakoutStatistics(),
        zone_registry=registry,
    )


class TestBreakoutEngine:
    def test_bullish_breakout_detected(self):
        """A bar closing above resistance triggers a bullish breakout."""
        zone = _make_zone(100.0, ZoneType.RESISTANCE)
        engine = _build_engine([zone])
        # 20 bars below resistance
        bars = [_make_bar(i, 95.0 + i * 0.1) for i in range(20)]
        # Breakout bar
        breakout_bar = _make_bar(20, 102.0, vol=250_000.0)
        bars.append(breakout_bar)
        event = engine.update(bars, breakout_bar)
        assert event is not None
        assert event.breakout_type in (BreakoutType.BULLISH, BreakoutType.VOLUME)

    def test_bearish_breakout_detected(self):
        """A bar closing below support triggers a bearish breakout."""
        zone = _make_zone(100.0, ZoneType.SUPPORT)
        engine = _build_engine([zone])
        bars = [_make_bar(i, 105.0 - i * 0.1) for i in range(20)]
        breakout_bar = _make_bar(20, 97.0, vol=250_000.0)
        bars.append(breakout_bar)
        event = engine.update(bars, breakout_bar)
        assert event is not None
        assert event.breakout_type in (BreakoutType.BEARISH, BreakoutType.VOLUME)

    def test_no_breakout_inside_zone(self):
        """No event when price stays inside zone."""
        zone = _make_zone(100.0, ZoneType.RESISTANCE)
        engine = _build_engine([zone])
        bars = [_make_bar(i, 99.0) for i in range(20)]
        event = engine.update(bars, bars[-1])
        assert event is None

    def test_get_active_breakout(self):
        zone = _make_zone(100.0, ZoneType.RESISTANCE)
        engine = _build_engine([zone])
        bars = [_make_bar(i, 95.0) for i in range(20)]
        breakout_bar = _make_bar(20, 102.0, vol=250_000.0)
        bars.append(breakout_bar)
        engine.update(bars, breakout_bar)
        active = engine.get_active_breakout()
        assert active is not None

    def test_volume_confirmation_property(self):
        zone = _make_zone(100.0, ZoneType.RESISTANCE)
        engine = _build_engine([zone])
        bars = [_make_bar(i, 95.0, vol=100_000.0) for i in range(20)]
        breakout_bar = _make_bar(20, 102.0, vol=250_000.0)
        bars.append(breakout_bar)
        event = engine.update(bars, breakout_bar)
        if event:
            assert event.volume_confirmation is True


class TestFalseBreakoutDetector:
    def test_failed_breakout_when_price_returns(self):
        zone = _make_zone(100.0, ZoneType.RESISTANCE)
        from iios.investment.market.structure.models import BreakoutEvent
        event = BreakoutEvent(
            breakout_id="test01",
            breakout_type=BreakoutType.BULLISH,
            status=BreakoutStatus.CONFIRMED,
            zone=zone,
            trigger_index=20,
            trigger_price=102.0,
            trigger_volume=200_000.0,
            avg_volume_20=100_000.0,
            close_beyond=2.0,
        )
        # Bars 21-23 close back below zone.upper (100.0 + 1.0 = 101.0)
        bars = [_make_bar(i, 95.0) for i in range(21)] + [_make_bar(i, 100.5) for i in range(21, 24)]
        detector = FalseBreakoutDetector(lookback_bars=3)
        assert detector.check(event, bars) is True

    def test_confirmed_breakout_holds(self):
        zone = _make_zone(100.0, ZoneType.RESISTANCE)
        from iios.investment.market.structure.models import BreakoutEvent
        event = BreakoutEvent(
            breakout_id="test02",
            breakout_type=BreakoutType.BULLISH,
            status=BreakoutStatus.CONFIRMED,
            zone=zone,
            trigger_index=20,
            trigger_price=102.0,
            trigger_volume=200_000.0,
            avg_volume_20=100_000.0,
            close_beyond=2.0,
        )
        # Price stays above zone
        bars = [_make_bar(i, 95.0) for i in range(21)] + [_make_bar(i, 104.0) for i in range(21, 24)]
        detector = FalseBreakoutDetector(lookback_bars=3)
        assert detector.check(event, bars) is False
