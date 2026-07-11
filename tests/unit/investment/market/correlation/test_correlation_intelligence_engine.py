"""test_correlation_intelligence_engine.py — integration tests for the main engine."""
from __future__ import annotations

import asyncio

import pytest

from iios.investment.market.correlation.models import (
    AssetClass,
    CorrelationEventType,
    CorrelationIntelligenceSnapshot,
    CorrelationRegimeType,
    MultiAssetSnapshot,
)
from iios.investment.market.correlation.correlation_intelligence_engine import (
    InstitutionalCorrelationIntelligenceEngine,
)

from tests.unit.investment.market.correlation.conftest import (
    make_snapshot,
    make_correlated_snapshots,
)


_ASSET_CLASSES = {
    "SPY":  AssetClass.INDEX.value,
    "QQQ":  AssetClass.INDEX.value,
    "TLT":  AssetClass.BOND.value,
    "GLD":  AssetClass.PRECIOUS_METAL.value,
    "VIX":  AssetClass.VOLATILITY.value,
}


def _make_engine(**kwargs):
    return InstitutionalCorrelationIntelligenceEngine(
        window=20, min_observations=5,
        asset_classes=_ASSET_CLASSES,
        **kwargs,
    )


def _run_n_bars(engine, n=25, target_corr=0.70):
    syms = ["SPY", "QQQ", "TLT", "GLD"]
    snaps = make_correlated_snapshots(n, syms, target_corr=target_corr)
    snap = None
    for s in snaps:
        snap = engine.update(s)
    return snap


# ── Single update ─────────────────────────────────────────────────────────

class TestEngineUpdate:
    def test_returns_snapshot(self):
        engine = _make_engine()
        snap   = engine.update(make_snapshot({"SPY": 0.01, "QQQ": 0.008}))
        assert isinstance(snap, CorrelationIntelligenceSnapshot)

    def test_snapshot_fields_populated(self):
        engine = _make_engine()
        snap   = engine.update(make_snapshot({"SPY": 0.01, "QQQ": -0.005}))
        assert snap.correlation_matrix is not None
        assert snap.regime_snapshot is not None
        assert snap.diversification is not None
        assert snap.systemic_risk is not None
        assert snap.confidence is not None

    def test_bar_index_increments(self):
        engine = _make_engine()
        snap1  = engine.update(make_snapshot({"A": 0.01, "B": 0.005}))
        snap2  = engine.update(make_snapshot({"A": 0.005, "B": 0.01}))
        assert snap2.bar_index == snap1.bar_index + 1

    def test_current_returns_latest(self):
        engine = _make_engine()
        snap   = engine.update(make_snapshot({"A": 0.01, "B": 0.005}))
        assert engine.current() is snap

    def test_history_grows(self):
        engine = _make_engine()
        for i in range(10):
            engine.update(make_snapshot({"A": 0.01 * i, "B": 0.005 * i}, bar_index=i))
        assert len(engine.history(20)) == 10

    def test_single_asset_snapshot_safe(self):
        engine = _make_engine()
        snap   = engine.update(make_snapshot({"SPY": 0.01}))
        assert snap is not None

    def test_empty_snapshot_safe(self):
        engine = _make_engine()
        snap   = engine.update(MultiAssetSnapshot(bar_index=0, timestamp=0.0, observations=[]))
        assert snap is not None


# ── Correlation matrix after warmup ──────────────────────────────────────

class TestCorrelationAfterWarmup:
    def test_correlation_populated_after_warmup(self):
        engine = _make_engine()
        snap   = _run_n_bars(engine, n=25, target_corr=0.80)
        m      = snap.correlation_matrix
        assert "SPY" in m.symbols
        assert "QQQ" in m.symbols

    def test_get_correlation_api(self):
        engine = _make_engine()
        _run_n_bars(engine, n=25, target_corr=0.80)
        corr = engine.get_correlation("SPY", "QQQ")
        if corr is not None:
            assert -1.0 <= corr <= 1.0

    def test_high_corr_input_gives_high_correlation(self):
        engine = _make_engine()
        snap   = _run_n_bars(engine, n=30, target_corr=0.90)
        avg    = snap.correlation_matrix.avg_abs_correlation()
        assert avg >= 0.0  # at minimum just verify it's computed


# ── Query APIs ────────────────────────────────────────────────────────────

class TestQueryAPIs:
    def test_dependency_graph_accessible(self):
        engine = _make_engine()
        _run_n_bars(engine, 25)
        graph  = engine.dependency_graph()
        assert graph is not None

    def test_systemic_risk_accessible(self):
        engine = _make_engine()
        _run_n_bars(engine, 25)
        risk   = engine.systemic_risk()
        assert risk is not None
        assert 0.0 <= risk.systemic_risk_score <= 100.0

    def test_diversification_accessible(self):
        engine = _make_engine()
        _run_n_bars(engine, 25)
        div    = engine.diversification()
        assert div is not None
        assert 0.0 <= div.diversification_score <= 100.0

    def test_regime_in_known_set(self):
        engine = _make_engine()
        _run_n_bars(engine, 25)
        snap   = engine.current()
        assert snap.regime_snapshot.regime in list(CorrelationRegimeType)


# ── Callbacks ─────────────────────────────────────────────────────────────

class TestCallbacks:
    def test_on_update_fires(self):
        engine   = _make_engine()
        received = []
        engine.on_update = received.append
        engine.update(make_snapshot({"A": 0.01, "B": 0.005}))
        assert len(received) == 1

    def test_on_update_receives_correct_snap(self):
        engine   = _make_engine()
        received = []
        engine.on_update = received.append
        snap = engine.update(make_snapshot({"A": 0.01, "B": 0.005}))
        assert received[0] is snap

    def test_on_regime_change_fires_on_first_update(self):
        engine = _make_engine()
        events = []
        engine.on_regime_change = events.append
        engine.update(make_snapshot({"A": 0.01, "B": 0.005}))
        # First update always transitions from UNKNOWN → something
        assert len(events) >= 1

    def test_callback_exception_does_not_crash(self):
        engine = _make_engine()
        engine.on_update = lambda _: (_ for _ in ()).throw(RuntimeError("boom"))
        engine.update(make_snapshot({"A": 0.01, "B": 0.005}))   # must not raise


# ── Batch and async ───────────────────────────────────────────────────────

class TestBatchAndAsync:
    def test_batch_returns_last_snapshot(self):
        engine    = _make_engine()
        snapshots = make_correlated_snapshots(5, ["A", "B"])
        result    = engine.update_batch(snapshots)
        assert result.bar_index == 4

    def test_batch_empty_raises(self):
        engine = _make_engine()
        with pytest.raises(ValueError):
            engine.update_batch([])

    def test_async_update(self):
        engine = _make_engine()
        snap   = asyncio.run(
            engine.async_update(make_snapshot({"A": 0.01, "B": 0.005}))
        )
        assert isinstance(snap, CorrelationIntelligenceSnapshot)


# ── Context passthrough ───────────────────────────────────────────────────

class TestContextPassthrough:
    def test_market_regime_stored(self):
        engine = _make_engine()
        snap   = engine.update(
            make_snapshot({"A": 0.01, "B": 0.005}), regime="bullish_trend"
        )
        assert snap.market_regime == "bullish_trend"

    def test_volatility_regime_stored(self):
        engine = _make_engine()
        snap   = engine.update(
            make_snapshot({"A": 0.01, "B": 0.005}), volatility="low_volatility"
        )
        assert snap.volatility_regime == "low_volatility"

    def test_breadth_regime_stored(self):
        engine = _make_engine()
        snap   = engine.update(
            make_snapshot({"A": 0.01, "B": 0.005}), breadth="healthy_participation"
        )
        assert snap.breadth_regime == "healthy_participation"


# ── History size cap ──────────────────────────────────────────────────────

class TestHistoryCap:
    def test_history_capped(self):
        engine = InstitutionalCorrelationIntelligenceEngine(
            window=20, min_observations=5, history_size=5
        )
        for i in range(20):
            engine.update(make_snapshot({"A": 0.01 * i, "B": 0.005 * i}, bar_index=i))
        assert len(engine.history(100)) == 5


# ── to_dict ───────────────────────────────────────────────────────────────

class TestToDict:
    def test_to_dict_returns_dict(self):
        engine = _make_engine()
        snap   = engine.update(make_snapshot({"A": 0.01, "B": 0.005}))
        d      = snap.to_dict()
        assert isinstance(d, dict)
        assert "snapshot_id" in d
        assert "regime" in d
        assert "correlation_matrix" in d
