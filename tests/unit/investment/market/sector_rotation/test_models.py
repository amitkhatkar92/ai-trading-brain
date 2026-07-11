"""tests/unit/investment/market/sector_rotation/test_models.py"""
from __future__ import annotations

import pytest

from iios.investment.market.sector_rotation.models import (
    CapitalFlowProfile,
    FlowType,
    IndustryProfile,
    MarketSnapshot,
    RelativeStrengthScore,
    RotationSignal,
    RotationStrength,
    RotationType,
    SecurityData,
    SectorConfidenceScore,
    SectorEvent,
    SectorEventType,
    SectorIntelligenceSnapshot,
    SectorLifecycleProfile,
    SectorPerformance,
    SectorRankEntry,
    SectorStage,
    TaxonomyType,
)


class TestSecurityData:
    def test_volume_ratio_normal(self):
        s = SecurityData(
            symbol="AAPL", return_pct=0.01, sector="IT", industry="Software",
            volume=1_200_000, avg_volume_20d=1_000_000,
        )
        assert s.volume_ratio == pytest.approx(1.2)

    def test_volume_ratio_zero_avg(self):
        s = SecurityData(
            symbol="X", return_pct=0.0, sector="IT", industry="Software",
            volume=1_000, avg_volume_20d=0.0,
        )
        assert s.volume_ratio == pytest.approx(1.0)

    def test_is_advancing(self):
        s = SecurityData(symbol="X", return_pct=0.01, sector="IT", industry="Software")
        assert s.is_advancing is True
        assert s.is_declining is False

    def test_is_declining(self):
        s = SecurityData(symbol="X", return_pct=-0.01, sector="IT", industry="Software")
        assert s.is_declining is True
        assert s.is_advancing is False

    def test_flat(self):
        s = SecurityData(symbol="X", return_pct=0.0, sector="IT", industry="Software")
        assert s.is_advancing is False
        assert s.is_declining is False


class TestMarketSnapshot:
    def test_by_sector(self, single_snapshot):
        by_sec = single_snapshot.by_sector()
        assert "Information Technology" in by_sec
        assert "Financials" in by_sec
        assert "Health Care" in by_sec
        assert len(by_sec["Information Technology"]) == 3

    def test_by_industry(self, single_snapshot):
        by_ind = single_snapshot.by_industry()
        assert "Software" in by_ind
        assert len(by_ind["Software"]) == 2

    def test_sectors_sorted(self, single_snapshot):
        secs = single_snapshot.sectors()
        assert secs == sorted(secs)

    def test_total(self, single_snapshot):
        assert single_snapshot.total == 9


class TestSectorPerformance:
    def _make(self) -> SectorPerformance:
        return SectorPerformance(
            sector="IT", bar_index=1,
            return_1bar=0.01, return_5bar=0.05, return_20bar=0.20, return_60bar=0.60,
            rel_return_1bar=0.005, rel_return_5bar=0.025, rel_return_20bar=0.10,
            breadth_pct=0.8, avg_volume_ratio=1.5,
            momentum_score=65.0, strength_score=70.0,
            n_securities=5,
        )

    def test_to_dict_keys(self):
        p = self._make()
        d = p.to_dict()
        assert "sector" in d
        assert "momentum_score" in d
        assert d["sector"] == "IT"
        assert d["n_securities"] == 5

    def test_rounding(self):
        p = self._make()
        d = p.to_dict()
        assert isinstance(d["return_1bar"], float)


class TestRelativeStrengthScore:
    def test_to_dict(self):
        rs = RelativeStrengthScore(
            symbol="IT", vs_benchmark=0.05, vs_group=0.02,
            composite=70.0, rank=1, percentile=1.0,
        )
        d = rs.to_dict()
        assert d["rank"] == 1
        assert d["symbol"] == "IT"

    def test_percentile_range(self):
        rs = RelativeStrengthScore(
            symbol="X", vs_benchmark=-0.1, vs_group=-0.05,
            composite=30.0, rank=10, percentile=0.1,
        )
        assert 0.0 <= rs.percentile <= 1.0


class TestCapitalFlowProfile:
    def test_to_dict(self):
        f = CapitalFlowProfile(
            sector="Financials", bar_index=5,
            flow_type=FlowType.ACCUMULATION,
            flow_intensity=0.7, volume_ratio=1.5,
            accumulation_score=70.0, distribution_score=30.0,
            net_flow_signal=0.4,
        )
        d = f.to_dict()
        assert d["flow_type"] == "accumulation"


class TestRotationSignal:
    def test_to_dict(self):
        sig = RotationSignal(
            rotation_type=RotationType.INTO_DEFENSIVES,
            strength=RotationStrength.STRONG,
            from_sectors=["IT", "Financials"],
            to_sectors=["Utilities", "Consumer Staples"],
            confidence=0.8, bars_active=5, confirmed=True,
        )
        d = sig.to_dict()
        assert d["rotation_type"] == "into_defensives"
        assert d["confirmed"] is True


class TestSectorLifecycleProfile:
    def test_to_dict(self):
        p = SectorLifecycleProfile(
            sector="IT", stage=SectorStage.LEADING,
            stage_duration_bars=10,
            previous_stage=SectorStage.EMERGING,
            stage_confidence=0.85,
            transition_probability=0.2,
        )
        d = p.to_dict()
        assert d["stage"] == "leading"
        assert d["previous_stage"] == "emerging"


class TestSectorRankEntry:
    def test_to_dict(self):
        e = SectorRankEntry(
            rank=1, sector="IT", composite_score=80.0,
            relative_strength=70.0, momentum=75.0, flow_signal=0.4,
            lifecycle_stage=SectorStage.LEADING, rank_change=2,
        )
        d = e.to_dict()
        assert d["rank"] == 1
        assert d["rank_change"] == 2


class TestSectorEvent:
    def test_to_dict(self):
        e = SectorEvent(
            event_type=SectorEventType.EMERGING_LEADER,
            sector="IT", bar_index=10, severity=0.6,
            description="IT emerging",
            from_stage=SectorStage.RECOVERING,
            to_stage=SectorStage.EMERGING,
        )
        d = e.to_dict()
        assert d["event_type"] == "emerging_leader"
        assert d["from_stage"] == "recovering"


class TestTaxonomyType:
    def test_values(self):
        assert TaxonomyType.GICS.value == "GICS"
        assert TaxonomyType.NSE.value == "NSE"
        assert TaxonomyType.ICB.value == "ICB"
        assert TaxonomyType.CUSTOM.value == "CUSTOM"
