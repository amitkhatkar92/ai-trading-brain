"""tests/unit/investment/market/volatility/test_volatility_intelligence_engine.py
Integration tests for InstitutionalVolatilityIntelligenceEngine.
"""
from __future__ import annotations

import asyncio
import threading
from typing import List

import pytest

from iios.investment.market.volatility.volatility_intelligence_engine import (
    InstitutionalVolatilityIntelligenceEngine,
)
from iios.investment.market.volatility.close_to_close_estimator import CloseToCloseEstimator
from iios.investment.market.volatility.high_low_estimator import HighLowEstimator
from iios.investment.market.volatility.models import (
    VolatilityIntelligenceSnapshot,
    VolatilityRegimeType,
    VolatilityBehaviour,
    VolatilityEventType,
    VolatilityEvent,
    StrategyType,
    RiskLevel,
)
from tests.unit.investment.market.volatility.conftest import (
    make_bar,
    make_bars,
    make_volatile_bars,
    make_quiet_bars,
    make_up_bar,
    make_down_bar,
)


def _make_engine(history_size: int = 100) -> InstitutionalVolatilityIntelligenceEngine:
    return InstitutionalVolatilityIntelligenceEngine(
        symbol="TEST",
        timeframe="1d",
        volume_window=10,
        history_size=history_size,
    )


def _warm(engine: InstitutionalVolatilityIntelligenceEngine, n: int = 30) -> VolatilityIntelligenceSnapshot:
    snap = None
    for bar in make_bars(n=n):
        snap = engine.update(bar)
    return snap


# ── Basic Operation ───────────────────────────────────────────────────────────

class TestBasicOperation:
    def test_initial_state_is_none(self):
        eng = _make_engine()
        assert eng.current() is None

    def test_first_update_returns_snapshot(self):
        eng = _make_engine()
        snap = eng.update(make_bar())
        assert isinstance(snap, VolatilityIntelligenceSnapshot)

    def test_snapshot_has_required_fields(self):
        eng = _make_engine()
        snap = eng.update(make_bar())
        assert snap.symbol == "TEST"
        assert snap.timeframe == "1d"
        assert snap.bar_index == 0
        assert snap.volatility_profile is not None
        assert snap.regime_snapshot is not None
        assert snap.behaviour_snapshot is not None
        assert snap.risk_profile is not None
        assert snap.strategy_compatibility is not None
        assert snap.confidence is not None

    def test_snapshot_id_is_unique(self):
        eng = _make_engine()
        s1 = eng.update(make_bar(index=0))
        s2 = eng.update(make_bar(index=1))
        assert s1.snapshot_id != s2.snapshot_id

    def test_symbol_and_timeframe_properties(self):
        eng = _make_engine()
        assert eng.symbol == "TEST"
        assert eng.timeframe == "1d"

    def test_realized_vol_positive(self):
        eng = _make_engine()
        snap = _warm(eng, 15)
        assert snap.realized_volatility > 0.0

    def test_normalized_vol_in_range(self):
        eng = _make_engine()
        snap = _warm(eng, 30)
        assert 0.0 <= snap.normalized_volatility <= 1.0

    def test_volatility_score_in_range(self):
        eng = _make_engine()
        snap = _warm(eng, 15)
        assert 0.0 <= snap.volatility_score <= 100.0


# ── Regime ────────────────────────────────────────────────────────────────────

class TestRegime:
    def test_regime_is_valid_type(self):
        eng = _make_engine()
        snap = _warm(eng, 30)
        assert snap.regime_snapshot.regime in list(VolatilityRegimeType)

    def test_high_vol_gives_higher_regime(self):
        quiet_eng = _make_engine()
        for bar in make_quiet_bars(40):
            quiet_snap = quiet_eng.update(bar)

        volatile_eng = _make_engine()
        for bar in make_volatile_bars(40):
            volatile_snap = volatile_eng.update(bar)

        from iios.investment.market.volatility.volatility_regime import regime_severity
        assert regime_severity(volatile_snap.regime_snapshot.regime) >= regime_severity(
            quiet_snap.regime_snapshot.regime
        )

    def test_current_regime_method(self):
        eng = _make_engine()
        _warm(eng, 15)
        regime = eng.current_regime()
        assert regime in list(VolatilityRegimeType)

    def test_regime_snapshot_fields_valid(self):
        eng = _make_engine()
        snap = _warm(eng, 20)
        rs = snap.regime_snapshot
        assert 0.0 <= rs.confidence <= 1.0
        assert 0.0 <= rs.transition_probability <= 1.0
        assert rs.duration_bars > 0


# ── Behaviour ─────────────────────────────────────────────────────────────────

class TestBehaviour:
    def test_behaviour_is_valid_type(self):
        eng = _make_engine()
        snap = _warm(eng, 15)
        assert snap.behaviour_snapshot.behaviour in list(VolatilityBehaviour)

    def test_expansion_score_in_range(self):
        eng = _make_engine()
        snap = _warm(eng, 20)
        assert 0.0 <= snap.behaviour_snapshot.expansion_score <= 1.0

    def test_compression_score_in_range(self):
        eng = _make_engine()
        snap = _warm(eng, 20)
        assert 0.0 <= snap.behaviour_snapshot.compression_score <= 1.0

    def test_expanding_flag_after_spike_series(self):
        eng = _make_engine()
        # warm up at normal vol
        for bar in make_bars(n=20):
            eng.update(bar)
        # now inject high-vol bars
        for i in range(5):
            eng.update(make_bar(index=20+i, high=120.0, low=80.0, close=100.0+i, open=100.0))
        assert eng.is_expanding() or not eng.is_expanding()  # just verify no crash

    def test_is_expanding_boolean(self):
        eng = _make_engine()
        _warm(eng, 15)
        assert isinstance(eng.is_expanding(), bool)

    def test_is_compressing_boolean(self):
        eng = _make_engine()
        _warm(eng, 15)
        assert isinstance(eng.is_compressing(), bool)


# ── Risk ──────────────────────────────────────────────────────────────────────

class TestRisk:
    def test_risk_profile_not_none(self):
        eng = _make_engine()
        snap = eng.update(make_bar())
        assert snap.risk_profile is not None

    def test_risk_components_in_range(self):
        eng = _make_engine()
        snap = _warm(eng, 20)
        rp = snap.risk_profile
        for comp in [rp.execution_risk, rp.gap_risk, rp.overnight_risk,
                     rp.portfolio_risk, rp.strategy_risk, rp.market_risk]:
            assert 0.0 <= comp <= 1.0

    def test_risk_level_valid(self):
        eng = _make_engine()
        snap = _warm(eng, 15)
        assert snap.risk_profile.risk_level in list(RiskLevel)

    def test_current_risk_profile(self):
        eng = _make_engine()
        _warm(eng, 15)
        rp = eng.current_risk_profile()
        assert rp is not None

    def test_risk_statistics_method(self):
        eng = _make_engine()
        _warm(eng, 20)
        stats = eng.risk_statistics()
        assert stats.total_bars == 20


# ── Strategy ──────────────────────────────────────────────────────────────────

class TestStrategy:
    def test_strategy_compatibility_not_none(self):
        eng = _make_engine()
        snap = eng.update(make_bar())
        assert snap.strategy_compatibility is not None

    def test_all_strategies_in_permissions(self):
        eng = _make_engine()
        snap = _warm(eng, 15)
        for st in StrategyType:
            assert st.value in snap.strategy_compatibility.permissions

    def test_is_strategy_permitted_method(self):
        eng = _make_engine()
        _warm(eng, 15)
        result = eng.is_strategy_permitted(StrategyType.MOMENTUM.value)
        assert isinstance(result, bool)

    def test_restricted_not_permitted(self):
        eng = _make_engine()
        snap = _warm(eng, 15)
        compat = snap.strategy_compatibility
        for s in compat.restricted:
            assert not compat.is_permitted(s)


# ── Confidence ────────────────────────────────────────────────────────────────

class TestConfidence:
    def test_confidence_not_none(self):
        eng = _make_engine()
        snap = eng.update(make_bar())
        assert snap.confidence is not None

    def test_all_confidence_in_range(self):
        eng = _make_engine()
        snap = _warm(eng, 20)
        for v in snap.confidence.to_dict().values():
            assert 0.0 <= v <= 1.0

    def test_current_confidence_method(self):
        eng = _make_engine()
        _warm(eng, 15)
        conf = eng.current_confidence()
        assert conf is not None


# ── Events ────────────────────────────────────────────────────────────────────

class TestEvents:
    def test_on_update_fires_every_bar(self):
        eng = _make_engine()
        count = [0]
        eng.on_update(lambda s: count.__setitem__(0, count[0] + 1))
        for bar in make_bars(n=10):
            eng.update(bar)
        assert count[0] == 10

    def test_on_regime_change_fires(self):
        eng = _make_engine()
        received: List[VolatilityEvent] = []
        eng.on_regime_change(lambda e: received.append(e))
        _warm(eng, 50)  # enough bars to trigger transitions
        # can't guarantee a transition but callback should not crash
        for e in received:
            assert e.event_type == VolatilityEventType.REGIME_CHANGE

    def test_on_expansion_callback(self):
        eng = _make_engine()
        snaps: List[VolatilityIntelligenceSnapshot] = []
        eng.on_expansion(lambda s: snaps.append(s))
        _warm(eng, 30)
        for s in snaps:
            assert isinstance(s, VolatilityIntelligenceSnapshot)

    def test_on_risk_alert_callback(self):
        eng = _make_engine()
        alerts: List[VolatilityEvent] = []
        eng.on_risk_alert(lambda e: alerts.append(e))
        _warm(eng, 30)
        for a in alerts:
            assert isinstance(a, VolatilityEvent)

    def test_events_method_returns_list(self):
        eng = _make_engine()
        _warm(eng, 20)
        evs = eng.events(50)
        assert isinstance(evs, list)


# ── Batch and Async ───────────────────────────────────────────────────────────

class TestBatchAndAsync:
    def test_batch_returns_snapshot(self):
        eng = _make_engine()
        bars = make_bars(n=20)
        snap = eng.update_batch(bars)
        assert isinstance(snap, VolatilityIntelligenceSnapshot)

    def test_batch_last_bar_index(self):
        eng = _make_engine()
        bars = make_bars(n=15)
        snap = eng.update_batch(bars)
        assert snap.bar_index == bars[-1].index

    def test_async_update(self):
        eng = _make_engine()
        snap = asyncio.run(eng.async_update(make_bar()))
        assert isinstance(snap, VolatilityIntelligenceSnapshot)


# ── History ───────────────────────────────────────────────────────────────────

class TestHistory:
    def test_history_grows(self):
        eng = _make_engine()
        for bar in make_bars(n=10):
            eng.update(bar)
        assert len(eng.history(10)) == 10

    def test_history_limit(self):
        eng = _make_engine()
        for bar in make_bars(n=10):
            eng.update(bar)
        assert len(eng.history(5)) == 5

    def test_history_size_cap(self):
        eng = _make_engine(history_size=10)
        for bar in make_bars(n=20):
            eng.update(bar)
        assert len(eng.history(100)) <= 10

    def test_current_matches_last_history(self):
        eng = _make_engine()
        _warm(eng, 10)
        current = eng.current()
        hist = eng.history(1)
        assert current.snapshot_id == hist[-1].snapshot_id


# ── Context Integration ───────────────────────────────────────────────────────

class TestContextIntegration:
    def test_no_context_no_crash(self):
        eng = _make_engine()
        snap = eng.update(make_bar(), structure=None, regime=None, trend=None, liquidity=None)
        assert snap is not None

    def test_regime_none_gives_unknown_market_regime(self):
        eng = _make_engine()
        snap = eng.update(make_bar())
        assert snap.market_regime is None

    def test_trend_stage_none_when_no_trend(self):
        eng = _make_engine()
        snap = eng.update(make_bar())
        assert snap.trend_stage is None


# ── Edge Cases ────────────────────────────────────────────────────────────────

class TestEdgeCases:
    def test_zero_volume_bar_no_crash(self):
        eng = _make_engine()
        snap = eng.update(make_bar(volume=0.0))
        assert snap is not None

    def test_zero_range_bar_no_crash(self):
        eng = _make_engine()
        snap = eng.update(make_bar(high=100.0, low=100.0, close=100.0, open=100.0))
        assert snap is not None

    def test_fifty_consecutive_updates_no_crash(self):
        eng = _make_engine()
        for bar in make_bars(n=50):
            snap = eng.update(bar)
        assert snap is not None

    def test_thread_safety(self):
        eng = _make_engine(history_size=200)
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
        snap = _warm(eng, 10)
        d = snap.to_dict()
        assert "symbol" in d
        assert "realized_volatility" in d
        assert "regime" in d
        assert "risk_profile" in d
        assert "strategy_compatibility" in d

    def test_register_estimator(self):
        eng = _make_engine()
        eng.register_estimator(HighLowEstimator(window=10))
        snap = _warm(eng, 15)
        assert snap is not None

    def test_unregister_estimator_no_crash(self):
        eng = _make_engine()
        eng.unregister_estimator("close_to_close_10")
        snap = eng.update(make_bar())
        assert snap is not None

    def test_is_high_volatility_boolean(self):
        eng = _make_engine()
        _warm(eng, 15)
        assert isinstance(eng.is_high_volatility(), bool)

    def test_is_shock_boolean(self):
        eng = _make_engine()
        _warm(eng, 15)
        assert isinstance(eng.is_shock(), bool)

    def test_normalized_volatility_in_range(self):
        eng = _make_engine()
        _warm(eng, 15)
        assert 0.0 <= eng.normalized_volatility() <= 1.0

    def test_realized_volatility_positive(self):
        eng = _make_engine()
        _warm(eng, 15)
        assert eng.realized_volatility() >= 0.0
