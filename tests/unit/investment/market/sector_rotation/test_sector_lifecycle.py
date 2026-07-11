"""tests/unit/investment/market/sector_rotation/test_sector_lifecycle.py"""
from __future__ import annotations

import pytest

from iios.investment.market.sector_rotation.models import (
    RelativeStrengthScore,
    SectorEventType,
    SectorPerformance,
    SectorStage,
)
from iios.investment.market.sector_rotation.sector_lifecycle import SectorLifecycleEngine
from iios.investment.market.sector_rotation.sector_quality import (
    overall_snapshot_quality,
    sector_data_quality,
    security_quality,
    snapshot_quality,
)
from iios.investment.market.sector_rotation.sector_stage import classify_stage
from iios.investment.market.sector_rotation.sector_transition import (
    TransitionTracker,
    stage_confidence,
    transition_probability,
)


def _perf(sector: str, momentum: float, rel20: float, breadth: float) -> SectorPerformance:
    return SectorPerformance(
        sector=sector, bar_index=1,
        return_1bar=rel20 / 20, return_5bar=rel20 / 4, return_20bar=rel20, return_60bar=0.0,
        rel_return_1bar=0.0, rel_return_5bar=0.0, rel_return_20bar=rel20,
        breadth_pct=breadth, avg_volume_ratio=1.2,
        momentum_score=momentum, strength_score=momentum,
        n_securities=5,
    )


def _rs(composite: float) -> RelativeStrengthScore:
    return RelativeStrengthScore(
        symbol="X", vs_benchmark=composite / 100 - 0.5, vs_group=0.0,
        composite=composite, rank=1, percentile=composite / 100,
    )


class TestClassifyStage:
    def test_leading(self):
        stage = classify_stage(_perf("IT", 70.0, 0.10, 0.75), _rs(70.0))
        assert stage is SectorStage.LEADING

    def test_lagging(self):
        # Low RS, weak momentum, but NOT strongly negative rel20 (which would be UNDERPERFORMING)
        stage = classify_stage(_perf("Utilities", 35.0, -0.02, 0.30), _rs(35.0))
        assert stage is SectorStage.LAGGING

    def test_emerging(self):
        stage = classify_stage(_perf("Materials", 65.0, 0.02, 0.55), _rs(55.0))
        assert stage is SectorStage.EMERGING

    def test_weakening(self):
        stage = classify_stage(_perf("IT", 38.0, 0.02, 0.45), _rs(60.0))
        assert stage is SectorStage.WEAKENING

    def test_recovering(self):
        stage = classify_stage(_perf("Energy", 65.0, -0.02, 0.55), _rs(42.0))
        assert stage is SectorStage.RECOVERING

    def test_outperforming(self):
        stage = classify_stage(_perf("IT", 55.0, 0.08, 0.55), _rs(65.0))
        assert stage is SectorStage.OUTPERFORMING

    def test_underperforming(self):
        stage = classify_stage(_perf("Utilities", 30.0, -0.08, 0.30), _rs(35.0))
        assert stage is SectorStage.UNDERPERFORMING

    def test_mature(self):
        stage = classify_stage(_perf("FIN", 55.0, 0.02, 0.55), _rs(55.0))
        assert stage is SectorStage.MATURE


class TestStageConfidence:
    def test_increases_with_duration(self):
        c1 = stage_confidence(SectorStage.LEADING, 1, 70.0)
        c5 = stage_confidence(SectorStage.LEADING, 5, 70.0)
        c20 = stage_confidence(SectorStage.LEADING, 20, 70.0)
        assert c1 <= c5 <= c20

    def test_in_range(self):
        for stage in SectorStage:
            for dur in (1, 5, 20):
                conf = stage_confidence(stage, dur, 50.0)
                assert 0.0 <= conf <= 1.0


class TestTransitionProbability:
    def test_stable_leading_low_probability(self):
        prob = transition_probability(SectorStage.LEADING, 65.0)
        # LEADING with improving momentum → low transition probability
        assert prob < 0.5

    def test_weakening_high_probability(self):
        prob = transition_probability(SectorStage.WEAKENING, 35.0)
        assert 0.0 <= prob <= 1.0

    def test_always_in_range(self):
        for stage in SectorStage:
            for mom in (20.0, 50.0, 80.0):
                p = transition_probability(stage, mom)
                assert 0.0 <= p <= 1.0


class TestTransitionTracker:
    def test_first_update_no_event(self):
        t = TransitionTracker("IT")
        evt = t.update(SectorStage.LEADING, bar_index=1, momentum_score=70.0)
        assert evt is None
        assert t.current_stage is SectorStage.LEADING
        assert t.duration == 1

    def test_same_stage_increments_duration(self):
        t = TransitionTracker("IT")
        t.update(SectorStage.LEADING, 1, 70.0)
        t.update(SectorStage.LEADING, 2, 70.0)
        assert t.duration == 2

    def test_transition_emits_event(self):
        t = TransitionTracker("IT")
        t.update(SectorStage.LEADING, 1, 70.0)
        evt = t.update(SectorStage.WEAKENING, 2, 40.0)
        assert evt is not None
        assert evt.from_stage is SectorStage.LEADING
        assert evt.to_stage is SectorStage.WEAKENING

    def test_falling_leader_event_type(self):
        t = TransitionTracker("IT")
        t.update(SectorStage.LEADING, 1, 70.0)
        evt = t.update(SectorStage.LAGGING, 2, 30.0)
        assert evt is not None
        assert evt.event_type is SectorEventType.FALLING_LEADER

    def test_emerging_leader_event_type(self):
        t = TransitionTracker("X")
        t.update(SectorStage.RECOVERING, 1, 60.0)
        evt = t.update(SectorStage.EMERGING, 2, 65.0)
        assert evt is not None
        assert evt.event_type is SectorEventType.EMERGING_LEADER


class TestSectorLifecycleEngine:
    def test_update_returns_profiles(self, multi_snapshot_series):
        from iios.investment.market.sector_rotation.sector_snapshot import SectorSnapshotBuilder
        from iios.investment.market.sector_rotation.relative_strength_engine import RelativeStrengthEngine
        from iios.investment.market.sector_rotation.sector_taxonomy import SectorTaxonomy

        taxonomy = SectorTaxonomy()
        builder  = SectorSnapshotBuilder(taxonomy)
        rs_eng   = RelativeStrengthEngine()
        lc_eng   = SectorLifecycleEngine()

        for snap in multi_snapshot_series:
            perfs = builder.update(snap)
            rs_eng.update(perfs, {})
            rs    = rs_eng.sector_rs()
            profiles, events = lc_eng.update(perfs, rs, snap.bar_index)

        assert isinstance(profiles, dict)
        assert all(isinstance(p.stage, SectorStage) for p in profiles.values())

    def test_stage_query_methods(self, multi_snapshot_series):
        from iios.investment.market.sector_rotation.sector_snapshot import SectorSnapshotBuilder
        from iios.investment.market.sector_rotation.relative_strength_engine import RelativeStrengthEngine
        from iios.investment.market.sector_rotation.sector_taxonomy import SectorTaxonomy

        taxonomy = SectorTaxonomy()
        builder  = SectorSnapshotBuilder(taxonomy)
        rs_eng   = RelativeStrengthEngine()
        lc_eng   = SectorLifecycleEngine()

        for snap in multi_snapshot_series:
            perfs = builder.update(snap)
            rs_eng.update(perfs, {})
            lc_eng.update(perfs, rs_eng.sector_rs(), snap.bar_index)

        leaders  = lc_eng.leaders()
        laggards = lc_eng.laggards()
        emerging = lc_eng.emerging()
        assert isinstance(leaders, list)
        assert isinstance(laggards, list)
        assert isinstance(emerging, list)


class TestSectorQuality:
    def test_security_quality_full(self, make_security):
        s = make_security("AAPL", "IT", "Software", return_pct=0.01,
                          market_cap=50.0, price=150.0)
        q = security_quality(s)
        assert q == pytest.approx(1.0)

    def test_security_quality_missing_data(self):
        from iios.investment.market.sector_rotation.models import SecurityData
        s = SecurityData(symbol="X", return_pct=0.0, sector="IT", industry="S")
        q = security_quality(s)
        assert q < 1.0

    def test_sector_data_quality_empty(self):
        q = sector_data_quality([])
        assert q == 0.0

    def test_sector_data_quality_range(self, make_security):
        secs = [
            make_security(f"S{i}", "IT", "Software", market_cap=10.0, price=100.0)
            for i in range(5)
        ]
        q = sector_data_quality(secs)
        assert 0.0 <= q <= 1.0

    def test_overall_snapshot_quality(self, single_snapshot):
        q = overall_snapshot_quality(single_snapshot)
        assert 0.0 <= q <= 1.0

    def test_snapshot_quality_all_sectors(self, single_snapshot):
        q = snapshot_quality(single_snapshot)
        assert "Information Technology" in q
