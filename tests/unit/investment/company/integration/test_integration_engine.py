"""tests/unit/investment/company/integration/test_integration_engine.py
Full integration tests for CompanyIntelligenceIntegrationEngine.
"""
from __future__ import annotations

import threading
import pytest
from unittest.mock import MagicMock

from iios.investment.company.integration import (
    CompanyIntelligenceIntegrationEngine,
    CompanyIntelligenceSnapshot,
    SCORED_ENGINES,
)
from iios.investment.company.integration.company_state import EngineStatus


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fin(quality=72.0):
    s = MagicMock(); s.quality_score = quality
    return s


def _earn(score=72.0, profitable=True):
    s = MagicMock()
    q = MagicMock(); q.overall_score = score
    s.quality = q; s.is_profitable = profitable
    prof = MagicMock(); prof.avg_roic = 0.15; prof.roic = 0.15
    s.profitability = prof
    return s


def _bq(score=70.0):
    s = MagicMock(); s.overall_score = score
    return s


def _val(score=65.0, undervalued=True):
    s = MagicMock()
    vs = MagicMock(); vs.overall_score = score
    s.valuation_score = vs
    s.is_undervalued = undervalued; s.is_overvalued = not undervalued
    return s


def _growth(score=68.0, growing=True):
    s = MagicMock()
    gs = MagicMock(); gs.overall_score = score; gs.label = "good"
    s.growth_score = gs; s.overall_growth_score = score; s.is_growing = growing
    return s


def _mgmt(score=70.0):
    s = MagicMock()
    ms = MagicMock(); ms.overall_score = score
    s.management_score = ms; s.overall_management_score = score
    gr = MagicMock(); gr.overall_risk_score = 20.0; s.governance_risk = gr
    return s


def _own(score=68.0, pledge=5.0):
    s = MagicMock(); s.overall_ownership_score = score; s.promoter_pledge_pct = pledge
    risk = MagicMock(); risk.alerts = []; s.ownership_risk = risk
    return s


def _opp(score=65.0):
    s = MagicMock(); s.overall_score = score
    cat = MagicMock(); cat.value = "compounder"; s.primary_category = cat
    lc = MagicMock(); lc.value = "monitoring"; s.lifecycle = lc
    thesis = MagicMock(); thesis.key_catalysts = ["market expansion"]
    s.thesis = thesis
    return s


# ── Engine lifecycle ──────────────────────────────────────────────────────────

class TestEngineLifecycle:
    def test_integrate_returns_snapshot(self):
        engine = CompanyIntelligenceIntegrationEngine()
        snap = engine.integrate("INFY", financial_snapshot=_fin(), earnings_snapshot=_earn(), business_quality=_bq())
        assert isinstance(snap, CompanyIntelligenceSnapshot)

    def test_get_snapshot_after_integrate(self):
        engine = CompanyIntelligenceIntegrationEngine()
        engine.integrate("INFY", financial_snapshot=_fin(), earnings_snapshot=_earn(), business_quality=_bq())
        snap = engine.get_snapshot("INFY")
        assert snap is not None
        assert snap.ticker == "INFY"

    def test_unknown_ticker_returns_none(self):
        engine = CompanyIntelligenceIntegrationEngine()
        assert engine.get_snapshot("UNKNOWN") is None

    def test_known_tickers(self):
        engine = CompanyIntelligenceIntegrationEngine()
        engine.integrate("A", financial_snapshot=_fin())
        engine.integrate("B", financial_snapshot=_fin())
        assert "A" in engine.known_tickers()
        assert "B" in engine.known_tickers()

    def test_population_size(self):
        engine = CompanyIntelligenceIntegrationEngine()
        engine.integrate("A", financial_snapshot=_fin())
        engine.integrate("B", financial_snapshot=_fin())
        assert engine.population_size() == 2

    def test_history_stored(self):
        engine = CompanyIntelligenceIntegrationEngine()
        for _ in range(3):
            engine.integrate("X", financial_snapshot=_fin(), earnings_snapshot=_earn())
        hist = engine.get_history("X", 5)
        assert len(hist) == 3

    def test_evaluation_count_increments(self):
        engine = CompanyIntelligenceIntegrationEngine()
        for _ in range(4):
            engine.integrate("X", financial_snapshot=_fin())
        snap = engine.get_snapshot("X")
        assert snap.evaluation_count == 4


# ── Update API ────────────────────────────────────────────────────────────────

class TestUpdateAPI:
    def test_update_single_engine(self):
        engine = CompanyIntelligenceIntegrationEngine()
        snap = engine.update("TCS", "financials", _fin())
        assert isinstance(snap, CompanyIntelligenceSnapshot)
        assert "financials" in snap.available_engines

    def test_update_unknown_engine_raises(self):
        engine = CompanyIntelligenceIntegrationEngine()
        with pytest.raises(ValueError):
            engine.update("X", "nonexistent_engine", MagicMock())

    def test_update_incremental(self):
        engine = CompanyIntelligenceIntegrationEngine()
        snap1 = engine.update("X", "financials", _fin())
        assert snap1.financial_score is not None
        assert snap1.earnings_score is None

        snap2 = engine.update("X", "earnings", _earn())
        assert snap2.financial_score is not None
        assert snap2.earnings_score is not None

    def test_metadata_stored(self):
        engine = CompanyIntelligenceIntegrationEngine()
        snap = engine.integrate(
            "X", financial_snapshot=_fin(),
            metadata={"company_name": "TestCo", "sector": "IT", "exchange": "NSE"},
        )
        assert snap.company_name == "TestCo"
        assert snap.sector == "IT"


# ── Snapshot field validation ─────────────────────────────────────────────────

class TestSnapshotFields:
    @pytest.fixture
    def snap(self):
        engine = CompanyIntelligenceIntegrationEngine()
        return engine.integrate(
            "INFY",
            financial_snapshot=_fin(),
            earnings_snapshot=_earn(),
            business_quality=_bq(),
            valuation_snapshot=_val(),
            growth_snapshot=_growth(),
            management_snapshot=_mgmt(),
            ownership_snapshot=_own(),
            opportunity_snapshot=_opp(),
            metadata={"company_name": "Infosys", "sector": "IT", "industry": "Software"},
        )

    def test_ticker(self, snap): assert snap.ticker == "INFY"
    def test_company_name(self, snap): assert snap.company_name == "Infosys"
    def test_sector(self, snap): assert snap.sector == "IT"
    def test_overall_score_range(self, snap): assert 0.0 <= snap.overall_score <= 100.0
    def test_confidence_range(self, snap): assert 0.0 <= snap.confidence <= 1.0
    def test_completeness_full(self, snap): assert snap.completeness == pytest.approx(1.0)
    def test_quality_score_range(self, snap): assert 0.0 <= snap.quality_score <= 100.0
    def test_validation_report(self, snap): assert snap.validation_report is not None
    def test_all_engine_scores(self, snap):
        assert snap.financial_score is not None
        assert snap.earnings_score is not None
        assert snap.business_quality_score is not None
    def test_all_labels(self, snap):
        assert snap.financial_label != "unavailable"
    def test_available_engines(self, snap):
        assert len(snap.available_engines) == 8
    def test_no_missing_engines(self, snap):
        assert len(snap.missing_engines) == 0
    def test_generated_at_aware(self, snap):
        assert snap.generated_at.tzinfo is not None
    def test_intelligence_grade_valid(self, snap):
        assert snap.intelligence_grade in ("A+", "A", "B+", "B", "C+", "C", "D", "F")
    def test_to_dict(self, snap):
        d = snap.to_dict()
        assert d["ticker"] == "INFY"
        assert "overall_score" in d


# ── Score and quality APIs ────────────────────────────────────────────────────

class TestQueryAPIs:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.engine = CompanyIntelligenceIntegrationEngine()
        self.engine.integrate(
            "TCS", financial_snapshot=_fin(), earnings_snapshot=_earn(),
            business_quality=_bq(), metadata={"sector": "IT"},
        )

    def test_get_confidence(self):
        c = self.engine.get_confidence("TCS")
        assert c is not None and 0.0 <= c <= 1.0

    def test_get_confidence_unknown(self):
        assert self.engine.get_confidence("UNKNOWN") is None

    def test_get_overall_score(self):
        s = self.engine.get_overall_score("TCS")
        assert s is not None and 0.0 <= s <= 100.0

    def test_get_summary(self):
        from iios.investment.company.integration.company_summary import CompanySummary
        summary = self.engine.get_summary("TCS")
        assert isinstance(summary, CompanySummary)

    def test_get_validation_report(self):
        from iios.investment.company.integration.validation_report import ValidationReport
        report = self.engine.get_validation_report("TCS")
        assert isinstance(report, ValidationReport)

    def test_get_conflicts(self):
        conflicts = self.engine.get_conflicts("TCS")
        assert isinstance(conflicts, list)

    def test_get_quality(self):
        from iios.investment.company.integration.company_quality import CompanyQualityScore
        q = self.engine.get_quality("TCS")
        assert isinstance(q, CompanyQualityScore)

    def test_get_history(self):
        hist = self.engine.get_history("TCS", 5)
        assert isinstance(hist, list)

    def test_score_distribution(self):
        dist = self.engine.score_distribution()
        assert dist["count"] == 1

    def test_compare(self):
        self.engine.integrate("B", financial_snapshot=_fin())
        cmp = self.engine.compare(["TCS", "B", "UNKNOWN"])
        assert cmp["TCS"] is not None
        assert cmp["UNKNOWN"] is None

    def test_top_tickers(self):
        self.engine.integrate("LOW", financial_snapshot=_fin(quality=20.0))
        top = self.engine.top_tickers(2)
        assert len(top) <= 2

    def test_search_by_min_score(self):
        results = self.engine.search(min_score=0.0)
        assert len(results) >= 1

    def test_search_no_match(self):
        results = self.engine.search(min_score=99.9)
        assert results == []


# ── Quality ordering ──────────────────────────────────────────────────────────

class TestQualityOrdering:
    def test_good_beats_weak(self):
        engine = CompanyIntelligenceIntegrationEngine()
        snap_good = engine.integrate(
            "G", financial_snapshot=_fin(80.0), earnings_snapshot=_earn(82.0),
            business_quality=_bq(80.0),
        )
        snap_weak = engine.integrate(
            "W", financial_snapshot=_fin(18.0), earnings_snapshot=_earn(20.0, False),
            business_quality=_bq(18.0),
        )
        assert snap_good.overall_score > snap_weak.overall_score


# ── Thread safety ─────────────────────────────────────────────────────────────

class TestThreadSafety:
    def test_concurrent_integrate(self):
        engine = CompanyIntelligenceIntegrationEngine()
        errors = []

        def run(ticker):
            try:
                engine.integrate(ticker, financial_snapshot=_fin(), earnings_snapshot=_earn())
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=run, args=(f"T{i}",)) for i in range(20)]
        for t in threads: t.start()
        for t in threads: t.join()

        assert errors == []
        assert engine.population_size() == 20

    def test_concurrent_update(self):
        engine = CompanyIntelligenceIntegrationEngine()
        errors = []

        def run(i):
            try:
                engine.update("SHARED", "financials", _fin())
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=run, args=(i,)) for i in range(10)]
        for t in threads: t.start()
        for t in threads: t.join()

        assert errors == []


# ── Health APIs ───────────────────────────────────────────────────────────────

class TestHealthAPIs:
    def test_health_report_after_integrate(self):
        engine = CompanyIntelligenceIntegrationEngine()
        engine.integrate("X", financial_snapshot=_fin())
        report = engine.health_report()
        assert report["total_tickers_tracked"] >= 1

    def test_engine_health_after_update(self):
        engine = CompanyIntelligenceIntegrationEngine()
        engine.update("X", "financials", _fin())
        health = engine.engine_health("financials")
        assert health is not None
        assert health.status == EngineStatus.HEALTHY


# ── Custom rule registration ──────────────────────────────────────────────────

class TestCustomRuleRegistration:
    def test_register_rule(self):
        engine = CompanyIntelligenceIntegrationEngine()

        triggered = []

        def my_rule(intel):
            triggered.append(True)
            return None

        engine.register_consistency_rule(my_rule)
        engine.integrate("X", financial_snapshot=_fin())
        assert len(triggered) > 0


# ── Missing data resilience ───────────────────────────────────────────────────

class TestMissingData:
    def test_single_engine_only(self):
        engine = CompanyIntelligenceIntegrationEngine()
        snap = engine.integrate("X", financial_snapshot=_fin())
        assert isinstance(snap, CompanyIntelligenceSnapshot)
        assert snap.earnings_score is None
        assert snap.financial_score is not None
        assert snap.completeness < 0.5

    def test_no_engines_raises_nothing(self):
        engine = CompanyIntelligenceIntegrationEngine()
        snap = engine.integrate("X")
        # No snapshots → all None scores, overall = neutral (50)
        assert isinstance(snap, CompanyIntelligenceSnapshot)
        assert snap.overall_score == pytest.approx(50.0)
