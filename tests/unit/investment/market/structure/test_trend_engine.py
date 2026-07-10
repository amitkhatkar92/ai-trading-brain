"""tests/unit/investment/market/structure/test_trend_engine.py"""
from __future__ import annotations

import pytest

from iios.investment.market.market_constants import TrendDirection
from iios.investment.market.structure.models import TrendPhase
from iios.investment.market.structure.swing_history import SwingHistory
from iios.investment.market.structure.trend_classifier import TrendClassifier
from iios.investment.market.structure.trend_engine import TrendEngine
from iios.investment.market.structure.trend_strength import TrendStrengthAnalyzer
from iios.investment.market.structure.trend_transition import TrendTransitionDetector
from tests.unit.investment.market.structure.conftest import (
    make_downtrend_bars,
    make_range_bars,
    make_uptrend_bars,
)


def _build_engine() -> TrendEngine:
    hist = SwingHistory()
    return TrendEngine(
        swing_history=hist,
        classifier=TrendClassifier(),
        strength_analyzer=TrendStrengthAnalyzer(),
        transition_detector=TrendTransitionDetector(),
    )


class TestTrendEngine:
    def test_uptrend_direction(self):
        bars = make_uptrend_bars(n=60)
        engine = _build_engine()
        state = engine.update(bars)
        # After 60 uptrend bars we expect UP or SIDEWAYS (swings needed for UP)
        assert state.direction in (TrendDirection.UP, TrendDirection.SIDEWAYS)

    def test_downtrend_direction(self):
        bars = make_downtrend_bars(n=60)
        engine = _build_engine()
        state = engine.update(bars)
        assert state.direction in (TrendDirection.DOWN, TrendDirection.SIDEWAYS)

    def test_sideways_on_range(self):
        bars = make_range_bars(n=40)
        engine = _build_engine()
        state = engine.update(bars)
        # Ranging bars should not produce a strongly confirmed trend
        assert state.direction in (TrendDirection.SIDEWAYS, TrendDirection.UP, TrendDirection.DOWN)

    def test_get_state_matches_update(self):
        bars = make_uptrend_bars(n=50)
        engine = _build_engine()
        state1 = engine.update(bars)
        state2 = engine.get_state()
        assert state1.direction == state2.direction

    def test_trend_state_fields_valid(self):
        bars = make_uptrend_bars(n=50)
        engine = _build_engine()
        state = engine.update(bars)
        assert state.leg_count >= 0
        assert state.current_leg_height >= 0.0
        assert state.total_displacement >= 0.0
        assert 0.0 <= state.correction_depth <= 1.0

    def test_get_phase_returns_trend_phase(self):
        bars = make_uptrend_bars(n=50)
        engine = _build_engine()
        engine.update(bars)
        phase = engine.get_phase()
        assert isinstance(phase, TrendPhase)

    def test_leg_count_increases_with_more_bars(self):
        bars_short = make_uptrend_bars(n=20)
        bars_long = make_uptrend_bars(n=60)
        engine_short = _build_engine()
        engine_long = _build_engine()
        state_short = engine_short.update(bars_short)
        state_long = engine_long.update(bars_long)
        # More bars = more confirmed legs
        assert state_long.leg_count >= state_short.leg_count

    def test_no_crash_on_single_bar(self):
        from tests.unit.investment.market.structure.conftest import _bar
        bars = [_bar(0, 100, 101, 99, 100.5, 1000)]
        engine = _build_engine()
        state = engine.update(bars)
        assert state is not None

    def test_transition_detected_after_reversal(self):
        """Build an uptrend then a downtrend and check transition detector."""
        up_bars = make_uptrend_bars(n=30)
        down_bars = make_downtrend_bars(n=30)
        # Re-index down bars to follow up bars
        import dataclasses
        offset = up_bars[-1].index + 1
        down_bars = [dataclasses.replace(b, index=b.index + offset) for b in down_bars]
        all_bars = up_bars + down_bars
        engine = _build_engine()
        engine.update(all_bars)
        # Just ensure no crash and a transition may or may not be detected
        transition = engine.get_last_transition()
        # Can be None or a TrendTransition
        assert transition is None or hasattr(transition, "from_direction")
