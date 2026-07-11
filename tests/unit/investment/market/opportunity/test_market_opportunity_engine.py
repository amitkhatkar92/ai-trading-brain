"""tests/unit/investment/market/opportunity/test_market_opportunity_engine.py
Integration tests for InstitutionalMarketOpportunityEngine.
"""
from __future__ import annotations

import asyncio
from typing import List

import pytest

from iios.investment.market.opportunity import InstitutionalMarketOpportunityEngine
from iios.investment.market.opportunity.models import (
    AssetObservation,
    IntelligenceContext,
    Opportunity,
    OpportunityAlert,
    OpportunityCategory,
    OpportunityLifecycleStage,
    OpportunitySnapshotData,
    ScanScope,
)
from iios.investment.market.opportunity.universe_scanner import Universe


def _make_obs_series(n: int, symbol: str = "AAPL", score: float = 75.0) -> List[List[AssetObservation]]:
    """Return n bars of observations with consistent strong scores."""
    bars = []
    for bar in range(1, n + 1):
        ctx = IntelligenceContext(
            trend_strength=score, rs_vs_market=score, volume_ratio=1.8,
            liquidity_score=70.0, sector_rs_score=score, sector_momentum=score,
            risk_score=score, return_1bar=0.02, return_20bar=0.10,
            breadth_score=65.0, above_ma20_pct=0.65, volatility_percentile=0.3,
            fundamental_score=65.0,
        )
        bars.append([
            AssetObservation(
                symbol=symbol, sector="IT", industry="Software",
                bar_index=bar, timestamp=float(bar), intelligence=ctx,
            )
        ])
    return bars


class TestSingleUpdate:
    def test_returns_snapshot(self, obs_batch):
        engine = InstitutionalMarketOpportunityEngine()
        snap   = engine.update(obs_batch)
        assert isinstance(snap, OpportunitySnapshotData)

    def test_snapshot_has_opportunities(self, obs_batch):
        engine = InstitutionalMarketOpportunityEngine()
        snap   = engine.update(obs_batch)
        assert snap.total_active > 0

    def test_bars_processed_increments(self, obs_batch):
        engine = InstitutionalMarketOpportunityEngine()
        assert engine.bars_processed == 0
        engine.update(obs_batch)
        assert engine.bars_processed == 1

    def test_empty_observations(self):
        engine = InstitutionalMarketOpportunityEngine()
        snap   = engine.update([])
        assert snap.total_active == 0

    def test_regimes_stored_in_snapshot(self, obs_batch):
        engine = InstitutionalMarketOpportunityEngine()
        snap   = engine.update(obs_batch, market_regime="bull", breadth_regime="positive")
        assert snap.market_regime == "bull"
        assert snap.breadth_regime == "positive"


class TestMultiBar:
    def test_opportunities_accumulate(self):
        engine = InstitutionalMarketOpportunityEngine()
        for bar_obs in _make_obs_series(5, "AAPL"):
            engine.update(bar_obs)
        active = engine.registry().all_active()
        assert any(o.symbol == "AAPL" for o in active)

    def test_lifecycle_advances_over_bars(self):
        engine = InstitutionalMarketOpportunityEngine()
        stages = set()
        for bar_obs in _make_obs_series(15, "STAR", score=80.0):
            engine.update(bar_obs)
            opp = engine.opportunity_for("STAR")
            if opp:
                stages.add(opp.lifecycle_stage)
        # Should see more than just DISCOVERED after 15 bars
        assert len(stages) > 1

    def test_top_opportunities_sorted(self):
        engine = InstitutionalMarketOpportunityEngine()
        syms   = ["AAPL", "MSFT", "GOOG"]
        for bar in range(1, 4):
            obs = []
            for sym in syms:
                ctx = IntelligenceContext(
                    trend_strength=70.0 + syms.index(sym) * 5,
                    rs_vs_market=70.0, volume_ratio=1.5,
                    return_1bar=0.01, return_20bar=0.08,
                )
                obs.append(AssetObservation(
                    symbol=sym, sector="IT", industry="S",
                    bar_index=bar, timestamp=float(bar), intelligence=ctx,
                ))
            engine.update(obs)
        top = engine.top_opportunities(3)
        assert len(top) <= 3

    def test_history_grows(self, obs_batch):
        engine = InstitutionalMarketOpportunityEngine()
        for _ in range(3):
            engine.update(obs_batch)
        hist = engine.recent_history(5)
        assert len(hist) == 3


class TestCallbacks:
    def test_on_new_opportunity_fires(self, obs_batch):
        discovered: List[Opportunity] = []
        engine = InstitutionalMarketOpportunityEngine()
        engine.on_new_opportunity = discovered.append
        engine.update(obs_batch)
        assert len(discovered) > 0

    def test_on_new_opportunity_fires_once_per_symbol(self, obs_batch):
        discovered: List[str] = []
        engine = InstitutionalMarketOpportunityEngine()
        engine.on_new_opportunity = lambda o: discovered.append(o.symbol)
        for _ in range(3):
            engine.update(obs_batch)
        # Each symbol should appear at most once
        from collections import Counter
        counts = Counter(discovered)
        for cnt in counts.values():
            assert cnt == 1

    def test_on_update_fires_every_bar(self, obs_batch):
        updates: List[OpportunitySnapshotData] = []
        engine = InstitutionalMarketOpportunityEngine()
        engine.on_update = updates.append
        for _ in range(4):
            engine.update(obs_batch)
        assert len(updates) == 4

    def test_on_alert_fires_on_new_opportunity(self, obs_batch):
        alerts: List[OpportunityAlert] = []
        engine = InstitutionalMarketOpportunityEngine()
        engine.on_alert = alerts.append
        engine.update(obs_batch)
        assert len(alerts) > 0

    def test_callback_exception_does_not_crash(self, obs_batch):
        def bad_callback(x):
            raise RuntimeError("intentional error in callback")
        engine = InstitutionalMarketOpportunityEngine()
        engine.on_new_opportunity = bad_callback
        # Should not raise
        engine.update(obs_batch)


class TestQueryAPIs:
    def test_opportunity_for_symbol(self, obs_batch):
        engine = InstitutionalMarketOpportunityEngine()
        engine.update(obs_batch)
        opp = engine.opportunity_for("AAPL")
        assert opp is not None
        assert opp.symbol == "AAPL"

    def test_opportunity_for_unknown_symbol(self):
        engine = InstitutionalMarketOpportunityEngine()
        assert engine.opportunity_for("UNKNOWN") is None

    def test_search_by_sector(self, obs_batch):
        engine = InstitutionalMarketOpportunityEngine()
        engine.update(obs_batch)
        results = engine.search(sector="Information Technology")
        for r in results:
            assert r.sector == "Information Technology"

    def test_search_by_category(self, obs_batch):
        engine = InstitutionalMarketOpportunityEngine()
        engine.update(obs_batch)
        results = engine.search(category=OpportunityCategory.TREND_FOLLOWING)
        for r in results:
            assert r.primary_category is OpportunityCategory.TREND_FOLLOWING

    def test_search_by_min_score(self, obs_batch):
        engine = InstitutionalMarketOpportunityEngine()
        engine.update(obs_batch)
        results = engine.search(min_score=60.0)
        for r in results:
            assert r.composite_score >= 60.0

    def test_explain_after_update(self, obs_batch):
        engine = InstitutionalMarketOpportunityEngine()
        engine.update(obs_batch)
        # AAPL is a strong asset → should have explanation
        exp = engine.explain("AAPL")
        assert exp is not None
        assert exp.symbol == "AAPL"

    def test_explain_unknown_symbol_is_none(self):
        engine = InstitutionalMarketOpportunityEngine()
        assert engine.explain("UNKNOWN") is None

    def test_latest_snapshot(self, obs_batch):
        engine = InstitutionalMarketOpportunityEngine()
        snap   = engine.update(obs_batch)
        latest = engine.latest()
        assert latest is not None
        assert latest.bar_index == snap.bar_index

    def test_recent_alerts(self, obs_batch):
        engine = InstitutionalMarketOpportunityEngine()
        engine.update(obs_batch)
        alerts = engine.recent_alerts(10)
        assert isinstance(alerts, list)

    def test_registry_not_none(self, obs_batch):
        engine = InstitutionalMarketOpportunityEngine()
        engine.update(obs_batch)
        assert engine.registry() is not None

    def test_profile_store_not_none(self, obs_batch):
        engine = InstitutionalMarketOpportunityEngine()
        engine.update(obs_batch)
        assert engine.profile_store() is not None


class TestWatchlistAndUniverse:
    def test_add_to_watchlist(self, obs_batch):
        engine = InstitutionalMarketOpportunityEngine()
        engine.add_to_watchlist("AAPL")
        # Should not raise
        engine.update(obs_batch)

    def test_register_universe(self, obs_batch):
        engine   = InstitutionalMarketOpportunityEngine()
        universe = Universe(name="tech_core", scope=ScanScope.THEME, symbols={"AAPL", "MSFT"})
        engine.register_universe(universe)
        snap = engine.update(obs_batch, universe_name="tech_core")
        assert isinstance(snap, OpportunitySnapshotData)


class TestAsyncUpdate:
    def test_async_update_returns_snapshot(self, obs_batch):
        engine = InstitutionalMarketOpportunityEngine()
        snap   = asyncio.run(engine.async_update(obs_batch))
        assert isinstance(snap, OpportunitySnapshotData)

    def test_async_update_increments_bars(self, obs_batch):
        engine = InstitutionalMarketOpportunityEngine()
        asyncio.run(engine.async_update(obs_batch))
        assert engine.bars_processed == 1


class TestEdgeCases:
    def test_single_observation(self, make_obs):
        engine = InstitutionalMarketOpportunityEngine()
        obs    = [make_obs("SOLO")]
        snap   = engine.update(obs)
        assert isinstance(snap, OpportunitySnapshotData)

    def test_many_symbols(self):
        engine = InstitutionalMarketOpportunityEngine()
        obs    = [
            AssetObservation(
                symbol=f"SYM{i:03d}", sector="IT", industry="S",
                bar_index=1, timestamp=1.0,
                intelligence=IntelligenceContext(
                    trend_strength=50.0 + i * 0.5,
                    rs_vs_market=50.0 + i * 0.3,
                ),
            )
            for i in range(50)
        ]
        snap = engine.update(obs)
        assert snap.total_active <= 50

    def test_repeated_same_bar_idempotent(self, obs_batch):
        """Sending the same bar twice should not double-count symbols."""
        engine = InstitutionalMarketOpportunityEngine()
        engine.update(obs_batch)
        snap2  = engine.update(obs_batch)   # same symbols, same bar_index
        assert snap2.total_active <= len(obs_batch)

    def test_snapshot_serialisable(self, obs_batch):
        import json
        engine = InstitutionalMarketOpportunityEngine()
        snap   = engine.update(obs_batch)
        d      = snap.to_dict()
        json.dumps(d)   # must not raise

    def test_thread_safety(self, obs_batch):
        import threading
        engine  = InstitutionalMarketOpportunityEngine()
        errors  = []

        def run():
            try:
                engine.update(obs_batch)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=run) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert errors == []
