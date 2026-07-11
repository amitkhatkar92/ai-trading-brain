"""test_internal_strength.py — tests for internal strength and market health."""
from __future__ import annotations

import pytest

from iios.investment.market.breadth.models import (
    BreadthData,
    BreadthTrend,
    HealthTrend,
    ParticipationSnapshot,
)
from iios.investment.market.breadth import internal_strength as ist
from iios.investment.market.breadth.market_health import MarketHealthAnalyzer

from tests.unit.investment.market.breadth.conftest import (
    make_bull_universe,
    make_bear_universe,
)

# Helpers defined locally
def _make_ps(
    above_ma20=0.65, above_ma50=0.55, nh_nl=4.0, part_breadth=0.80,
    sector_participation=None, large=0.70, mid=0.60, small=0.50,
) -> ParticipationSnapshot:
    return ParticipationSnapshot(
        large_cap_pct=large, mid_cap_pct=mid, small_cap_pct=small,
        sector_participation=sector_participation or {},
        above_ma20_pct=above_ma20, above_ma50_pct=above_ma50,
        new_highs=20, new_lows=5, nh_nl_ratio=nh_nl,
        market_participation_score=72.0,
        participation_breadth=part_breadth,
    )


def _make_bd(breadth_pct=0.70, ad_ratio=3.5, stability=0.8) -> BreadthData:
    return BreadthData(
        advancing=int(100 * breadth_pct), declining=int(100 * (1 - breadth_pct)),
        unchanged=0, total=100, breadth_pct=breadth_pct, ad_ratio=ad_ratio,
        ad_line=10.0, ad_momentum=0.0, breadth_trend=BreadthTrend.RISING,
        breadth_stability=stability, metric_values={},
    )


class TestInternalStrength:
    def test_strong_bull(self):
        bd = _make_bd(breadth_pct=0.80, ad_ratio=4.0)
        ps = _make_ps(above_ma20=0.75, above_ma50=0.65, nh_nl=5.0)
        score = ist.internal_strength_score(bd, ps)
        assert 0.0 <= score <= 1.0
        assert score >= 0.60  # strong bull

    def test_bear_low_score(self):
        bd = _make_bd(breadth_pct=0.20, ad_ratio=0.25)
        ps = _make_ps(above_ma20=0.20, above_ma50=0.15, nh_nl=0.2)
        score = ist.internal_strength_score(bd, ps)
        assert score < 0.40

    def test_neutral_midrange(self):
        bd = _make_bd(breadth_pct=0.50, ad_ratio=1.0)
        ps = _make_ps(above_ma20=0.50, above_ma50=0.50, nh_nl=1.0)
        score = ist.internal_strength_score(bd, ps)
        assert 0.30 <= score <= 0.70

    def test_always_0_to_1(self):
        for pct in [0.0, 0.25, 0.50, 0.75, 1.0]:
            bd = _make_bd(breadth_pct=pct)
            ps = _make_ps(above_ma20=pct, above_ma50=pct)
            s = ist.internal_strength_score(bd, ps)
            assert 0.0 <= s <= 1.0

    def test_momentum_positive_when_improving(self):
        bd = _make_bd(breadth_pct=0.70)
        mom = ist.internal_momentum(bd, prev_breadth_pct=0.50)
        assert mom > 0

    def test_momentum_negative_when_declining(self):
        bd = _make_bd(breadth_pct=0.30)
        mom = ist.internal_momentum(bd, prev_breadth_pct=0.60)
        assert mom < 0

    def test_momentum_clamped(self):
        bd = _make_bd(breadth_pct=1.0)
        mom = ist.internal_momentum(bd, prev_breadth_pct=0.0)
        assert mom <= 1.0


class TestMarketHealthAnalyzer:
    def test_bull_health_high(self):
        analyzer = MarketHealthAnalyzer()
        bd = _make_bd(breadth_pct=0.80)
        ps = _make_ps(above_ma20=0.80, above_ma50=0.70, part_breadth=0.90)
        health = analyzer.analyze(bd, ps)
        assert health.health_score >= 50.0

    def test_bear_health_low(self):
        analyzer = MarketHealthAnalyzer()
        bd = _make_bd(breadth_pct=0.20)
        ps = _make_ps(above_ma20=0.20, above_ma50=0.15, part_breadth=0.20)
        health = analyzer.analyze(bd, ps)
        assert health.health_score < 50.0

    def test_health_trend_improving(self):
        analyzer = MarketHealthAnalyzer()
        # Prime with low health
        bd_low = _make_bd(0.30)
        ps_low = _make_ps(above_ma20=0.30, part_breadth=0.30)
        analyzer.analyze(bd_low, ps_low)
        # Then go high
        bd_high = _make_bd(0.80)
        ps_high = _make_ps(above_ma20=0.80, part_breadth=0.90)
        health = analyzer.analyze(bd_high, ps_high)
        assert health.health_trend == HealthTrend.IMPROVING

    def test_health_score_bounds(self):
        analyzer = MarketHealthAnalyzer()
        for pct in [0.0, 0.5, 1.0]:
            bd = _make_bd(breadth_pct=pct)
            ps = _make_ps(above_ma20=pct, above_ma50=pct)
            h = analyzer.analyze(bd, ps)
            assert 0.0 <= h.health_score <= 100.0

    def test_leading_lagging_sectors(self):
        analyzer = MarketHealthAnalyzer()
        bd = _make_bd(0.70)
        ps = _make_ps(
            sector_participation={"Tech": 0.90, "Finance": 0.60, "Energy": 0.30},
            part_breadth=0.67,
        )
        health = analyzer.analyze(bd, ps)
        assert isinstance(health.leading_sectors, list)
        assert isinstance(health.lagging_sectors, list)
