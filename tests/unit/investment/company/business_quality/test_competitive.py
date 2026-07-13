"""tests/unit/investment/company/business_quality/test_competitive.py"""
import pytest

from iios.investment.company.business_quality.market_position import MarketPositionAnalyzer
from iios.investment.company.business_quality.peer_comparison import PeerComparisonAnalyzer
from iios.investment.company.business_quality.competitive_analysis import CompetitiveAnalyzer
from iios.investment.company.business_quality.competitive_position import (
    MarketLeadershipLabel, CompetitivePressureLabel,
)
from tests.unit.investment.company.business_quality.conftest import make_ctx


class TestMarketPositionAnalyzer:
    def test_leader_for_high_quality(self, ctx_high_quality):
        p = MarketPositionAnalyzer().analyze(ctx_high_quality)
        assert p.leadership in [
            MarketLeadershipLabel.LEADER, MarketLeadershipLabel.CHALLENGER,
        ]

    def test_follower_for_commodity(self, ctx_commodity):
        p = MarketPositionAnalyzer().analyze(ctx_commodity)
        assert p.leadership in [
            MarketLeadershipLabel.FOLLOWER, MarketLeadershipLabel.UNKNOWN,
        ]

    def test_premium_margins_flag(self, ctx_high_quality):
        p = MarketPositionAnalyzer().analyze(ctx_high_quality)
        assert p.is_premium_margins is True

    def test_high_roic_flag(self, ctx_high_quality):
        p = MarketPositionAnalyzer().analyze(ctx_high_quality)
        assert p.is_high_roic is True

    def test_low_competitive_pressure_high_gm(self, ctx_high_quality):
        p = MarketPositionAnalyzer().analyze(ctx_high_quality)
        assert p.competitive_pressure == CompetitivePressureLabel.LOW

    def test_high_competitive_pressure_commodity(self, ctx_commodity):
        p = MarketPositionAnalyzer().analyze(ctx_commodity)
        assert p.competitive_pressure == CompetitivePressureLabel.HIGH

    def test_market_position_score_range(self, ctx_high_quality):
        p = MarketPositionAnalyzer().analyze(ctx_high_quality)
        assert 0.0 <= p.market_position_score <= 100.0

    def test_minimal_no_crash(self, ctx_minimal):
        p = MarketPositionAnalyzer().analyze(ctx_minimal)
        assert isinstance(p.leadership, MarketLeadershipLabel)

    def test_to_dict_keys(self, ctx_high_quality):
        d = MarketPositionAnalyzer().analyze(ctx_high_quality).to_dict()
        assert "leadership" in d
        assert "market_position_score" in d


class TestPeerComparisonAnalyzer:
    def test_no_peers_neutral_score(self, ctx_high_quality):
        from iios.investment.company.business_quality.business_quality_engine import BusinessQualityEngine
        own_snap = BusinessQualityEngine().ingest("TEST", **{
            "financial_snapshot": ctx_high_quality.financial_snapshot,
            "earnings_snapshot":  ctx_high_quality.earnings_snapshot,
        })
        p = PeerComparisonAnalyzer().analyze("TEST", own_snap, [])
        assert p.peer_count == 0
        assert p.competitive_score_vs_peers == pytest.approx(50.0)

    def test_peer_count_populated(self, ctx_high_quality, ctx_commodity):
        engine = __import__(
            "iios.investment.company.business_quality.business_quality_engine",
            fromlist=["BusinessQualityEngine"],
        ).BusinessQualityEngine()
        own  = engine.ingest("HQ", financial_snapshot=ctx_high_quality.financial_snapshot,
                             earnings_snapshot=ctx_high_quality.earnings_snapshot)
        peer = engine.ingest("CM", financial_snapshot=ctx_commodity.financial_snapshot,
                             earnings_snapshot=ctx_commodity.earnings_snapshot)
        result = PeerComparisonAnalyzer().analyze("HQ", own, [peer])
        assert result.peer_count == 1

    def test_top_quartile_flag_for_superior(self, ctx_high_quality, ctx_commodity):
        engine = __import__(
            "iios.investment.company.business_quality.business_quality_engine",
            fromlist=["BusinessQualityEngine"],
        ).BusinessQualityEngine()
        own  = engine.ingest("HQ", financial_snapshot=ctx_high_quality.financial_snapshot,
                             earnings_snapshot=ctx_high_quality.earnings_snapshot)
        peers = [
            engine.ingest(f"P{i}", financial_snapshot=ctx_commodity.financial_snapshot,
                          earnings_snapshot=ctx_commodity.earnings_snapshot)
            for i in range(5)
        ]
        result = PeerComparisonAnalyzer().analyze("HQ", own, peers)
        assert "top_quartile_vs_peers" in result.flags


class TestCompetitiveAnalyzer:
    def test_returns_profile(self, ctx_high_quality):
        p = CompetitiveAnalyzer().analyze(ctx_high_quality)
        assert p.market_position is not None
        assert p.peer_comparison is not None

    def test_score_range(self, ctx_high_quality):
        p = CompetitiveAnalyzer().analyze(ctx_high_quality)
        assert 0.0 <= p.competitive_intelligence_score <= 100.0

    def test_high_quality_vs_commodity(self, ctx_high_quality, ctx_commodity):
        a = CompetitiveAnalyzer()
        hq = a.analyze(ctx_high_quality).competitive_intelligence_score
        cm = a.analyze(ctx_commodity).competitive_intelligence_score
        assert hq > cm

    def test_no_peers_uses_market_position(self, ctx_high_quality):
        p = CompetitiveAnalyzer().analyze(ctx_high_quality)
        mp = p.market_position.market_position_score
        assert p.competitive_intelligence_score == pytest.approx(mp, abs=5)

    def test_to_dict_keys(self, ctx_high_quality):
        d = CompetitiveAnalyzer().analyze(ctx_high_quality).to_dict()
        assert "competitive_intelligence_score" in d
        assert "market_position" in d
