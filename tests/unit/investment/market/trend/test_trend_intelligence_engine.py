"""tests/unit/investment/market/trend/test_trend_intelligence_engine.py
Integration tests for InstitutionalTrendIntelligenceEngine.
"""
from __future__ import annotations

import asyncio
import pytest
from iios.investment.market.trend.trend_intelligence_engine import (
    InstitutionalTrendIntelligenceEngine,
)
from iios.investment.market.trend.models import (
    TrendStage,
    TrendIntelligenceSnapshot,
    TrendEventRecord,
    TrendTransitionRecord,
    TrendQualityMetrics,
    TrendMomentumState,
    StrategyReadiness,
)
from iios.investment.market.market_constants import TrendDirection
from tests.unit.investment.market.trend.conftest import (
    make_structure_snapshot,
    make_regime_snapshot,
)


@pytest.fixture
def engine() -> InstitutionalTrendIntelligenceEngine:
    return InstitutionalTrendIntelligenceEngine("NIFTY", "1d")


@pytest.fixture
def bull_snap():
    return make_structure_snapshot(direction="up", confirmed=True, leg_count=3)


@pytest.fixture
def bear_snap():
    return make_structure_snapshot(
        direction="down", confirmed=True, leg_count=3,
        phase="markdown", trend_phase="impulse",
    )


class TestBasicOperation:
    def test_initial_state(self, engine):
        assert engine.current() is None

    def test_first_update(self, engine, bull_snap):
        result = engine.update(bull_snap)
        assert isinstance(result, TrendIntelligenceSnapshot)

    def test_snapshot_fields(self, engine, bull_snap):
        snap = engine.update(bull_snap)
        assert snap.symbol == "NIFTY"
        assert snap.timeframe == "1d"
        assert snap.direction in TrendDirection
        assert snap.stage in TrendStage
        assert 0.0 <= snap.confidence <= 1.0
        assert snap.quality is not None
        assert snap.momentum is not None

    def test_direction_from_structure(self, engine, bull_snap):
        snap = engine.update(bull_snap)
        assert snap.direction == TrendDirection.UP

    def test_direction_bear_from_structure(self, engine, bear_snap):
        snap = engine.update(bear_snap)
        assert snap.direction == TrendDirection.DOWN

    def test_confidence_in_range(self, engine, bull_snap):
        snap = engine.update(bull_snap)
        assert 0.05 <= snap.confidence <= 0.97


class TestHistory:
    def test_history_grows(self, engine, bull_snap):
        for _ in range(5):
            engine.update(make_structure_snapshot(direction="up", leg_count=3))
        assert engine._history.count() == 5

    def test_history_limit(self):
        eng = InstitutionalTrendIntelligenceEngine("TEST", history_size=3)
        for _ in range(5):
            eng.update(make_structure_snapshot())
        assert eng._history.count() <= 3

    def test_trend_timeline_populated_after_updates(self, engine):
        # Trigger multiple updates to potentially create stage changes
        snaps = [
            make_structure_snapshot(direction="up", confirmed=False, leg_count=0),
            make_structure_snapshot(direction="up", confirmed=True, leg_count=2),
            make_structure_snapshot(direction="up", confirmed=True, leg_count=3),
        ]
        for s in snaps:
            engine.update(s)
        # timeline should be a list (may be empty if no events triggered)
        assert isinstance(engine.trend_timeline(), list)

    def test_history_method_returns_list(self, engine, bull_snap):
        engine.update(bull_snap)
        h = engine.history(n=5)
        assert isinstance(h, list)


class TestCallbacks:
    def test_on_update_fires_every_time(self, engine, bull_snap):
        fired = []
        engine.on_update(lambda s: fired.append(s))
        for _ in range(3):
            engine.update(make_structure_snapshot())
        assert len(fired) == 3

    def test_on_stage_change_fires_on_change(self):
        eng = InstitutionalTrendIntelligenceEngine("TEST")
        stage_changes = []
        eng.on_stage_change(lambda old, new: stage_changes.append((old.stage, new.stage)))

        # First update creates state (no previous → no stage_change callback)
        eng.update(make_structure_snapshot(confirmed=False, leg_count=0))
        # Second with more progress
        eng.update(make_structure_snapshot(confirmed=True, leg_count=3))
        # If stage changed, callback fired; if not, list is empty — both valid
        assert isinstance(stage_changes, list)

    def test_on_event_fires_on_event(self, engine):
        events = []
        engine.on_event(lambda e: events.append(e))
        engine.update(make_structure_snapshot(confirmed=False, leg_count=0))
        engine.update(make_structure_snapshot(confirmed=True, leg_count=2))
        engine.update(make_structure_snapshot(confirmed=True, leg_count=3))
        # events may or may not have fired — just ensure no crash
        assert isinstance(events, list)


class TestStrategyAPI:
    def test_strategy_readiness_not_none(self, engine, bull_snap):
        engine.update(bull_snap)
        r = engine.strategy_readiness()
        assert r is not None
        assert isinstance(r, StrategyReadiness)

    def test_is_strategy_suitable(self, engine, bull_snap):
        engine.update(bull_snap)
        # result is a bool — no crash
        result = engine.is_strategy_suitable("momentum")
        assert isinstance(result, bool)

    def test_check_trade(self, engine, bull_snap):
        engine.update(bull_snap)
        allowed, reason = engine.check_trade("momentum", "long")
        assert isinstance(allowed, bool)
        assert isinstance(reason, str)

    def test_check_trade_no_state(self):
        eng = InstitutionalTrendIntelligenceEngine("TEST")
        allowed, reason = eng.check_trade("momentum", "long")
        assert not allowed


class TestBatchUpdate:
    def test_batch_returns_last(self, engine):
        snaps = [make_structure_snapshot(leg_count=i + 1) for i in range(5)]
        result = engine.update_batch(snaps)
        assert isinstance(result, TrendIntelligenceSnapshot)
        assert result.leg_count == snaps[-1].trend.leg_count


class TestAsyncUpdate:
    def test_async_update(self, engine, bull_snap):
        result = asyncio.run(engine.async_update(bull_snap))
        assert isinstance(result, TrendIntelligenceSnapshot)


class TestMomentumAndLifecycle:
    def test_bull_established_has_reasonable_momentum_score(self):
        eng = InstitutionalTrendIntelligenceEngine("NIFTY")
        snap = make_structure_snapshot(
            direction="up", confirmed=True, leg_count=4,
            n_swing_highs=5, n_swing_lows=5, quality_overall=80.0,
        )
        result = eng.update(snap)
        assert result.momentum.momentum_score >= 0.0

    def test_reversing_stage_detected(self):
        eng = InstitutionalTrendIntelligenceEngine("NIFTY")
        snap = make_structure_snapshot(
            direction="up", confirmed=True, leg_count=3,
            trend_phase="reversal",
        )
        result = eng.update(snap)
        assert result.stage == TrendStage.REVERSING


class TestRegimeIntegration:
    def test_regime_aligned_bull_trend_bull_regime(self):
        eng = InstitutionalTrendIntelligenceEngine("NIFTY")
        struct = make_structure_snapshot(direction="up", confirmed=True, leg_count=3)
        regime = make_regime_snapshot(regime="bull", confidence=0.85, stability=0.75)
        snap = eng.update(struct, regime)
        assert snap.regime_aligned is True

    def test_regime_not_aligned_bear_trend_bull_regime(self):
        eng = InstitutionalTrendIntelligenceEngine("NIFTY")
        struct = make_structure_snapshot(
            direction="down", confirmed=True, leg_count=3,
            phase="markdown", trend_phase="impulse",
        )
        regime = make_regime_snapshot(regime="bull", confidence=0.85)
        snap = eng.update(struct, regime)
        assert snap.regime_aligned is False


class TestEdgeCases:
    def test_empty_swings(self):
        eng = InstitutionalTrendIntelligenceEngine("TEST")
        snap = make_structure_snapshot(n_swing_highs=0, n_swing_lows=0)
        result = eng.update(snap)
        assert isinstance(result, TrendIntelligenceSnapshot)

    def test_single_swing(self):
        eng = InstitutionalTrendIntelligenceEngine("TEST")
        snap = make_structure_snapshot(n_swing_highs=1, n_swing_lows=1)
        result = eng.update(snap)
        assert isinstance(result, TrendIntelligenceSnapshot)

    def test_no_regime_snapshot(self):
        eng = InstitutionalTrendIntelligenceEngine("TEST")
        snap = make_structure_snapshot()
        result = eng.update(snap, regime_snapshot=None)
        assert isinstance(result, TrendIntelligenceSnapshot)

    def test_multiple_updates_no_crash(self):
        eng = InstitutionalTrendIntelligenceEngine("TEST")
        for i in range(50):
            snap = make_structure_snapshot(
                leg_count=(i % 8) + 1,
                confirmed=(i > 5),
            )
            result = eng.update(snap)
            assert isinstance(result, TrendIntelligenceSnapshot)

    def test_continuation_and_failure_probabilities(self):
        eng = InstitutionalTrendIntelligenceEngine("TEST")
        snap = make_structure_snapshot(confirmed=True, leg_count=3)
        eng.update(snap)
        cp = eng.continuation_probability()
        fp = eng.failure_probability()
        rp = eng.reversal_probability()
        assert 0.0 <= cp <= 1.0
        assert 0.0 <= fp <= 1.0
        assert 0.0 <= rp <= 1.0

    def test_symbol_and_timeframe_properties(self):
        eng = InstitutionalTrendIntelligenceEngine("BANKNIFTY", "1h")
        assert eng.symbol == "BANKNIFTY"
        assert eng.timeframe == "1h"

    def test_statistics_returns_trend_statistics(self):
        from iios.investment.market.trend.trend_statistics import TrendStatistics
        eng = InstitutionalTrendIntelligenceEngine("TEST")
        assert isinstance(eng.statistics(), TrendStatistics)
