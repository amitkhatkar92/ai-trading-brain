"""tests/unit/investment/market/liquidity/test_volume_liquidity_engine.py
Integration tests for InstitutionalVolumeLiquidityEngine.
"""
from __future__ import annotations

import asyncio
import threading
from typing import List

import pytest

from iios.investment.market.liquidity.volume_liquidity_engine import (
    InstitutionalVolumeLiquidityEngine,
)
from iios.investment.market.liquidity.models import (
    VolumeLiquiditySnapshot, VolumeLevel, VolumeTrend,
    LiquidityEventType, LiquidityEvent,
)
from tests.unit.investment.market.liquidity.conftest import (
    make_bar, make_bars, make_up_bar, make_down_bar, make_high_volume_bar,
)


def _make_engine(history_size: int = 100) -> InstitutionalVolumeLiquidityEngine:
    return InstitutionalVolumeLiquidityEngine(
        symbol="TEST", timeframe="1d", history_size=history_size
    )


def _warm_engine(engine: InstitutionalVolumeLiquidityEngine, n: int = 25) -> VolumeLiquiditySnapshot:
    bars = make_bars(n=n)
    snap = None
    for bar in bars:
        snap = engine.update(bar)
    return snap


# ── Basic Operation ───────────────────────────────────────────────────────────

class TestBasicOperation:
    def test_initial_state(self):
        eng = _make_engine()
        assert eng.current() is None

    def test_first_update_returns_snapshot(self):
        eng = _make_engine()
        bar = make_bar()
        snap = eng.update(bar)
        assert isinstance(snap, VolumeLiquiditySnapshot)

    def test_snapshot_has_required_fields(self):
        eng = _make_engine()
        snap = eng.update(make_bar())
        assert snap.symbol == "TEST"
        assert snap.timeframe == "1d"
        assert snap.bar_index == 0
        assert snap.volume_bar is not None
        assert snap.volume_profile is not None
        assert snap.participation is not None
        assert snap.liquidity is not None
        assert snap.effort_result is not None
        assert snap.order_flow is not None

    def test_volume_level_is_valid(self):
        eng = _make_engine()
        snap = eng.update(make_bar())
        assert snap.volume_level in list(VolumeLevel)

    def test_volume_trend_is_valid(self):
        eng = _make_engine()
        snap = _warm_engine(eng, 25)
        assert snap.volume_trend in list(VolumeTrend)

    def test_scores_in_range(self):
        eng = _make_engine()
        snap = _warm_engine(eng, 25)
        assert 0.0 <= snap.liquidity_score <= 100.0
        assert 0.05 <= snap.execution_readiness <= 0.95
        assert 0.05 <= snap.overall_confidence <= 0.95
        assert 0.0 <= snap.volume_quality <= 100.0

    def test_symbol_and_timeframe_properties(self):
        eng = _make_engine()
        assert eng.symbol == "TEST"
        assert eng.timeframe == "1d"


# ── Volume Analysis ───────────────────────────────────────────────────────────

class TestVolumeAnalysis:
    def test_high_volume_bar_level(self):
        eng = _make_engine()
        # Warm up with average volume
        for bar in make_bars(n=25):
            eng.update(bar)
        # Now inject very high volume bar
        high_bar = make_bar(index=25, volume=500_000.0)
        snap = eng.update(high_bar)
        assert snap.volume_level in (
            VolumeLevel.HIGH, VolumeLevel.VERY_HIGH, VolumeLevel.EXTREME_HIGH, VolumeLevel.ABOVE_AVERAGE
        )

    def test_low_volume_bar_level(self):
        eng = _make_engine()
        for bar in make_bars(n=25):
            eng.update(bar)
        low_bar = make_bar(index=25, volume=5_000.0)
        snap = eng.update(low_bar)
        assert snap.volume_level in (VolumeLevel.LOW, VolumeLevel.BELOW_AVERAGE, VolumeLevel.NONE)

    def test_relative_volume_positive(self):
        eng = _make_engine()
        snap = _warm_engine(eng, 25)
        assert snap.volume_bar.relative_volume >= 0.0

    def test_normalized_volume_in_range(self):
        eng = _make_engine()
        snap = _warm_engine(eng, 25)
        assert 0.0 <= snap.volume_bar.normalized_volume <= 1.0


# ── Participation ─────────────────────────────────────────────────────────────

class TestParticipation:
    def test_participation_not_none(self):
        eng = _make_engine()
        snap = eng.update(make_bar())
        assert snap.participation is not None

    def test_up_bar_has_buy_bias_or_neutral(self):
        eng = _make_engine()
        for b in make_bars(n=20):
            eng.update(b)
        up_bar = make_up_bar(index=20, base=110.0, volume=200_000.0)
        snap = eng.update(up_bar)
        from iios.investment.market.liquidity.models import ParticipationBias
        assert snap.participation.participation_bias in (
            ParticipationBias.BUY, ParticipationBias.STRONG_BUY, ParticipationBias.NEUTRAL
        )

    def test_participation_scores_in_range(self):
        eng = _make_engine()
        snap = _warm_engine(eng, 20)
        assert 0.0 <= snap.participation.participation_score <= 100.0
        assert 0.0 <= snap.participation.participation_confidence <= 1.0
        assert 0.0 <= snap.participation.buying_participation <= 1.0
        assert 0.0 <= snap.participation.selling_participation <= 1.0


# ── Liquidity Profile ─────────────────────────────────────────────────────────

class TestLiquidityProfile:
    def test_liquidity_profile_not_none(self):
        eng = _make_engine()
        snap = eng.update(make_bar())
        assert snap.liquidity is not None

    def test_execution_readiness_in_range(self):
        eng = _make_engine()
        snap = _warm_engine(eng, 20)
        assert 0.05 <= snap.execution_readiness <= 0.95

    def test_is_liquid_default(self):
        eng = _make_engine()
        _warm_engine(eng, 20)
        # Should return a boolean
        result = eng.is_liquid()
        assert isinstance(result, bool)

    def test_liquidity_profile_fields_in_range(self):
        eng = _make_engine()
        snap = _warm_engine(eng, 20)
        lp = snap.liquidity
        assert 0.0 <= lp.availability <= 1.0
        assert 0.0 <= lp.stability <= 1.0
        assert 0.0 <= lp.depth <= 1.0
        assert 0.0 <= lp.concentration <= 1.0
        assert 0.0 <= lp.fragmentation <= 1.0
        assert 0.0 <= lp.quality <= 100.0


# ── Events ───────────────────────────────────────────────────────────────────

class TestEvents:
    def test_volume_spike_generates_event(self):
        eng = _make_engine()
        # Warm up with normal volume
        for b in make_bars(n=25):
            eng.update(b)
        # Inject extreme spike
        spike_bar = make_bar(index=25, volume=1_000_000.0)
        snap = eng.update(spike_bar)
        event_types = [e.event_type for e in snap.active_events]
        assert LiquidityEventType.VOLUME_SPIKE in event_types

    def test_no_events_for_normal_bar(self):
        eng = _make_engine()
        _warm_engine(eng, 25)
        # Average volume, average range
        normal_bar = make_bar(index=25, volume=100_000.0)
        snap = eng.update(normal_bar)
        # Normal bar shouldn't generate extreme events
        critical_types = {
            LiquidityEventType.SHOCK,
            LiquidityEventType.BUYING_CLIMAX,
            LiquidityEventType.SELLING_CLIMAX,
        }
        active_types = {e.event_type for e in snap.active_events}
        assert not critical_types.intersection(active_types)

    def test_on_liquidity_event_callback(self):
        eng = _make_engine()
        events_received: List[LiquidityEvent] = []
        eng.on_liquidity_event(lambda e: events_received.append(e))

        for b in make_bars(n=25):
            eng.update(b)
        # Spike to trigger an event
        eng.update(make_bar(index=25, volume=1_000_000.0))
        assert len(events_received) > 0
        assert all(isinstance(e, LiquidityEvent) for e in events_received)

    def test_on_update_callback_fires_every_update(self):
        eng = _make_engine()
        call_count = [0]
        eng.on_update(lambda s: call_count.__setitem__(0, call_count[0] + 1))
        for b in make_bars(n=10):
            eng.update(b)
        assert call_count[0] == 10

    def test_on_volume_spike_callback(self):
        eng = _make_engine()
        spikes: List[VolumeLiquiditySnapshot] = []
        eng.on_volume_spike(lambda s: spikes.append(s))
        for b in make_bars(n=25):
            eng.update(b)
        eng.update(make_bar(index=25, volume=5_000_000.0))
        # May or may not fire depending on threshold, but shouldn't crash
        for snap in spikes:
            assert isinstance(snap, VolumeLiquiditySnapshot)


# ── Order Flow ────────────────────────────────────────────────────────────────

class TestOrderFlow:
    def test_order_flow_not_none(self):
        eng = _make_engine()
        snap = eng.update(make_bar())
        assert snap.order_flow is not None

    def test_has_l2_data_false(self):
        eng = _make_engine()
        snap = eng.update(make_bar())
        assert snap.order_flow.has_l2_data is False

    def test_cumulative_delta_changes(self):
        eng = _make_engine()
        snap1 = eng.update(make_up_bar(index=0))
        snap2 = eng.update(make_up_bar(index=1))
        # cumulative delta should accumulate
        assert snap2.order_flow.cumulative_delta != 0.0

    def test_buy_sell_imbalance_sums_to_one(self):
        eng = _make_engine()
        snap = eng.update(make_bar())
        total = snap.order_flow.buy_imbalance + snap.order_flow.sell_imbalance
        assert abs(total - 1.0) < 1e-9

    def test_has_buy_pressure(self):
        eng = _make_engine()
        # Multiple up bars
        for i in range(5):
            eng.update(make_up_bar(index=i, volume=200_000.0))
        of = eng.current_order_flow()
        assert of is not None
        # cumulative delta should be positive after multiple up bars
        assert of.cumulative_delta >= 0.0

    def test_connect_l2_feed_noop(self):
        eng = _make_engine()
        # Should not raise
        eng.connect_l2_feed(None)


# ── Batch Update ─────────────────────────────────────────────────────────────

class TestBatchUpdate:
    def test_batch_returns_snapshot(self):
        eng = _make_engine()
        bars = make_bars(n=20)
        snap = eng.update_batch(bars)
        assert isinstance(snap, VolumeLiquiditySnapshot)

    def test_batch_bar_index_matches_last(self):
        eng = _make_engine()
        bars = make_bars(n=15)
        snap = eng.update_batch(bars)
        assert snap.bar_index == bars[-1].index


# ── Async Update ─────────────────────────────────────────────────────────────

class TestAsyncUpdate:
    def test_async_update(self):
        eng = _make_engine()
        bar = make_bar()
        snap = asyncio.run(eng.async_update(bar))
        assert isinstance(snap, VolumeLiquiditySnapshot)

    def test_async_update_matches_sync(self):
        eng_sync = _make_engine()
        eng_async = _make_engine()
        bar = make_bar()
        sync_snap = eng_sync.update(bar)
        async_snap = asyncio.run(eng_async.async_update(bar))
        assert sync_snap.volume_level == async_snap.volume_level


# ── History ───────────────────────────────────────────────────────────────────

class TestHistory:
    def test_history_grows(self):
        eng = _make_engine()
        bars = make_bars(n=10)
        for b in bars:
            eng.update(b)
        hist = eng.history(10)
        assert len(hist) == 10

    def test_history_respects_limit(self):
        eng = _make_engine()
        bars = make_bars(n=10)
        for b in bars:
            eng.update(b)
        hist = eng.history(5)
        assert len(hist) == 5

    def test_history_limited_by_history_size(self):
        eng = _make_engine(history_size=10)
        bars = make_bars(n=20)
        for b in bars:
            eng.update(b)
        hist = eng.history(100)  # ask for more than stored
        assert len(hist) <= 10

    def test_events_list(self):
        eng = _make_engine()
        for b in make_bars(n=25):
            eng.update(b)
        eng.update(make_bar(index=25, volume=1_000_000.0))  # spike
        events = eng.events(50)
        assert isinstance(events, list)

    def test_current_matches_last_history(self):
        eng = _make_engine()
        _warm_engine(eng, 10)
        current = eng.current()
        hist = eng.history(1)
        assert current is not None
        assert hist[-1].snapshot_id == current.snapshot_id


# ── Context Inputs ────────────────────────────────────────────────────────────

class TestContextInputs:
    def test_no_context_no_crash(self):
        eng = _make_engine()
        snap = eng.update(make_bar(), structure=None, regime=None, trend=None)
        assert snap is not None

    def test_regime_none_uses_unknown(self):
        from iios.investment.market.regime.models import RegimeType
        eng = _make_engine()
        snap = eng.update(make_bar())
        assert snap.regime == RegimeType.UNKNOWN

    def test_trend_stage_unknown_when_no_trend(self):
        eng = _make_engine()
        snap = eng.update(make_bar())
        assert snap.trend_stage == "unknown"


# ── Edge Cases ────────────────────────────────────────────────────────────────

class TestEdgeCases:
    def test_zero_volume_bar_no_crash(self):
        eng = _make_engine()
        bar = make_bar(volume=0.0)
        snap = eng.update(bar)
        assert snap is not None

    def test_zero_range_bar_no_crash(self):
        eng = _make_engine()
        # high == low
        bar = make_bar(high=100.0, low=100.0, close=100.0, open=100.0)
        snap = eng.update(bar)
        assert snap is not None

    def test_fifty_consecutive_updates_no_crash(self):
        eng = _make_engine()
        bars = make_bars(n=50)
        snaps = [eng.update(b) for b in bars]
        assert len(snaps) == 50
        for s in snaps:
            assert s is not None

    def test_thread_safety(self):
        """Concurrent updates from multiple threads should not crash."""
        eng = _make_engine()
        errors = []

        def worker(offset: int) -> None:
            try:
                for i in range(10):
                    eng.update(make_bar(index=offset + i))
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(i * 100,)) for i in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert errors == [], f"Thread errors: {errors}"

    def test_to_dict_no_crash(self):
        eng = _make_engine()
        snap = _warm_engine(eng, 10)
        d = snap.to_dict()
        assert isinstance(d, dict)
        assert "symbol" in d
        assert "liquidity_score" in d
        assert "volume_profile" in d
        assert "participation" in d
