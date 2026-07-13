"""tests/unit/investment/company/business_quality/test_business_quality_engine.py
Integration tests for BusinessQualityEngine.
"""
import threading
import pytest

from iios.investment.company.business_quality.business_quality_engine import BusinessQualityEngine
from iios.investment.company.business_quality.economic_moat import MoatStrength
from iios.investment.company.business_quality.assessment_context import (
    AssessmentContext, BusinessQualityPlugin, PluginResult,
)
from tests.unit.investment.company.business_quality.conftest import make_ctx


@pytest.fixture
def engine():
    return BusinessQualityEngine()


@pytest.fixture
def populated_engine(ctx_high_quality, ctx_commodity):
    e = BusinessQualityEngine()
    e.ingest("HQ", financial_snapshot=ctx_high_quality.financial_snapshot,
             earnings_snapshot=ctx_high_quality.earnings_snapshot)
    e.ingest("CM", financial_snapshot=ctx_commodity.financial_snapshot,
             earnings_snapshot=ctx_commodity.earnings_snapshot)
    return e


class TestIngestBehavior:
    def test_ingest_returns_snapshot(self, engine, ctx_high_quality):
        snap = engine.ingest(
            "INFY",
            financial_snapshot=ctx_high_quality.financial_snapshot,
            earnings_snapshot=ctx_high_quality.earnings_snapshot,
        )
        assert snap.ticker == "INFY"
        assert snap.quality_score is not None

    def test_ingest_financial_only(self, engine, ctx_high_quality):
        snap = engine.ingest_financial("TCS", ctx_high_quality.financial_snapshot)
        assert snap.ticker == "TCS"
        assert snap.quality_score.overall_score >= 0.0

    def test_ingest_no_data_no_crash(self, engine):
        snap = engine.ingest("EMPTY")
        assert snap.ticker == "EMPTY"
        assert 0.0 <= snap.quality_score.overall_score <= 100.0

    def test_ingest_updates_snapshot(self, engine, ctx_high_quality, ctx_commodity):
        engine.ingest("X", financial_snapshot=ctx_high_quality.financial_snapshot)
        snap1 = engine.get_snapshot("X")
        engine.ingest("X", financial_snapshot=ctx_commodity.financial_snapshot)
        snap2 = engine.get_snapshot("X")
        assert snap2 is not None
        assert snap2.generated_at >= snap1.generated_at

    def test_callback_invoked(self, ctx_high_quality):
        called = []
        e = BusinessQualityEngine(on_snapshot_updated=called.append)
        e.ingest("T", financial_snapshot=ctx_high_quality.financial_snapshot)
        assert len(called) == 1
        assert called[0].ticker == "T"

    def test_callback_exception_does_not_propagate(self, ctx_high_quality):
        def bad_cb(snap):
            raise RuntimeError("test")
        e = BusinessQualityEngine(on_snapshot_updated=bad_cb)
        snap = e.ingest("T", financial_snapshot=ctx_high_quality.financial_snapshot)
        assert snap.ticker == "T"

    def test_history_grows_on_multiple_ingests(self, engine, ctx_high_quality):
        for _ in range(3):
            engine.ingest("H", financial_snapshot=ctx_high_quality.financial_snapshot)
        hist = engine.get_history("H")
        assert len(hist) == 3


class TestQueryAPIs:
    def test_get_snapshot_unknown_returns_none(self, engine):
        assert engine.get_snapshot("UNKNOWN") is None

    def test_get_moat_score(self, populated_engine):
        score = populated_engine.get_moat_score("HQ")
        assert score is not None
        assert 0.0 <= score <= 100.0

    def test_get_moat_strength(self, populated_engine):
        strength = populated_engine.get_moat_strength("HQ")
        assert isinstance(strength, MoatStrength)

    def test_get_operational_score(self, populated_engine):
        score = populated_engine.get_operational_score("HQ")
        assert score is not None
        assert 0.0 <= score <= 100.0

    def test_get_resilience_score(self, populated_engine):
        score = populated_engine.get_resilience_score("HQ")
        assert score is not None
        assert 0.0 <= score <= 100.0

    def test_get_quality_score(self, populated_engine):
        score = populated_engine.get_quality_score("HQ")
        assert score is not None
        assert 0.0 <= score <= 100.0

    def test_get_competitive_score(self, populated_engine):
        score = populated_engine.get_competitive_score("HQ")
        assert score is not None

    def test_get_confidence(self, populated_engine):
        c = populated_engine.get_confidence("HQ")
        assert c is not None
        assert 0.0 <= c <= 100.0

    def test_known_tickers(self, populated_engine):
        tickers = populated_engine.known_tickers()
        assert "HQ" in tickers
        assert "CM" in tickers

    def test_high_quality_scores_higher_than_commodity(self, populated_engine):
        hq = populated_engine.get_quality_score("HQ")
        cm = populated_engine.get_quality_score("CM")
        assert hq > cm

    def test_snapshot_properties(self, populated_engine):
        snap = populated_engine.get_snapshot("HQ")
        assert isinstance(snap.is_wide_moat, bool)
        assert isinstance(snap.is_resilient, bool)
        assert snap.moat_score >= 0.0
        assert snap.overall_score >= 0.0


class TestPluginSystem:
    def test_plugin_registered_and_invoked(self, ctx_high_quality):
        class TestPlugin(BusinessQualityPlugin):
            @property
            def name(self) -> str:
                return "test_plugin"
            def assess(self, ctx: AssessmentContext) -> PluginResult:
                return PluginResult(
                    plugin_name="test_plugin", score=80.0, confidence=0.9,
                    signals=["test_signal"],
                )

        e = BusinessQualityEngine()
        e.register_plugin(TestPlugin())
        snap = e.ingest("T", financial_snapshot=ctx_high_quality.financial_snapshot)
        assert "test_plugin" in snap.plugin_scores
        assert snap.plugin_scores["test_plugin"] == pytest.approx(80.0)

    def test_plugin_unregistered(self, ctx_high_quality):
        class TestPlugin(BusinessQualityPlugin):
            @property
            def name(self) -> str: return "p2"
            def assess(self, ctx): return PluginResult("p2", 80.0, 1.0)

        e = BusinessQualityEngine()
        e.register_plugin(TestPlugin())
        e.unregister_plugin("p2")
        snap = e.ingest("T", financial_snapshot=ctx_high_quality.financial_snapshot)
        assert "p2" not in snap.plugin_scores

    def test_faulty_plugin_does_not_crash_engine(self, ctx_high_quality):
        class BadPlugin(BusinessQualityPlugin):
            @property
            def name(self) -> str: return "bad"
            def assess(self, ctx): raise RuntimeError("plugin error")

        e = BusinessQualityEngine()
        e.register_plugin(BadPlugin())
        snap = e.ingest("T", financial_snapshot=ctx_high_quality.financial_snapshot)
        assert snap.ticker == "T"


class TestThreadSafety:
    def test_concurrent_ingestion(self, ctx_high_quality):
        e = BusinessQualityEngine()
        errors = []

        def ingest(ticker):
            try:
                e.ingest(ticker, financial_snapshot=ctx_high_quality.financial_snapshot)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=ingest, args=(f"T{i}",)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        assert len(e.known_tickers()) == 20


class TestSnapshotOutput:
    def test_to_dict_complete(self, populated_engine):
        d = populated_engine.get_snapshot("HQ").to_dict()
        for key in ["ticker", "business_model", "moat", "operational",
                    "resilience", "competitive", "quality_score", "confidence"]:
            assert key in d

    def test_quality_score_label_set(self, populated_engine):
        snap = populated_engine.get_snapshot("HQ")
        assert snap.quality_score.label in [
            "exceptional", "strong", "average", "weak", "poor"
        ]

    def test_confidence_label_set(self, populated_engine):
        snap = populated_engine.get_snapshot("HQ")
        assert snap.confidence.label in [
            "high", "medium", "low", "insufficient"
        ]

    def test_sector_stored(self, engine, ctx_high_quality):
        snap = engine.ingest(
            "TCS", financial_snapshot=ctx_high_quality.financial_snapshot,
            sector="Technology", industry="IT Services",
        )
        assert snap.sector == "Technology"
        assert snap.industry == "IT Services"

    def test_peer_comparison_with_peers(self, ctx_high_quality, ctx_commodity):
        engine = BusinessQualityEngine()
        engine.ingest("CM", financial_snapshot=ctx_commodity.financial_snapshot)
        snap = engine.ingest(
            "HQ",
            financial_snapshot=ctx_high_quality.financial_snapshot,
            earnings_snapshot=ctx_high_quality.earnings_snapshot,
            peer_tickers=["CM"],
        )
        assert snap.competitive.peer_comparison.peer_count == 1
