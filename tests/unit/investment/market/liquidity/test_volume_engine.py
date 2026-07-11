"""tests/unit/investment/market/liquidity/test_volume_engine.py"""
from __future__ import annotations

import pytest

from iios.investment.market.liquidity.models import VolumeLevel, VolumeTrend
from iios.investment.market.liquidity.volume_statistics import VolumeStatistics
from iios.investment.market.liquidity.volume_history import VolumeHistory
from iios.investment.market.liquidity.volume_profile import VolumeProfileAnalyzer
from iios.investment.market.liquidity.volume_engine import VolumeEngine

from tests.unit.investment.market.liquidity.conftest import (
    make_bar, make_up_bar, make_down_bar, make_bars, make_volume_bar,
)


class TestVolumeStatistics:
    def test_empty_state(self):
        stats = VolumeStatistics(window=20)
        assert stats.avg == 0.0
        assert stats.std == 0.0
        assert stats.peak == 0.0
        assert stats.minimum == 0.0
        assert stats.count == 0

    def test_after_updates_avg(self):
        stats = VolumeStatistics(window=20)
        for v in [100.0, 200.0, 300.0]:
            stats.update(v)
        assert abs(stats.avg - 200.0) < 1e-6

    def test_after_updates_peak_min(self):
        stats = VolumeStatistics(window=20)
        for v in [100.0, 200.0, 300.0]:
            stats.update(v)
        assert stats.peak == 300.0
        assert stats.minimum == 100.0

    def test_std_nontrivial(self):
        stats = VolumeStatistics(window=20)
        for v in [100.0, 100.0, 200.0, 200.0]:
            stats.update(v)
        assert stats.std > 0.0

    def test_relative_volume(self):
        stats = VolumeStatistics(window=20)
        for _ in range(10):
            stats.update(100.0)
        assert abs(stats.relative(200.0) - 2.0) < 1e-6

    def test_relative_zero_avg(self):
        stats = VolumeStatistics(window=20)
        assert stats.relative(100.0) == 1.0

    def test_normalized_clamped_to_1(self):
        stats = VolumeStatistics(window=20)
        for v in [100.0, 200.0]:
            stats.update(v)
        assert stats.normalized(1_000_000.0) == 1.0

    def test_normalized_empty(self):
        stats = VolumeStatistics(window=20)
        assert stats.normalized(100.0) == 0.0

    def test_classify_extreme_high(self):
        stats = VolumeStatistics(window=20)
        for _ in range(20):
            stats.update(100.0)
        assert stats.classify(400.0) == VolumeLevel.EXTREME_HIGH

    def test_classify_very_high(self):
        stats = VolumeStatistics(window=20)
        for _ in range(20):
            stats.update(100.0)
        assert stats.classify(250.0) == VolumeLevel.VERY_HIGH

    def test_classify_high(self):
        stats = VolumeStatistics(window=20)
        for _ in range(20):
            stats.update(100.0)
        assert stats.classify(175.0) == VolumeLevel.HIGH

    def test_classify_above_average(self):
        stats = VolumeStatistics(window=20)
        for _ in range(20):
            stats.update(100.0)
        assert stats.classify(130.0) == VolumeLevel.ABOVE_AVERAGE

    def test_classify_average(self):
        stats = VolumeStatistics(window=20)
        for _ in range(20):
            stats.update(100.0)
        assert stats.classify(100.0) == VolumeLevel.AVERAGE

    def test_classify_below_average(self):
        stats = VolumeStatistics(window=20)
        for _ in range(20):
            stats.update(100.0)
        assert stats.classify(60.0) == VolumeLevel.BELOW_AVERAGE

    def test_classify_low(self):
        stats = VolumeStatistics(window=20)
        for _ in range(20):
            stats.update(100.0)
        assert stats.classify(30.0) == VolumeLevel.LOW

    def test_classify_none_for_zero_volume(self):
        stats = VolumeStatistics(window=20)
        for _ in range(20):
            stats.update(100.0)
        assert stats.classify(0.0) == VolumeLevel.NONE

    def test_window_respects_maxlen(self):
        stats = VolumeStatistics(window=5)
        for i in range(10):
            stats.update(float(i * 100))
        assert stats.count == 5

    def test_median_odd(self):
        stats = VolumeStatistics(window=10)
        for v in [10.0, 30.0, 20.0]:
            stats.update(v)
        assert stats.median == 20.0

    def test_recent_avg(self):
        stats = VolumeStatistics(window=20)
        for i in range(10):
            stats.update(float(i + 1) * 10.0)  # 10, 20, ..., 100
        assert abs(stats.recent_avg(5) - 80.0) < 1e-6  # last 5: 60,70,80,90,100


class TestVolumeHistory:
    def test_record_and_last(self):
        hist = VolumeHistory(max_size=100)
        vbar = make_volume_bar(index=0)
        hist.record(vbar)
        assert hist.last() is vbar

    def test_count(self):
        hist = VolumeHistory(max_size=100)
        for i in range(5):
            hist.record(make_volume_bar(index=i))
        assert hist.count() == 5

    def test_ring_buffer_respects_max_size(self):
        hist = VolumeHistory(max_size=3)
        for i in range(10):
            hist.record(make_volume_bar(index=i))
        assert hist.count() == 3

    def test_recent_returns_last_n(self):
        hist = VolumeHistory(max_size=100)
        for i in range(10):
            hist.record(make_volume_bar(index=i))
        recent = hist.recent(3)
        assert len(recent) == 3
        assert recent[-1].index == 9

    def test_up_volume_last_n(self):
        hist = VolumeHistory(max_size=100)
        for i in range(5):
            hist.record(make_volume_bar(index=i, is_up=True, volume=100_000.0))
        for i in range(5, 10):
            hist.record(make_volume_bar(index=i, is_up=False, volume=100_000.0))
        up = hist.up_volume_last_n(5)
        assert up == 0.0  # last 5 are down

    def test_down_volume_last_n(self):
        hist = VolumeHistory(max_size=100)
        for i in range(5):
            hist.record(make_volume_bar(index=i, is_up=False, volume=100_000.0))
        down = hist.down_volume_last_n(5)
        assert down == 500_000.0

    def test_empty_last_returns_none(self):
        hist = VolumeHistory()
        assert hist.last() is None


class TestVolumeProfileAnalyzer:
    def test_analyze_returns_volume_profile(self):
        analyzer = VolumeProfileAnalyzer()
        vbars = [make_volume_bar(index=i, volume=100_000.0) for i in range(20)]
        profile = analyzer.analyze(vbars, window=20)
        assert profile.period_bars == 20
        assert profile.avg_volume > 0

    def test_all_fields_present(self):
        analyzer = VolumeProfileAnalyzer()
        vbars = [make_volume_bar(index=i, volume=100_000.0) for i in range(20)]
        profile = analyzer.analyze(vbars, window=20)
        assert profile.std_volume >= 0
        assert profile.peak_volume >= profile.min_volume
        assert profile.up_down_ratio >= 0

    def test_volume_trend_expanding(self):
        """Recent volume much higher than older → EXPANDING."""
        analyzer = VolumeProfileAnalyzer()
        vbars = [make_volume_bar(index=i, volume=100_000.0) for i in range(15)]
        # Last 5 bars: very high volume
        for i in range(15, 20):
            vbars.append(make_volume_bar(index=i, volume=300_000.0))
        profile = analyzer.analyze(vbars, window=20)
        assert profile.volume_trend == VolumeTrend.EXPANDING

    def test_volume_trend_contracting(self):
        """Recent volume much lower → CONTRACTING."""
        analyzer = VolumeProfileAnalyzer()
        vbars = [make_volume_bar(index=i, volume=300_000.0) for i in range(15)]
        for i in range(15, 20):
            vbars.append(make_volume_bar(index=i, volume=50_000.0))
        profile = analyzer.analyze(vbars, window=20)
        assert profile.volume_trend == VolumeTrend.CONTRACTING

    def test_empty_bars_returns_defaults(self):
        analyzer = VolumeProfileAnalyzer()
        profile = analyzer.analyze([], window=20)
        assert profile.period_bars == 0
        assert profile.volume_trend == VolumeTrend.STABLE


class TestVolumeEngine:
    def test_update_returns_tuple(self):
        engine = VolumeEngine(window=20)
        bar = make_bar()
        vbar, profile = engine.update(bar)
        assert vbar is not None
        assert profile is not None

    def test_vbar_fields_up_bar(self):
        engine = VolumeEngine(window=20)
        for i in range(19):
            engine.update(make_bar(index=i))
        bar = make_up_bar(index=19, volume=150_000.0)
        vbar, _ = engine.update(bar)
        assert vbar.is_up is True
        assert 0.0 <= vbar.close_position <= 1.0
        assert 0.0 <= vbar.body_pct <= 1.0

    def test_vbar_fields_down_bar(self):
        engine = VolumeEngine(window=20)
        for i in range(19):
            engine.update(make_bar(index=i))
        bar = make_down_bar(index=19, volume=150_000.0)
        vbar, _ = engine.update(bar)
        assert vbar.is_up is False
        assert vbar.close_position < 0.5

    def test_close_position_in_range(self):
        engine = VolumeEngine(window=20)
        bars = make_bars(30)
        for bar in bars:
            vbar, _ = engine.update(bar)
            assert 0.0 <= vbar.close_position <= 1.0

    def test_body_pct_in_range(self):
        engine = VolumeEngine(window=20)
        bars = make_bars(30)
        for bar in bars:
            vbar, _ = engine.update(bar)
            assert 0.0 <= vbar.body_pct <= 1.0

    def test_initialize_with_bars(self):
        engine = VolumeEngine(window=20)
        bars = make_bars(25)
        vbar, profile = engine.initialize(bars)
        assert vbar is not None
        assert profile.period_bars > 0

    def test_current_profile_updates(self):
        engine = VolumeEngine(window=20)
        assert engine.current_profile() is None
        engine.update(make_bar())
        assert engine.current_profile() is not None

    def test_volume_level_none_for_zero(self):
        engine = VolumeEngine(window=20)
        bar = make_bar(volume=0.0)
        vbar, _ = engine.update(bar)
        assert vbar.volume_level == VolumeLevel.NONE
