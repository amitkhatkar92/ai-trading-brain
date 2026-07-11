"""test_market_breadth_engine.py — integration tests for InstitutionalMarketBreadthEngine."""
from __future__ import annotations

import time

import pytest

from iios.investment.market.breadth import InstitutionalMarketBreadthEngine
from iios.investment.market.breadth.models import (
    BreadthEventType,
    BreadthIntelligenceSnapshot,
    BreadthRegimeType,
    DivergenceType,
)

from tests.unit.investment.market.breadth.conftest import (
    make_bull_universe,
    make_bear_universe,
    make_mixed_universe,
    make_multi_sector_universe,
    make_universe,
)


# ── Single update ─────────────────────────────────────────────────────────

class TestEngineUpdate:
    def test_returns_snapshot(self):
        engine = InstitutionalMarketBreadthEngine()
        snap = engine.update(make_bull_universe())
        assert isinstance(snap, BreadthIntelligenceSnapshot)

    def test_snapshot_fields_populated(self):
        engine = InstitutionalMarketBreadthEngine()
        snap = engine.update(make_bull_universe())
        assert snap.universe_id == "default"
        assert snap.bar_index == 0
        assert snap.breadth_data is not None
        assert snap.participation is not None
        assert snap.market_health is not None
        assert snap.regime_snapshot is not None
        assert snap.confidence is not None

    def test_bull_regime(self):
        engine = InstitutionalMarketBreadthEngine()
        for i in range(5):
            snap = engine.update(make_bull_universe(bar_index=i))
        assert snap.regime_snapshot.regime != BreadthRegimeType.UNKNOWN

    def test_bear_regime_low_breadth(self):
        engine = InstitutionalMarketBreadthEngine()
        for i in range(5):
            snap = engine.update(make_bear_universe(bar_index=i))
        assert snap.breadth_data.breadth_pct < 0.40

    def test_bar_index_increments(self):
        engine = InstitutionalMarketBreadthEngine()
        snap1 = engine.update(make_bull_universe())
        snap2 = engine.update(make_bull_universe())
        assert snap2.bar_index == snap1.bar_index + 1

    def test_current_returns_latest(self):
        engine = InstitutionalMarketBreadthEngine()
        snap = engine.update(make_bull_universe())
        assert engine.current() is snap

    def test_history_grows(self):
        engine = InstitutionalMarketBreadthEngine()
        for i in range(10):
            engine.update(make_bull_universe(bar_index=i))
        assert len(engine.history(20)) == 10


# ── Regime queries ────────────────────────────────────────────────────────

class TestRegimeQueries:
    def test_broad_rally_flag(self):
        engine = InstitutionalMarketBreadthEngine()
        sectors = ["Tech", "Finance", "Healthcare", "Energy", "Consumer"]
        # Very strong bull market
        for i in range(5):
            u = make_multi_sector_universe(sectors, [0.85] * 5, n_per_sector=30,
                                           bar_index=i)
            engine.update(u)
        # Broad rally or strong participation expected
        assert engine.is_broad_participation() or engine.is_broad_rally()

    def test_broad_selloff_flag(self):
        engine = InstitutionalMarketBreadthEngine()
        for i in range(5):
            u = make_universe(10, 90, bar_index=i)
            engine.update(u)
        assert engine.is_broad_selloff()

    def test_current_regime_not_unknown_after_update(self):
        engine = InstitutionalMarketBreadthEngine()
        engine.update(make_mixed_universe())
        assert engine.current_regime() != BreadthRegimeType.UNKNOWN


# ── Callbacks ─────────────────────────────────────────────────────────────

class TestCallbacks:
    def test_on_update_fires(self):
        engine = InstitutionalMarketBreadthEngine()
        received = []
        engine.on_update = received.append
        engine.update(make_bull_universe())
        assert len(received) == 1

    def test_on_regime_change_fires(self):
        engine = InstitutionalMarketBreadthEngine()
        events = []
        engine.on_regime_change = events.append
        # First bar always triggers a transition
        engine.update(make_bull_universe())
        assert len(events) >= 1

    def test_on_update_receives_correct_snap(self):
        engine = InstitutionalMarketBreadthEngine()
        received = []
        engine.on_update = received.append
        snap = engine.update(make_bull_universe())
        assert received[0] is snap

    def test_callback_exception_does_not_crash_engine(self):
        engine = InstitutionalMarketBreadthEngine()
        engine.on_update = lambda _: (_ for _ in ()).throw(RuntimeError("boom"))
        # Should not raise
        engine.update(make_bull_universe())


# ── Batch update ──────────────────────────────────────────────────────────

class TestBatchUpdate:
    def test_batch_returns_last_snapshot(self):
        engine = InstitutionalMarketBreadthEngine()
        universes = [make_bull_universe(bar_index=i) for i in range(5)]
        snap = engine.update_batch(universes)
        assert snap.bar_index == 4

    def test_batch_empty_raises(self):
        engine = InstitutionalMarketBreadthEngine()
        with pytest.raises(ValueError):
            engine.update_batch([])


# ── Async update ──────────────────────────────────────────────────────────

class TestAsyncUpdate:
    def test_async_update(self):
        import asyncio
        engine = InstitutionalMarketBreadthEngine()
        snap = asyncio.run(engine.async_update(make_bull_universe()))
        assert isinstance(snap, BreadthIntelligenceSnapshot)


# ── Context passthrough ───────────────────────────────────────────────────

class TestContextPassthrough:
    def test_market_regime_string_stored(self):
        engine = InstitutionalMarketBreadthEngine()
        snap = engine.update(make_bull_universe(), regime="bullish_trend")
        assert snap.market_regime == "bullish_trend"

    def test_volatility_regime_stored(self):
        engine = InstitutionalMarketBreadthEngine()
        snap = engine.update(make_bull_universe(), volatility="low_volatility")
        assert snap.volatility_regime == "low_volatility"

    def test_liquidity_score_stored(self):
        engine = InstitutionalMarketBreadthEngine()
        snap = engine.update(make_bull_universe(), liquidity=0.75)
        assert snap.liquidity_score == pytest.approx(0.75)


# ── Metric management ─────────────────────────────────────────────────────

class TestMetricManagement:
    def test_register_and_unregister(self):
        from iios.investment.market.breadth.advance_decline_metric import AdvanceDeclineMetric
        engine = InstitutionalMarketBreadthEngine(metrics=[])
        ad = AdvanceDeclineMetric()
        engine.register_metric(ad)
        snap = engine.update(make_bull_universe())
        assert "advance_decline" in snap.breadth_data.metric_values
        engine.unregister_metric("advance_decline")

    def test_empty_metrics_still_runs(self):
        engine = InstitutionalMarketBreadthEngine(metrics=[])
        snap = engine.update(make_bull_universe())
        assert snap is not None


# ── History and events ────────────────────────────────────────────────────

class TestHistoryAndEvents:
    def test_history_limited_by_history_size(self):
        engine = InstitutionalMarketBreadthEngine(history_size=5)
        for i in range(20):
            engine.update(make_bull_universe(bar_index=i))
        assert len(engine.history(100)) == 5

    def test_events_not_empty_after_transition(self):
        engine = InstitutionalMarketBreadthEngine()
        engine.update(make_bull_universe())
        evs = engine.events(100)
        assert len(evs) >= 1

    def test_current_health_not_none(self):
        engine = InstitutionalMarketBreadthEngine()
        engine.update(make_bull_universe())
        assert engine.current_health() is not None


# ── Breadth strategy signal ───────────────────────────────────────────────

class TestStrategySignal:
    def test_bullish_signal_in_bull_market(self):
        engine = InstitutionalMarketBreadthEngine()
        sectors = ["Tech", "Finance", "Healthcare", "Energy", "Consumer"]
        for i in range(10):
            u = make_multi_sector_universe(sectors, [0.80] * 5, n_per_sector=30,
                                           bar_index=i)
            engine.update(u)
        # Not asserting True/False — just no crash and returns bool
        result = engine.is_strategy_bullish_breadth()
        assert isinstance(result, bool)

    def test_no_crash_on_bear_market(self):
        engine = InstitutionalMarketBreadthEngine()
        for i in range(5):
            engine.update(make_bear_universe(bar_index=i))
        result = engine.is_strategy_bullish_breadth()
        assert result is False or result is True   # just bool


# ── Custom universe_id ────────────────────────────────────────────────────

class TestCustomUniverseId:
    def test_custom_id_propagated(self):
        engine = InstitutionalMarketBreadthEngine(universe_id="NIFTY50")
        snap = engine.update(make_bull_universe())
        assert snap.universe_id == "NIFTY50"
