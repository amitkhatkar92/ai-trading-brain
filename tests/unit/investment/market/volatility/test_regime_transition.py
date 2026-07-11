"""tests/unit/investment/market/volatility/test_regime_transition.py"""
from __future__ import annotations

import pytest

from iios.investment.market.volatility.regime_transition import RegimeTransitionDetector
from iios.investment.market.volatility.models import (
    VolatilityEventType,
    VolatilityRegimeType,
)


class TestRegimeTransitionDetector:
    def test_initial_state(self):
        det = RegimeTransitionDetector()
        assert det.current_regime is None
        assert det.duration_bars == 0
        assert det.previous_regime is None

    def test_first_update_no_event(self):
        det = RegimeTransitionDetector()
        event = det.update(VolatilityRegimeType.NORMAL, 0, "TEST", "1d")
        assert event is None
        assert det.current_regime == VolatilityRegimeType.NORMAL

    def test_same_regime_increments_duration(self):
        det = RegimeTransitionDetector()
        det.update(VolatilityRegimeType.NORMAL, 0, "TEST", "1d")
        det.update(VolatilityRegimeType.NORMAL, 1, "TEST", "1d")
        det.update(VolatilityRegimeType.NORMAL, 2, "TEST", "1d")
        assert det.duration_bars == 3

    def test_regime_change_emits_event(self):
        det = RegimeTransitionDetector()
        det.update(VolatilityRegimeType.NORMAL, 0, "TEST", "1d")
        event = det.update(VolatilityRegimeType.HIGH, 1, "TEST", "1d")
        assert event is not None
        assert event.event_type == VolatilityEventType.REGIME_CHANGE
        assert event.from_regime == VolatilityRegimeType.NORMAL
        assert event.to_regime == VolatilityRegimeType.HIGH

    def test_transition_severity_proportional_to_distance(self):
        det = RegimeTransitionDetector()
        det.update(VolatilityRegimeType.VERY_LOW, 0, "T", "1d")
        ev_far = det.update(VolatilityRegimeType.SHOCK, 1, "T", "1d")

        det2 = RegimeTransitionDetector()
        det2.update(VolatilityRegimeType.NORMAL, 0, "T", "1d")
        ev_near = det2.update(VolatilityRegimeType.ELEVATED, 1, "T", "1d")

        assert ev_far.severity > ev_near.severity

    def test_duration_resets_after_transition(self):
        det = RegimeTransitionDetector()
        det.update(VolatilityRegimeType.NORMAL, 0, "T", "1d")
        det.update(VolatilityRegimeType.NORMAL, 1, "T", "1d")
        det.update(VolatilityRegimeType.HIGH, 2, "T", "1d")
        assert det.duration_bars == 1

    def test_previous_regime_tracked(self):
        det = RegimeTransitionDetector()
        det.update(VolatilityRegimeType.LOW, 0, "T", "1d")
        det.update(VolatilityRegimeType.NORMAL, 1, "T", "1d")
        assert det.previous_regime == VolatilityRegimeType.LOW

    def test_recent_transitions_history(self):
        det = RegimeTransitionDetector()
        det.update(VolatilityRegimeType.LOW, 0, "T", "1d")
        det.update(VolatilityRegimeType.NORMAL, 1, "T", "1d")
        det.update(VolatilityRegimeType.HIGH, 2, "T", "1d")
        transitions = det.recent_transitions()
        assert len(transitions) == 2

    def test_event_description_not_empty(self):
        det = RegimeTransitionDetector()
        det.update(VolatilityRegimeType.NORMAL, 0, "T", "1d")
        ev = det.update(VolatilityRegimeType.HIGH, 1, "T", "1d")
        assert ev is not None
        assert len(ev.description) > 0
