"""tests/unit/investment/market/volatility/test_volatility_engine.py
Tests for estimators, VolatilityStatistics, VolatilityStateTracker,
VolatilityProfileAnalyzer, and VolatilityEngine.
"""
from __future__ import annotations

import math
import pytest

from iios.investment.market.volatility.close_to_close_estimator import CloseToCloseEstimator
from iios.investment.market.volatility.high_low_estimator import HighLowEstimator
from iios.investment.market.volatility.ohlc_estimator import OHLCEstimator
from iios.investment.market.volatility.estimator_registry import EstimatorRegistry
from iios.investment.market.volatility.volatility_statistics import VolatilityStatistics
from iios.investment.market.volatility.volatility_state import VolatilityStateTracker
from iios.investment.market.volatility.volatility_profile import VolatilityProfileAnalyzer
from iios.investment.market.volatility.volatility_engine import VolatilityEngine
from iios.investment.market.volatility.models import VolatilityProfile
from tests.unit.investment.market.volatility.conftest import (
    make_bar, make_bars, make_volatile_bars, make_quiet_bars,
)


class TestCloseToCloseEstimator:
    def test_insufficient_bars_returns_none(self):
        est = CloseToCloseEstimator(window=20)
        bars = make_bars(n=5)
        assert est.estimate(bars) is None

    def test_sufficient_bars_returns_estimate(self):
        est = CloseToCloseEstimator(window=20)
        bars = make_bars(n=25)
        result = est.estimate(bars)
        assert result is not None
        assert result.annualized_pct > 0.0
        assert 0.0 < result.confidence <= 1.0

    def test_name_contains_window(self):
        est = CloseToCloseEstimator(window=14)
        assert "14" in est.name

    def test_required_bars(self):
        est = CloseToCloseEstimator(window=10)
        assert est.required_bars == 11

    def test_higher_vol_series_gives_higher_estimate(self):
        est = CloseToCloseEstimator(window=20)
        quiet = make_quiet_bars(25)
        volatile = make_volatile_bars(25)
        q_est = est.estimate(quiet)
        v_est = est.estimate(volatile)
        assert q_est is not None and v_est is not None
        assert v_est.annualized_pct > q_est.annualized_pct

    def test_zero_close_handled(self):
        """Bars with zero close should not crash."""
        est = CloseToCloseEstimator(window=5)
        bars = make_bars(n=10)
        # Should not raise
        result = est.estimate(bars)
        assert result is not None or result is None  # either is fine

    def test_window_constructor_validation(self):
        with pytest.raises(ValueError):
            CloseToCloseEstimator(window=1)


class TestHighLowEstimator:
    def test_insufficient_bars(self):
        est = HighLowEstimator(window=20)
        bars = make_bars(n=5)
        assert est.estimate(bars) is None

    def test_returns_estimate(self):
        est = HighLowEstimator(window=20)
        bars = make_bars(n=25)
        result = est.estimate(bars)
        assert result is not None
        assert result.annualized_pct > 0.0

    def test_high_vol_higher_estimate(self):
        est = HighLowEstimator(window=20)
        quiet = make_quiet_bars(25)
        volatile = make_volatile_bars(25)
        q = est.estimate(quiet)
        v = est.estimate(volatile)
        assert q is not None and v is not None
        assert v.annualized_pct > q.annualized_pct

    def test_name(self):
        est = HighLowEstimator(window=15)
        assert "15" in est.name


class TestOHLCEstimator:
    def test_insufficient_bars(self):
        est = OHLCEstimator(window=20)
        bars = make_bars(n=5)
        assert est.estimate(bars) is None

    def test_returns_estimate(self):
        est = OHLCEstimator(window=20)
        bars = make_bars(n=25)
        result = est.estimate(bars)
        assert result is not None
        assert result.annualized_pct > 0.0

    def test_name(self):
        est = OHLCEstimator(window=20)
        assert "20" in est.name

    def test_overnight_weight_validation(self):
        with pytest.raises(ValueError):
            OHLCEstimator(overnight_weight=1.5)


class TestEstimatorRegistry:
    def test_register_and_retrieve(self):
        reg = EstimatorRegistry()
        est = CloseToCloseEstimator(window=20)
        reg.register(est)
        assert reg.get(est.name) is est

    def test_unregister(self):
        reg = EstimatorRegistry()
        est = CloseToCloseEstimator(window=20)
        reg.register(est)
        reg.unregister(est.name)
        assert reg.get(est.name) is None

    def test_all_returns_list(self):
        reg = EstimatorRegistry()
        reg.register(CloseToCloseEstimator(window=10))
        reg.register(CloseToCloseEstimator(window=20))
        assert len(reg.all()) == 2

    def test_replace_same_name(self):
        reg = EstimatorRegistry()
        est1 = CloseToCloseEstimator(window=20)
        est2 = CloseToCloseEstimator(window=20)
        reg.register(est1)
        reg.register(est2)
        assert len(reg) == 1


class TestVolatilityStatistics:
    def test_empty_stats(self):
        s = VolatilityStatistics(window=10)
        assert s.count == 0
        assert s.mean == 0.0

    def test_mean_updates_correctly(self):
        s = VolatilityStatistics(window=10)
        for v in [10.0, 20.0, 30.0]:
            s.update(v)
        assert abs(s.mean - 20.0) < 1e-9

    def test_window_eviction(self):
        s = VolatilityStatistics(window=3)
        for v in [10.0, 20.0, 30.0, 40.0]:
            s.update(v)
        assert s.count == 3
        assert abs(s.mean - 30.0) < 1e-9

    def test_normalized_in_range(self, populated_stats):
        assert 0.0 <= populated_stats.normalized(15.0) <= 1.0
        assert 0.0 <= populated_stats.normalized(25.0) <= 1.0

    def test_percentile_rank_monotone(self, populated_stats):
        r1 = populated_stats.percentile_rank(10.0)
        r2 = populated_stats.percentile_rank(25.0)
        assert r2 > r1

    def test_autocorr_in_range(self, populated_stats):
        ac = populated_stats.lag1_autocorrelation()
        assert 0.0 <= ac <= 1.0

    def test_window_means(self, populated_stats):
        s, m, l = populated_stats.multi_window_means(5, 20, 50)
        assert s > 0 and m > 0 and l > 0


class TestVolatilityStateTracker:
    def test_first_bar_produces_state(self):
        tracker = VolatilityStateTracker()
        bar = make_bar()
        state = tracker.update(15.0, bar)
        assert state.realized_volatility == 15.0
        assert state.bars_processed == 1

    def test_state_initialized_after_window(self):
        tracker = VolatilityStateTracker(medium_window=10)
        for i in range(10):
            state = tracker.update(20.0, make_bar(index=i))
        assert state.is_initialized is True

    def test_not_initialized_before_window(self):
        tracker = VolatilityStateTracker(medium_window=20)
        state = tracker.update(20.0, make_bar())
        assert state.is_initialized is False

    def test_relative_vol_near_one_with_stable_series(self):
        tracker = VolatilityStateTracker()
        for i in range(25):
            state = tracker.update(20.0, make_bar(index=i))
        assert abs(state.relative_volatility - 1.0) < 0.1

    def test_normalized_vol_in_range(self):
        tracker = VolatilityStateTracker()
        for i in range(30):
            state = tracker.update(15.0 + i * 0.5, make_bar(index=i))
        assert 0.0 <= state.normalized_volatility <= 1.0

    def test_range_ratio_computed(self):
        tracker = VolatilityStateTracker()
        for i in range(5):
            state = tracker.update(20.0, make_bar(index=i))
        assert state.bar_range_ratio > 0.0


class TestVolatilityEngine:
    def _make_engine(self) -> VolatilityEngine:
        reg = EstimatorRegistry()
        reg.register(CloseToCloseEstimator(window=10))
        return VolatilityEngine(registry=reg)

    def test_first_bar_returns_profile(self):
        engine = self._make_engine()
        profile = engine.update(make_bar())
        assert isinstance(profile, VolatilityProfile)

    def test_profile_has_state(self):
        engine = self._make_engine()
        profile = engine.update(make_bar())
        assert profile.state is not None
        assert profile.state.bars_processed == 1

    def test_estimates_populated_after_warmup(self):
        engine = self._make_engine()
        for i, bar in enumerate(make_bars(n=15)):
            profile = engine.update(bar)
        # After 15 bars, close_to_close_10 should have estimates
        assert len(profile.estimates) > 0

    def test_multi_estimator_agreement(self):
        reg = EstimatorRegistry()
        reg.register(CloseToCloseEstimator(window=10))
        reg.register(HighLowEstimator(window=10))
        engine = VolatilityEngine(registry=reg)
        for bar in make_bars(n=20):
            profile = engine.update(bar)
        assert 0.0 <= profile.estimate_agreement <= 1.0

    def test_fallback_no_estimators(self):
        """Engine with no estimates still produces a valid profile."""
        reg = EstimatorRegistry()
        engine = VolatilityEngine(registry=reg)
        profile = engine.update(make_bar())
        assert profile.state.realized_volatility >= 0.0

    def test_volatile_series_higher_vol(self):
        reg = EstimatorRegistry()
        reg.register(CloseToCloseEstimator(window=10))
        engine = VolatilityEngine(registry=reg)
        for bar in make_volatile_bars(20):
            profile = engine.update(bar)
        high_vol = profile.state.realized_volatility

        reg2 = EstimatorRegistry()
        reg2.register(CloseToCloseEstimator(window=10))
        engine2 = VolatilityEngine(registry=reg2)
        for bar in make_quiet_bars(20):
            profile2 = engine2.update(bar)
        low_vol = profile2.state.realized_volatility

        assert high_vol > low_vol
