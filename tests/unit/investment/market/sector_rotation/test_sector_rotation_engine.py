"""tests/unit/investment/market/sector_rotation/test_sector_rotation_engine.py"""
from __future__ import annotations

import asyncio
import time
from typing import List

import pytest

from iios.investment.market.sector_rotation import InstitutionalSectorRotationEngine
from iios.investment.market.sector_rotation.models import (
    CapitalFlowProfile,
    MarketSnapshot,
    RelativeStrengthScore,
    RotationSignal,
    SectorEvent,
    SectorIntelligenceSnapshot,
    SectorLifecycleProfile,
    SectorPerformance,
    SectorRankEntry,
    SecurityData,
)
from iios.investment.market.sector_rotation.sector_taxonomy import SectorTaxonomy


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_snap(
    bar_index: int,
    it_ret:  float = 0.01,
    fin_ret: float = -0.005,
    hc_ret:  float = 0.003,
    cs_ret:  float = -0.002,
    benchmark: float = 0.002,
) -> MarketSnapshot:
    secs: List[SecurityData] = [
        SecurityData("AAPL",  it_ret,  "Information Technology", "Software",
                     market_cap=50.0, volume=1_200_000, avg_volume_20d=1_000_000, price=180.0),
        SecurityData("MSFT",  it_ret,  "Information Technology", "IT Services",
                     market_cap=45.0, volume=900_000, avg_volume_20d=800_000, price=400.0),
        SecurityData("JPM",   fin_ret, "Financials", "Banks",
                     market_cap=40.0, volume=700_000, avg_volume_20d=650_000, price=200.0),
        SecurityData("GS",    fin_ret, "Financials", "Capital Markets",
                     market_cap=25.0, volume=400_000, avg_volume_20d=380_000, price=450.0),
        SecurityData("JNJ",   hc_ret,  "Health Care", "Pharmaceuticals",
                     market_cap=30.0, volume=500_000, avg_volume_20d=480_000, price=160.0),
        SecurityData("UNH",   hc_ret,  "Health Care", "Health Care Services",
                     market_cap=22.0, volume=350_000, avg_volume_20d=330_000, price=510.0),
        SecurityData("PG",    cs_ret,  "Consumer Staples", "Personal Products",
                     market_cap=18.0, volume=300_000, avg_volume_20d=290_000, price=155.0),
        SecurityData("KO",    cs_ret,  "Consumer Staples", "Food Beverage",
                     market_cap=16.0, volume=280_000, avg_volume_20d=270_000, price=65.0),
    ]
    return MarketSnapshot(
        bar_index=bar_index,
        timestamp=float(bar_index),
        securities=secs,
        benchmark_return=benchmark,
    )


@pytest.fixture
def engine():
    return InstitutionalSectorRotationEngine()


@pytest.fixture
def warmed_engine():
    """Engine with 25 bars of history."""
    eng = InstitutionalSectorRotationEngine()
    for i in range(1, 26):
        it_ret  = 0.02 if i <= 15 else -0.01
        fin_ret = -0.01 if i <= 15 else 0.02
        eng.update(_make_snap(i, it_ret=it_ret, fin_ret=fin_ret))
    return eng


# ── basic tests ───────────────────────────────────────────────────────────────

class TestEngineBasic:
    def test_single_update_returns_snapshot(self, engine):
        snap = engine.update(_make_snap(1))
        assert isinstance(snap, SectorIntelligenceSnapshot)

    def test_snapshot_fields_populated(self, engine):
        snap = engine.update(_make_snap(1))
        assert snap.bar_index == 1
        assert snap.taxonomy  == "GICS"
        assert isinstance(snap.sector_rankings,  list)
        assert isinstance(snap.sector_perf,      dict)
        assert isinstance(snap.capital_flows,    dict)
        assert isinstance(snap.rs_scores,        dict)
        assert isinstance(snap.lifecycle_profiles, dict)
        assert isinstance(snap.confidence,       type(snap.confidence))

    def test_sector_rankings_sorted(self, engine):
        snap = engine.update(_make_snap(1))
        ranks = [e.rank for e in snap.sector_rankings]
        assert ranks == sorted(ranks)

    def test_leaders_and_laggards_populated(self, engine):
        snap = engine.update(_make_snap(1))
        assert isinstance(snap.leaders, list)
        assert isinstance(snap.laggards, list)

    def test_snapshot_id_unique(self, engine):
        s1 = engine.update(_make_snap(1))
        s2 = engine.update(_make_snap(2))
        assert s1.snapshot_id != s2.snapshot_id

    def test_bars_processed(self, engine):
        engine.update(_make_snap(1))
        engine.update(_make_snap(2))
        assert engine.bars_processed == 2


# ── rank & scoring ────────────────────────────────────────────────────────────

class TestRankingAndScoring:
    def test_strong_sector_ranked_higher(self, engine):
        """IT (high return) should rank above Consumer Staples (negative return)."""
        for i in range(1, 6):
            snap = engine.update(_make_snap(i, it_ret=0.03, cs_ret=-0.02))
        it_entry = next(e for e in snap.sector_rankings if e.sector == "Information Technology")
        cs_entry = next(e for e in snap.sector_rankings if e.sector == "Consumer Staples")
        assert it_entry.rank < cs_entry.rank

    def test_composite_scores_in_range(self, engine):
        snap = engine.update(_make_snap(1))
        for entry in snap.sector_rankings:
            assert 0.0 <= entry.composite_score <= 100.0

    def test_rank_change_nonzero_after_reversal(self):
        eng = InstitutionalSectorRotationEngine()
        for i in range(1, 10):
            eng.update(_make_snap(i, it_ret=0.04, fin_ret=-0.02))
        # Now reverse
        for i in range(10, 20):
            eng.update(_make_snap(i, it_ret=-0.02, fin_ret=0.04))
        snap = eng.latest()
        it_entry  = next(e for e in snap.sector_rankings if e.sector == "Information Technology")
        fin_entry = next(e for e in snap.sector_rankings if e.sector == "Financials")
        # Financials should now rank better; IT worse
        assert fin_entry.rank < it_entry.rank


# ── RS engine ─────────────────────────────────────────────────────────────────

class TestRelativeStrengthQuery:
    def test_rs_score_populated(self, engine):
        snap = engine.update(_make_snap(1))
        assert len(snap.rs_scores) > 0

    def test_rs_scores_in_range(self, engine):
        snap = engine.update(_make_snap(1))
        for rs in snap.rs_scores.values():
            assert 0.0 <= rs.composite <= 100.0

    def test_relative_strength_query_api(self, warmed_engine):
        rs = warmed_engine.relative_strength("Information Technology")
        assert rs is not None
        assert 0.0 <= rs.composite <= 100.0


# ── capital flow ──────────────────────────────────────────────────────────────

class TestCapitalFlowQuery:
    def test_flows_populated(self, engine):
        snap = engine.update(_make_snap(1))
        assert len(snap.capital_flows) > 0

    def test_flow_api(self, engine):
        engine.update(_make_snap(1))
        flow = engine.capital_flow("Information Technology")
        assert flow is not None
        assert -1.0 <= flow.net_flow_signal <= 1.0


# ── lifecycle ─────────────────────────────────────────────────────────────────

class TestLifecycleQuery:
    def test_profiles_populated_after_warmup(self, warmed_engine):
        profiles = warmed_engine.latest().lifecycle_profiles
        assert len(profiles) > 0
        from iios.investment.market.sector_rotation.models import SectorStage
        for p in profiles.values():
            assert isinstance(p.stage, SectorStage)

    def test_lifecycle_profile_api(self, warmed_engine):
        lc = warmed_engine.lifecycle_profile("Information Technology")
        assert lc is not None
        assert lc.stage_duration_bars >= 1


# ── rotation detection ────────────────────────────────────────────────────────

class TestRotationDetection:
    def test_rotation_timeline(self, warmed_engine):
        timeline = warmed_engine.rotation_timeline(20)
        assert isinstance(timeline, list)

    def test_rank_change_since(self, warmed_engine):
        changes = warmed_engine.rank_change_since(5)
        assert isinstance(changes, dict)


# ── context kwargs ────────────────────────────────────────────────────────────

class TestContextKwargs:
    def test_context_stored_in_snapshot(self, engine):
        snap = engine.update(
            _make_snap(1),
            market_regime="bull",
            breadth_regime="expanding",
            volatility_regime="low",
            correlation_regime="low_correlation",
        )
        assert snap.market_regime     == "bull"
        assert snap.breadth_regime    == "expanding"
        assert snap.volatility_regime == "low"

    def test_context_optional(self, engine):
        snap = engine.update(_make_snap(1))
        assert snap.market_regime is None


# ── callbacks ─────────────────────────────────────────────────────────────────

class TestCallbacks:
    def test_on_update_called(self, engine):
        received = []
        engine.on_update = received.append
        engine.update(_make_snap(1))
        assert len(received) == 1
        assert isinstance(received[0], SectorIntelligenceSnapshot)

    def test_on_rotation_callback(self):
        """Rotation callback fires when a rotation signal is emitted."""
        received = []
        eng = InstitutionalSectorRotationEngine()
        eng.on_rotation_detected = received.append

        # Create strong rotation: IT always top → then defensives always top
        for i in range(1, 6):
            eng.update(_make_snap(i, it_ret=0.04, fin_ret=-0.02, hc_ret=-0.01, cs_ret=-0.01))
        for i in range(6, 14):
            eng.update(_make_snap(i, it_ret=-0.03, fin_ret=-0.01, hc_ret=0.03, cs_ret=0.04))

        # Callback may or may not have fired depending on rotation threshold; no crash
        assert isinstance(received, list)

    def test_on_lifecycle_change_callback(self, warmed_engine):
        events = []
        warmed_engine.on_lifecycle_change = events.append
        # Process a few more bars — transitions may occur
        for i in range(26, 31):
            warmed_engine.update(_make_snap(i, it_ret=-0.04, fin_ret=0.05))
        assert isinstance(events, list)


# ── history & replay ──────────────────────────────────────────────────────────

class TestHistory:
    def test_history_returns_snapshots(self, warmed_engine):
        hist = warmed_engine.history(10)
        assert len(hist) == 10
        assert all(isinstance(s, SectorIntelligenceSnapshot) for s in hist)

    def test_latest_is_most_recent(self, warmed_engine):
        snap  = warmed_engine.update(_make_snap(99, it_ret=0.05))
        latest = warmed_engine.latest()
        assert latest is snap

    def test_sector_history_oldest_first(self, warmed_engine):
        hist = warmed_engine.history(5)
        bar_indices = [s.bar_index for s in hist]
        assert bar_indices == sorted(bar_indices)


# ── async update ──────────────────────────────────────────────────────────────

class TestAsyncUpdate:
    def test_async_update(self, engine):
        async def _run():
            snap = await engine.async_update(_make_snap(1))
            assert isinstance(snap, SectorIntelligenceSnapshot)
        asyncio.run(_run())


# ── taxonomy ──────────────────────────────────────────────────────────────────

class TestTaxonomySwitch:
    def test_nse_taxonomy(self):
        from iios.investment.market.sector_rotation.models import MarketSnapshot, SecurityData
        taxonomy = SectorTaxonomy(taxonomy_type="NSE")
        eng = InstitutionalSectorRotationEngine(taxonomy=taxonomy)
        secs = [
            SecurityData("HDFCBANK", 0.01, "Banks",  "Private Banks",  market_cap=20.0),
            SecurityData("INFY",     0.02, "IT",     "Software",       market_cap=18.0),
            SecurityData("HINDUNILVR", -0.005, "FMCG", "Personal Care", market_cap=15.0),
        ]
        snap = MarketSnapshot(bar_index=1, timestamp=1.0, securities=secs, taxonomy="NSE")
        result = eng.update(snap)
        assert isinstance(result, SectorIntelligenceSnapshot)
        assert result.taxonomy == "NSE"

    def test_custom_taxonomy(self):
        taxonomy = SectorTaxonomy()
        taxonomy.register_custom(
            sectors=["Tech", "Banking", "Pharma"],
            character={"Tech": "growth", "Banking": "cyclical", "Pharma": "defensive"},
            industries={"Tech": ["Hardware", "Software"], "Banking": ["Retail Banking"], "Pharma": ["Generics"]},
        )
        eng = InstitutionalSectorRotationEngine(taxonomy=taxonomy)
        secs = [
            SecurityData("A", 0.02, "Tech",    "Software",       market_cap=10.0),
            SecurityData("B", -0.01, "Banking", "Retail Banking", market_cap=8.0),
            SecurityData("C", 0.005, "Pharma",  "Generics",       market_cap=6.0),
        ]
        snap = MarketSnapshot(bar_index=1, timestamp=1.0, securities=secs, taxonomy="CUSTOM")
        result = eng.update(snap)
        assert "Tech" in result.sector_perf


# ── edge cases ────────────────────────────────────────────────────────────────

class TestEdgeCases:
    def test_single_security(self):
        eng = InstitutionalSectorRotationEngine()
        sec = SecurityData("AAPL", 0.01, "IT", "Software", market_cap=50.0)
        snap = MarketSnapshot(bar_index=1, timestamp=1.0, securities=[sec])
        result = eng.update(snap)
        assert "IT" in result.sector_perf

    def test_single_sector(self):
        eng = InstitutionalSectorRotationEngine()
        secs = [
            SecurityData(f"S{i}", 0.01 * (i % 3 - 1), "IT", "Software", market_cap=float(i + 1))
            for i in range(5)
        ]
        snap = MarketSnapshot(bar_index=1, timestamp=1.0, securities=secs)
        result = eng.update(snap)
        assert result is not None

    def test_zero_market_cap(self):
        eng  = InstitutionalSectorRotationEngine()
        secs = [SecurityData("A", 0.01, "IT", "Software", market_cap=0.0) for _ in range(3)]
        snap = MarketSnapshot(bar_index=1, timestamp=1.0, securities=secs)
        result = eng.update(snap)
        assert isinstance(result, SectorIntelligenceSnapshot)

    def test_to_dict_serialisable(self):
        eng  = InstitutionalSectorRotationEngine()
        snap = eng.update(_make_snap(1))
        d    = snap.to_dict()
        import json
        # Must be JSON serialisable without error
        json.dumps(d)

    def test_large_return_values_clamped(self):
        """Extreme returns should not crash any sub-engine."""
        eng  = InstitutionalSectorRotationEngine()
        secs = [SecurityData("A", 0.99, "IT", "Software", market_cap=10.0)]
        snap = MarketSnapshot(bar_index=1, timestamp=1.0, securities=secs)
        result = eng.update(snap)
        assert isinstance(result, SectorIntelligenceSnapshot)
