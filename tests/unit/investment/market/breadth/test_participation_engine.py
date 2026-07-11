"""test_participation_engine.py — tests for ParticipationProfileBuilder and ParticipationEngine."""
from __future__ import annotations

import pytest

from iios.investment.market.breadth.participation_profile import ParticipationProfileBuilder
from iios.investment.market.breadth.participation_engine import ParticipationEngine

from tests.unit.investment.market.breadth.conftest import (
    make_bull_universe,
    make_bear_universe,
    make_multi_sector_universe,
    make_universe,
)


class TestParticipationProfileBuilder:
    def test_bull_above_half(self):
        builder = ParticipationProfileBuilder()
        u = make_bull_universe()
        ps = builder.build(u)
        assert ps.above_ma20_pct >= 0.50   # bull universe has 70% above_ma20

    def test_participation_breadth_multi_sector(self):
        sectors = ["Tech", "Finance", "Healthcare"]
        adv_pcts = [0.80, 0.70, 0.60]
        u = make_multi_sector_universe(sectors, adv_pcts)
        builder = ParticipationProfileBuilder()
        ps = builder.build(u)
        # All sectors > 50% advancing → participation_breadth = 1.0
        assert ps.participation_breadth == pytest.approx(1.0)

    def test_no_sectors(self):
        u = make_universe(50, 50, sectors=["unknown"])
        builder = ParticipationProfileBuilder()
        ps = builder.build(u)
        assert isinstance(ps.sector_participation, dict)

    def test_new_highs_count(self):
        from iios.investment.market.breadth.models import SecurityObservation, UniverseSnapshot
        import time
        obs = [SecurityObservation(f"A{i}", 0.5, is_new_52w_high=True) for i in range(10)]
        obs += [SecurityObservation(f"D{i}", -0.5) for i in range(90)]
        u = UniverseSnapshot("TEST", 0, time.time(), obs)
        builder = ParticipationProfileBuilder()
        ps = builder.build(u)
        assert ps.new_highs == 10
        assert ps.nh_nl_ratio >= 10.0  # no new lows → denominator is 1

    def test_score_range(self):
        builder = ParticipationProfileBuilder()
        for u in [make_bull_universe(), make_bear_universe()]:
            ps = builder.build(u)
            assert 0.0 <= ps.market_participation_score <= 100.0


class TestParticipationEngine:
    def test_update_returns_snapshot(self):
        engine = ParticipationEngine()
        u = make_bull_universe()
        ps = engine.update(u)
        assert ps is not None
        assert engine.current is ps

    def test_history_grows(self):
        engine = ParticipationEngine()
        for i in range(5):
            engine.update(make_bull_universe(bar_index=i))
        assert len(engine.recent(10)) == 5

    def test_history_capped(self):
        engine = ParticipationEngine(history_size=3)
        for i in range(10):
            engine.update(make_bull_universe(bar_index=i))
        assert len(engine.recent(100)) == 3
