"""tests/unit/investment/market/opportunity/test_models.py"""
from __future__ import annotations

import pytest

from iios.investment.market.opportunity.models import (
    AlertType,
    AssetObservation,
    Evidence,
    IntelligenceContext,
    Opportunity,
    OpportunityAlert,
    OpportunityCategory,
    OpportunityEvent,
    OpportunityEventType,
    OpportunityLifecycleStage,
    OpportunityPriority,
    OpportunitySnapshotData,
    RankingScore,
    ScanScope,
)


class TestIntelligenceContext:
    def test_defaults(self):
        ctx = IntelligenceContext()
        assert ctx.market_regime is None
        assert ctx.rs_vs_market == 50.0
        assert ctx.volume_ratio == 1.0

    def test_custom_values(self):
        ctx = IntelligenceContext(market_regime="bull", trend_strength=80.0)
        assert ctx.market_regime == "bull"
        assert ctx.trend_strength == 80.0


class TestAssetObservation:
    def test_construction(self):
        obs = AssetObservation(
            symbol="AAPL", sector="IT", industry="Software",
            bar_index=1, timestamp=1.0,
        )
        assert obs.symbol == "AAPL"
        assert isinstance(obs.intelligence, IntelligenceContext)


class TestOpportunity:
    def test_new_factory(self):
        opp = Opportunity.new("AAPL", "IT", "Software", OpportunityCategory.TREND_FOLLOWING, 1)
        assert opp.symbol == "AAPL"
        assert opp.lifecycle_stage is OpportunityLifecycleStage.DISCOVERED
        assert len(opp.opportunity_id) == 36   # UUID

    def test_is_active(self):
        opp = Opportunity.new("X", "S", "I", OpportunityCategory.OBSERVATION_ONLY, 1)
        assert opp.is_active()
        opp.lifecycle_stage = OpportunityLifecycleStage.EXPIRED
        assert not opp.is_active()

    def test_to_dict_keys(self):
        opp = Opportunity.new("AAPL", "IT", "Software", OpportunityCategory.HIGH_RS, 1)
        d = opp.to_dict()
        assert "opportunity_id" in d
        assert "primary_category" in d
        assert d["primary_category"] == "high_relative_strength"


class TestOpportunityAlert:
    def test_make_factory(self):
        opp = Opportunity.new("AAPL", "IT", "S", OpportunityCategory.TREND_FOLLOWING, 1)
        alert = OpportunityAlert.make(
            AlertType.NEW_OPPORTUNITY, opp, 1, 0.7, "New opp",
        )
        assert alert.symbol == "AAPL"
        assert alert.alert_type is AlertType.NEW_OPPORTUNITY

    def test_to_dict(self):
        opp   = Opportunity.new("MSFT", "IT", "S", OpportunityCategory.MOMENTUM_CANDIDATE, 1)
        alert = OpportunityAlert.make(AlertType.PRIORITY_UPGRADE, opp, 1, 0.8, "Upgrade")
        d = alert.to_dict()
        assert d["alert_type"] == "priority_upgrade"


class TestRankingScore:
    def test_to_dict(self):
        rs = RankingScore(
            opportunity_id="abc", symbol="AAPL",
            composite_score=80.0, trend_score=75.0, momentum_score=70.0,
            flow_score=60.0, sector_score=65.0, risk_adj_score=72.0,
            quality_score=68.0, rank=1,
        )
        d = rs.to_dict()
        assert d["rank"] == 1
        assert 0 <= d["composite_score"] <= 100


class TestEvidence:
    def test_to_dict(self):
        e = Evidence(key="high_rs", value="75.0", weight=0.3, description="High RS")
        d = e.to_dict()
        assert d["key"] == "high_rs"
        assert d["weight"] == pytest.approx(0.3)


class TestOpportunitySnapshotData:
    def test_to_dict_serialisable(self):
        import json
        snap = OpportunitySnapshotData(
            snapshot_id="test", bar_index=1, timestamp=1.0,
            opportunities=[], new_discoveries=[], expired=[],
            alerts=[], events=[],
            total_active=0, high_priority_count=0,
            critical_count=0, new_count=0, expired_count=0,
            top_by_category={},
        )
        d = snap.to_dict()
        json.dumps(d)


class TestEnums:
    def test_opportunity_category_values(self):
        assert OpportunityCategory.TREND_FOLLOWING.value == "trend_following"
        assert OpportunityCategory.HIGH_RS.value == "high_relative_strength"

    def test_lifecycle_stages(self):
        stages = [s.value for s in OpportunityLifecycleStage]
        assert "discovered" in stages
        assert "confirmed" in stages
        assert "expired" in stages

    def test_scan_scope(self):
        assert ScanScope.FULL_MARKET.value == "full_market"
        assert ScanScope.WATCHLIST.value   == "watchlist"
