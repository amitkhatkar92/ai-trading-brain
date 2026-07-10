"""tests/unit/investment/market/structure/test_market_structure_engine.py
Integration test: full cycle through InstitutionalMarketStructureEngine.
"""
from __future__ import annotations

import dataclasses

import pytest

from iios.investment.market.market_constants import TrendDirection
from iios.investment.market.structure.market_structure_engine import InstitutionalMarketStructureEngine
from iios.investment.market.structure.models import (
    MarketStructureSnapshot,
    StructurePhase,
    StructureQualityScore,
    TrendState,
)
from tests.unit.investment.market.structure.conftest import (
    make_breakout_bars,
    make_compression_bars,
    make_downtrend_bars,
    make_range_bars,
    make_uptrend_bars,
)


def _engine(symbol: str = "TEST", timeframe: str = "1d") -> InstitutionalMarketStructureEngine:
    return InstitutionalMarketStructureEngine.create_default(symbol, timeframe)


class TestEngineInitialization:
    def test_initialize_returns_snapshot(self):
        bars = make_uptrend_bars(n=50)
        engine = _engine()
        snap = engine.initialize(bars)
        assert isinstance(snap, MarketStructureSnapshot)

    def test_initialize_populates_trend(self):
        bars = make_uptrend_bars(n=50)
        engine = _engine()
        snap = engine.initialize(bars)
        assert snap.trend is not None
        assert isinstance(snap.trend.direction, TrendDirection)

    def test_initialize_populates_quality(self):
        bars = make_uptrend_bars(n=50)
        engine = _engine()
        snap = engine.initialize(bars)
        assert snap.quality is not None
        assert 0.0 <= snap.quality.overall <= 100.0

    def test_initialize_populates_structure_phase(self):
        bars = make_uptrend_bars(n=50)
        engine = _engine()
        snap = engine.initialize(bars)
        assert isinstance(snap.structure_phase, StructurePhase)

    def test_snapshot_to_dict(self):
        bars = make_uptrend_bars(n=50)
        engine = _engine()
        snap = engine.initialize(bars)
        d = snap.to_dict()
        assert isinstance(d, dict)
        assert "symbol" in d
        assert "trend" in d
        assert "quality" in d


class TestEngineUpdate:
    def test_update_returns_snapshot(self):
        bars = make_uptrend_bars(n=50)
        engine = _engine()
        engine.initialize(bars[:-1])
        snap = engine.update(bars[-1])
        assert isinstance(snap, MarketStructureSnapshot)

    def test_update_increments_bar_index(self):
        bars = make_uptrend_bars(n=50)
        engine = _engine()
        snap1 = engine.initialize(bars[:40])
        snap2 = engine.update(bars[40])
        assert snap2.bar_index >= snap1.bar_index

    def test_batch_update(self):
        bars = make_uptrend_bars(n=50)
        engine = _engine()
        engine.initialize(bars[:30])
        snap = engine.update_batch(bars[30:])
        assert isinstance(snap, MarketStructureSnapshot)

    def test_get_current_matches_last_update(self):
        bars = make_uptrend_bars(n=50)
        engine = _engine()
        snap = engine.initialize(bars)
        current = engine.get_current()
        assert current is not None
        assert current.bar_index == snap.bar_index


class TestEngineQueryAPI:
    def test_get_trend(self):
        bars = make_uptrend_bars(n=50)
        engine = _engine()
        engine.initialize(bars)
        trend = engine.get_trend()
        assert isinstance(trend, TrendState)

    def test_get_phase(self):
        bars = make_uptrend_bars(n=50)
        engine = _engine()
        engine.initialize(bars)
        phase = engine.get_phase()
        assert isinstance(phase, StructurePhase)

    def test_get_swings(self):
        bars = make_uptrend_bars(n=60)
        engine = _engine()
        engine.initialize(bars)
        seq = engine.get_swings(n=5)
        assert len(seq.highs) <= 5
        assert len(seq.lows) <= 5

    def test_get_all_zones_list(self):
        bars = make_range_bars(n=40)
        engine = _engine()
        engine.initialize(bars)
        zones = engine.get_all_zones()
        assert isinstance(zones, list)

    def test_get_quality(self):
        bars = make_uptrend_bars(n=50)
        engine = _engine()
        engine.initialize(bars)
        quality = engine.get_quality()
        assert quality is not None
        assert isinstance(quality, StructureQualityScore)


class TestEngineCallbacks:
    def test_on_structure_update_called(self):
        bars = make_uptrend_bars(n=50)
        engine = _engine()
        engine.initialize(bars[:40])
        called = []
        engine.on_structure_update(lambda snap: called.append(snap))
        engine.update(bars[40])
        assert len(called) == 1
        assert isinstance(called[0], MarketStructureSnapshot)

    def test_multiple_callbacks(self):
        bars = make_uptrend_bars(n=50)
        engine = _engine()
        engine.initialize(bars[:40])
        results = []
        engine.on_structure_update(lambda s: results.append("a"))
        engine.on_structure_update(lambda s: results.append("b"))
        engine.update(bars[40])
        assert "a" in results and "b" in results


class TestEngineHistoricalQuery:
    def test_trend_at_bar_index(self):
        bars = make_uptrend_bars(n=50)
        engine = _engine()
        engine.initialize(bars)
        direction = engine.trend_at(bars[20].index)
        # May be None if not yet snapshotted at that index
        assert direction is None or isinstance(direction, TrendDirection)

    def test_transitions_since(self):
        bars = make_uptrend_bars(n=50)
        engine = _engine()
        engine.initialize(bars)
        transitions = engine.transitions_since(0)
        assert isinstance(transitions, list)

    def test_get_history_range(self):
        bars = make_uptrend_bars(n=50)
        engine = _engine()
        engine.initialize(bars)
        history = engine.get_history(0, 100)
        assert isinstance(history, list)


class TestEngineScenarios:
    def test_uptrend_direction(self):
        bars = make_uptrend_bars(n=60)
        engine = _engine()
        snap = engine.initialize(bars)
        # With sufficient bars, should detect UP or SIDEWAYS (swings needed)
        assert snap.trend.direction in (TrendDirection.UP, TrendDirection.SIDEWAYS)

    def test_downtrend_direction(self):
        bars = make_downtrend_bars(n=60)
        engine = _engine()
        snap = engine.initialize(bars)
        assert snap.trend.direction in (TrendDirection.DOWN, TrendDirection.SIDEWAYS)

    def test_breakout_scenario(self):
        bars = make_breakout_bars(n=40)
        engine = _engine()
        snap = engine.initialize(bars)
        assert snap is not None

    def test_compression_scenario(self):
        bars = make_compression_bars(n=30)
        engine = _engine()
        snap = engine.initialize(bars)
        assert snap is not None

    def test_engine_symbol_preserved(self):
        bars = make_uptrend_bars(n=30)
        engine = InstitutionalMarketStructureEngine.create_default("RELIANCE", "1d")
        snap = engine.initialize(bars)
        assert snap.symbol == "RELIANCE"
        assert snap.timeframe == "1d"
