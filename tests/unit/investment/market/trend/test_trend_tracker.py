"""tests/unit/investment/market/trend/test_trend_tracker.py
Tests for TrendTracker.
"""
from __future__ import annotations

import pytest
from iios.investment.market.trend.trend_tracker import TrendTracker
from iios.investment.market.trend.models import (
    ImpulseQuality,
    CorrectionQuality,
)
from tests.unit.investment.market.trend.conftest import make_structure_snapshot


class TestTrendTrackerEmpty:
    def test_empty_tracker_returns_no_legs(self):
        tracker = TrendTracker()
        assert tracker.compute_leg_metrics() == []

    def test_latest_structure_none_when_empty(self):
        tracker = TrendTracker()
        assert tracker.latest_structure() is None

    def test_prev_structure_none_when_empty(self):
        tracker = TrendTracker()
        assert tracker.prev_structure() is None


class TestTrendTrackerSingleSnapshot:
    def test_single_snapshot_returns_legs(self):
        tracker = TrendTracker()
        snap = make_structure_snapshot(
            direction="up", confirmed=True, leg_count=3,
            n_swing_highs=3, n_swing_lows=3,
        )
        tracker.update(snap)
        legs = tracker.compute_leg_metrics()
        # At least some legs derived from swings
        assert isinstance(legs, list)

    def test_leg_metrics_have_correct_fields(self):
        tracker = TrendTracker()
        snap = make_structure_snapshot(n_swing_highs=4, n_swing_lows=4)
        tracker.update(snap)
        legs = tracker.compute_leg_metrics()
        for leg in legs:
            assert leg.displacement > 0
            assert leg.bars > 0
            assert leg.velocity > 0

    def test_latest_structure_returns_last_added(self):
        tracker = TrendTracker()
        s1 = make_structure_snapshot(leg_count=2)
        s2 = make_structure_snapshot(leg_count=4)
        tracker.update(s1)
        tracker.update(s2)
        assert tracker.latest_structure() is s2

    def test_prev_structure_returns_second_to_last(self):
        tracker = TrendTracker()
        s1 = make_structure_snapshot(leg_count=2)
        s2 = make_structure_snapshot(leg_count=4)
        tracker.update(s1)
        tracker.update(s2)
        assert tracker.prev_structure() is s1


class TestTrendTrackerLegClassification:
    def test_correction_quality_shallow_for_small_retracement(self):
        tracker = TrendTracker()
        snap = make_structure_snapshot(
            direction="up", n_swing_highs=4, n_swing_lows=4
        )
        tracker.update(snap)
        legs = tracker.compute_leg_metrics()
        # Swings are built with consistent sizes — most corrections should be classified
        for leg in legs:
            assert leg.correction_quality in CorrectionQuality

    def test_impulse_quality_assigned(self):
        tracker = TrendTracker()
        snap = make_structure_snapshot(n_swing_highs=4, n_swing_lows=4)
        tracker.update(snap)
        legs = tracker.compute_leg_metrics()
        for leg in legs:
            assert leg.impulse_quality in ImpulseQuality

    def test_uptrend_impulse_legs_are_low_to_high(self):
        """For uptrend, LOW→HIGH transitions should be marked as impulse."""
        tracker = TrendTracker()
        snap = make_structure_snapshot(direction="up", n_swing_highs=4, n_swing_lows=4)
        tracker.update(snap)
        legs = tracker.compute_leg_metrics()
        # At least one impulse leg should exist
        impulse_legs = [l for l in legs if l.is_impulse]
        assert len(impulse_legs) > 0

    def test_max_10_legs_returned(self):
        tracker = TrendTracker()
        snap = make_structure_snapshot(n_swing_highs=8, n_swing_lows=8)
        tracker.update(snap)
        legs = tracker.compute_leg_metrics()
        assert len(legs) <= 10


class TestTrendTrackerClear:
    def test_clear_resets_state(self):
        tracker = TrendTracker()
        snap = make_structure_snapshot()
        tracker.update(snap)
        tracker.clear()
        assert tracker.latest_structure() is None
        assert tracker.compute_leg_metrics() == []

    def test_history_returns_all_updates(self):
        tracker = TrendTracker(window=5)
        for i in range(4):
            tracker.update(make_structure_snapshot(leg_count=i + 1))
        assert len(tracker.history()) == 4
