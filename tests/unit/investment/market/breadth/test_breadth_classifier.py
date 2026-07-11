"""test_breadth_classifier.py — tests for BreadthClassifier and BreadthTransitionDetector."""
from __future__ import annotations

import pytest

from iios.investment.market.breadth.models import (
    BreadthData,
    BreadthEvent,
    BreadthEventType,
    BreadthRegimeType,
    BreadthTrend,
    HealthTrend,
    MarketHealthSnapshot,
    ParticipationSnapshot,
)
from iios.investment.market.breadth.breadth_classifier import BreadthClassifier
from iios.investment.market.breadth.breadth_transition import BreadthTransitionDetector


def _bd(pct: float, stability: float = 0.70) -> BreadthData:
    return BreadthData(
        advancing=int(100 * pct), declining=int(100 * (1 - pct)),
        unchanged=0, total=100, breadth_pct=pct,
        ad_ratio=pct / max(1 - pct, 0.01),
        ad_line=0.0, ad_momentum=0.0,
        breadth_trend=BreadthTrend.RISING if pct > 0.5 else BreadthTrend.FALLING,
        breadth_stability=stability, metric_values={},
    )


def _ps(part_breadth: float, above_ma20: float = 0.60) -> ParticipationSnapshot:
    return ParticipationSnapshot(
        large_cap_pct=0.65, mid_cap_pct=0.60, small_cap_pct=0.55,
        sector_participation={},
        above_ma20_pct=above_ma20, above_ma50_pct=above_ma20 * 0.90,
        new_highs=10, new_lows=5, nh_nl_ratio=2.0,
        market_participation_score=65.0,
        participation_breadth=part_breadth,
    )


def _health() -> MarketHealthSnapshot:
    return MarketHealthSnapshot(
        health_score=65.0, internal_strength=0.65, leadership_breadth=0.60,
        lagging_breadth=0.40, participation_quality=0.65, internal_momentum=0.0,
        health_trend=HealthTrend.STABLE, leading_sectors=[], lagging_sectors=[],
    )


class TestBreadthClassifier:
    def test_broad_rally(self):
        c = BreadthClassifier()
        snap = c.classify(_bd(0.75), _ps(0.65), _health(), None, 1)
        assert snap.regime == BreadthRegimeType.BROAD_RALLY

    def test_broad_selloff(self):
        c = BreadthClassifier()
        snap = c.classify(_bd(0.20), _ps(0.30), _health(), None, 1)
        assert snap.regime == BreadthRegimeType.BROAD_SELLOFF

    def test_strong_participation(self):
        c = BreadthClassifier()
        snap = c.classify(_bd(0.67), _ps(0.70, above_ma20=0.70), _health(), None, 1)
        assert snap.regime == BreadthRegimeType.STRONG_PARTICIPATION

    def test_healthy_participation(self):
        c = BreadthClassifier()
        snap = c.classify(_bd(0.58), _ps(0.55, above_ma20=0.60), _health(), None, 1)
        assert snap.regime == BreadthRegimeType.HEALTHY_PARTICIPATION

    def test_neutral(self):
        c = BreadthClassifier()
        snap = c.classify(_bd(0.47), _ps(0.55), _health(), None, 1)
        assert snap.regime == BreadthRegimeType.NEUTRAL

    def test_weak_participation(self):
        c = BreadthClassifier()
        snap = c.classify(_bd(0.35), _ps(0.35), _health(), None, 1)
        assert snap.regime in (BreadthRegimeType.WEAK_PARTICIPATION,
                               BreadthRegimeType.NARROW_SELLOFF)

    def test_very_weak(self):
        c = BreadthClassifier()
        snap = c.classify(_bd(0.22), _ps(0.25), _health(), None, 1)
        # Low breadth + low sector participation → VERY_WEAK or BROAD_SELLOFF
        assert snap.regime in (
            BreadthRegimeType.VERY_WEAK_PARTICIPATION,
            BreadthRegimeType.BROAD_SELLOFF,
        )

    def test_confidence_range(self):
        c = BreadthClassifier()
        for pct in [0.20, 0.50, 0.80]:
            snap = c.classify(_bd(pct), _ps(0.50), _health(), None, 1)
            assert 0.0 <= snap.confidence <= 1.0

    def test_transition_prob_range(self):
        c = BreadthClassifier()
        snap = c.classify(_bd(0.70), _ps(0.65), _health(), None, 10)
        assert 0.0 <= snap.transition_probability <= 1.0

    def test_previous_regime_stored(self):
        c = BreadthClassifier()
        snap = c.classify(
            _bd(0.70), _ps(0.65), _health(),
            previous_regime=BreadthRegimeType.NEUTRAL, duration_bars=3
        )
        assert snap.previous_regime == BreadthRegimeType.NEUTRAL

    def test_regime_score_range(self):
        c = BreadthClassifier()
        for pct in [0.0, 0.25, 0.50, 0.75, 1.0]:
            snap = c.classify(_bd(pct), _ps(pct), _health(), None, 1)
            assert 0.0 <= snap.regime_score <= 100.0


class TestBreadthTransitionDetector:
    def test_initial_unknown(self):
        td = BreadthTransitionDetector()
        assert td.current_regime == BreadthRegimeType.UNKNOWN

    def test_first_update_triggers_transition(self):
        from iios.investment.market.breadth.breadth_regime import build_regime_snapshot
        td = BreadthTransitionDetector()
        snap = build_regime_snapshot(
            BreadthRegimeType.BROAD_RALLY, 0.85, 1, None, 0.10, 80.0
        )
        events = td.update(snap, bar_index=0, universe_id="TEST")
        assert td.current_regime == BreadthRegimeType.BROAD_RALLY
        assert any(e.event_type == BreadthEventType.REGIME_CHANGE for e in events)

    def test_no_event_when_regime_unchanged(self):
        from iios.investment.market.breadth.breadth_regime import build_regime_snapshot
        td = BreadthTransitionDetector()
        snap = build_regime_snapshot(
            BreadthRegimeType.NEUTRAL, 0.70, 1, None, 0.10, 50.0
        )
        td.update(snap, bar_index=0, universe_id="TEST")
        events = td.update(snap, bar_index=1, universe_id="TEST")
        assert events == []

    def test_duration_increments(self):
        from iios.investment.market.breadth.breadth_regime import build_regime_snapshot
        td = BreadthTransitionDetector()
        snap = build_regime_snapshot(
            BreadthRegimeType.NEUTRAL, 0.70, 1, None, 0.10, 50.0
        )
        for i in range(5):
            td.update(snap, bar_index=i, universe_id="TEST")
        # First bar starts the regime, then 4 more = duration 5
        assert td.duration_bars >= 4

    def test_health_improvement_event_on_upward_transition(self):
        from iios.investment.market.breadth.breadth_regime import build_regime_snapshot
        td = BreadthTransitionDetector()
        low = build_regime_snapshot(BreadthRegimeType.WEAK_PARTICIPATION, 0.60, 1, None, 0.20, 30.0)
        td.update(low, 0, "TEST")
        high = build_regime_snapshot(BreadthRegimeType.BROAD_RALLY, 0.90, 1, BreadthRegimeType.WEAK_PARTICIPATION, 0.05, 90.0)
        events = td.update(high, 1, "TEST")
        ev_types = {e.event_type for e in events}
        assert BreadthEventType.HEALTH_IMPROVEMENT in ev_types

    def test_previous_regime_tracked(self):
        from iios.investment.market.breadth.breadth_regime import build_regime_snapshot
        td = BreadthTransitionDetector()
        snap1 = build_regime_snapshot(BreadthRegimeType.NEUTRAL, 0.70, 1, None, 0.10, 50.0)
        td.update(snap1, 0, "TEST")
        snap2 = build_regime_snapshot(BreadthRegimeType.BROAD_RALLY, 0.85, 1, None, 0.05, 80.0)
        td.update(snap2, 1, "TEST")
        assert td.previous_regime == BreadthRegimeType.NEUTRAL
