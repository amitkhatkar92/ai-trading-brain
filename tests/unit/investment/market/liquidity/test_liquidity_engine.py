"""tests/unit/investment/market/liquidity/test_liquidity_engine.py"""
from __future__ import annotations

import pytest

from iios.investment.market.liquidity.models import ParticipationBias
from iios.investment.market.liquidity.liquidity_profile import LiquidityProfileAnalyzer
from iios.investment.market.liquidity.liquidity_score import LiquidityScoreCalculator
from iios.investment.market.liquidity.liquidity_history import LiquidityHistory
from iios.investment.market.liquidity.liquidity_engine import LiquidityEngine
from iios.investment.market.liquidity.models import (
    LiquidityProfile, ParticipationSnapshot, VolumeProfile, VolumeTrend,
)

from tests.unit.investment.market.liquidity.conftest import make_volume_bar, make_bars
from iios.investment.market.liquidity.volume_engine import VolumeEngine
from iios.investment.market.liquidity.participation_engine import ParticipationEngine


def make_participation(score: float = 50.0) -> ParticipationSnapshot:
    return ParticipationSnapshot(
        buying_participation=0.5, selling_participation=0.5,
        institutional_participation=0.4, retail_participation=0.6,
        participation_balance=0.0, participation_bias=ParticipationBias.NEUTRAL,
        participation_confidence=0.7, participation_score=score,
    )


def make_volume_profile(avg_vol: float = 100_000.0) -> VolumeProfile:
    return VolumeProfile(
        period_bars=20, avg_volume=avg_vol, std_volume=5000.0,
        median_volume=avg_vol, peak_volume=avg_vol * 2,
        min_volume=avg_vol * 0.5, recent_avg=avg_vol,
        volume_trend=VolumeTrend.STABLE,
        up_volume=avg_vol * 10, down_volume=avg_vol * 10,
        up_down_ratio=1.0,
    )


class TestLiquidityProfileAnalyzer:
    def setup_method(self):
        self.analyzer = LiquidityProfileAnalyzer()

    def test_analyze_returns_profile(self):
        vbars = [make_volume_bar(index=i, volume=100_000.0, relative_volume=1.0) for i in range(20)]
        profile = self.analyzer.analyze(vbars, 100_000.0, 200_000.0)
        assert profile is not None

    def test_all_fields_in_valid_ranges(self):
        vbars = [make_volume_bar(index=i, volume=100_000.0, relative_volume=1.0) for i in range(20)]
        p = self.analyzer.analyze(vbars, 100_000.0, 200_000.0)
        assert 0.0 <= p.availability <= 1.0
        assert 0.0 <= p.stability <= 1.0
        assert 0.0 <= p.depth <= 1.0
        assert 0.0 <= p.concentration <= 1.0
        assert 0.0 <= p.fragmentation <= 1.0
        assert 0.0 <= p.quality <= 100.0
        assert 0.0 <= p.liquidity_confidence <= 1.0

    def test_high_volume_bars_high_availability(self):
        vbars = [make_volume_bar(index=i, relative_volume=2.0, volume=200_000.0) for i in range(20)]
        p = self.analyzer.analyze(vbars, 100_000.0, 300_000.0)
        assert p.availability > 0.5

    def test_low_volume_bars_low_availability(self):
        vbars = [make_volume_bar(index=i, relative_volume=0.2, volume=20_000.0) for i in range(20)]
        p = self.analyzer.analyze(vbars, 100_000.0, 300_000.0)
        assert p.availability < 0.3

    def test_stable_volumes_high_stability(self):
        vbars = [make_volume_bar(index=i, volume=100_000.0) for i in range(20)]
        p = self.analyzer.analyze(vbars, 100_000.0, 200_000.0)
        assert p.stability > 0.8

    def test_spike_increases_concentration(self):
        vbars = [make_volume_bar(index=i, volume=10_000.0) for i in range(9)]
        vbars.append(make_volume_bar(index=9, volume=500_000.0))
        p = self.analyzer.analyze(vbars, 100_000.0, 500_000.0)
        assert p.concentration > 0.5

    def test_empty_returns_zero_profile(self):
        p = self.analyzer.analyze([], 0.0, 0.0)
        assert p.quality == 0.0


class TestLiquidityScoreCalculator:
    def setup_method(self):
        self.calc = LiquidityScoreCalculator()

    def test_returns_float_in_range(self):
        lp = LiquidityProfile(
            availability=0.7, stability=0.8, depth=0.6,
            concentration=0.3, fragmentation=0.7, quality=70.0,
            liquidity_confidence=0.75,
        )
        p = make_participation(score=60.0)
        vp = make_volume_profile()
        score = self.calc.calculate(lp, p, 70.0, vp)
        assert 0.0 <= score <= 100.0

    def test_volatile_regime_lower_score(self):
        from iios.investment.market.regime.models import RegimeType
        lp = LiquidityProfile(
            availability=0.7, stability=0.8, depth=0.6,
            concentration=0.3, fragmentation=0.7, quality=70.0,
            liquidity_confidence=0.75,
        )
        p = make_participation(score=60.0)
        vp = make_volume_profile()
        normal = self.calc.calculate(lp, p, 70.0, vp, None)
        volatile = self.calc.calculate(lp, p, 70.0, vp, RegimeType.VOLATILE)
        assert volatile < normal

    def test_calm_regime_higher_score(self):
        from iios.investment.market.regime.models import RegimeType
        lp = LiquidityProfile(
            availability=0.5, stability=0.5, depth=0.5,
            concentration=0.5, fragmentation=0.5, quality=50.0,
            liquidity_confidence=0.5,
        )
        p = make_participation(score=50.0)
        vp = make_volume_profile()
        normal = self.calc.calculate(lp, p, 50.0, vp, None)
        calm = self.calc.calculate(lp, p, 50.0, vp, RegimeType.CALM)
        assert calm > normal

    def test_high_volume_quality_higher_score(self):
        lp = LiquidityProfile(
            availability=0.7, stability=0.7, depth=0.7,
            concentration=0.3, fragmentation=0.7, quality=70.0,
            liquidity_confidence=0.7,
        )
        p = make_participation(score=70.0)
        vp = make_volume_profile()
        s_low = self.calc.calculate(lp, p, 10.0, vp)
        s_high = self.calc.calculate(lp, p, 90.0, vp)
        assert s_high > s_low


class TestLiquidityHistory:
    def test_record_and_last(self):
        hist = LiquidityHistory(max_size=100)
        lp = LiquidityProfile(
            availability=0.7, stability=0.8, depth=0.6,
            concentration=0.3, fragmentation=0.7, quality=70.0,
            liquidity_confidence=0.75,
        )
        hist.record(lp)
        assert hist.last() is lp

    def test_count(self):
        hist = LiquidityHistory(max_size=100)
        for _ in range(5):
            hist.record(LiquidityProfile(
                availability=0.5, stability=0.5, depth=0.5,
                concentration=0.5, fragmentation=0.5, quality=50.0,
                liquidity_confidence=0.5,
            ))
        assert hist.count() == 5

    def test_avg_quality(self):
        hist = LiquidityHistory(max_size=100)
        for q in [40.0, 60.0, 80.0]:
            hist.record(LiquidityProfile(
                availability=0.5, stability=0.5, depth=0.5,
                concentration=0.5, fragmentation=0.5, quality=q,
                liquidity_confidence=0.5,
            ))
        assert abs(hist.avg_quality(3) - 60.0) < 1e-6


class TestLiquidityEngine:
    def _make_vbars(self, n=20, rel_vol=1.0):
        return [make_volume_bar(index=i, volume=100_000.0, relative_volume=rel_vol) for i in range(n)]

    def test_update_returns_profile_and_score(self):
        engine = LiquidityEngine(window=20)
        vbars = self._make_vbars()
        p = make_participation()
        vp = make_volume_profile()
        profile, score = engine.update(vbars, 100_000.0, p, 70.0, vp)
        assert profile is not None
        assert 0.0 <= score <= 100.0

    def test_is_liquid_respects_threshold(self):
        engine = LiquidityEngine(window=20)
        vbars = self._make_vbars(rel_vol=2.0)
        p = make_participation(score=80.0)
        vp = make_volume_profile()
        _, score = engine.update(vbars, 100_000.0, p, 80.0, vp)
        assert engine.is_liquid(threshold=0.0) is True

    def test_current_profile_updates(self):
        engine = LiquidityEngine(window=20)
        assert engine.current_profile() is None
        vbars = self._make_vbars()
        engine.update(vbars, 100_000.0, make_participation(), 70.0, make_volume_profile())
        assert engine.current_profile() is not None
