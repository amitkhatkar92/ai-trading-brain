"""tests/unit/investment/company/opportunity/test_opportunity_engine.py
Full integration tests for CompanyOpportunityEngine.
"""
from __future__ import annotations

import threading
import pytest
from unittest.mock import MagicMock

from iios.investment.company.opportunity import (
    CompanyOpportunityEngine, OpportunitySnapshot,
    OpportunityPlugin, OpportunityPluginRegistry,
    OpportunityCategory, OpportunityLifecycle, OpportunityPriority,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fin(fcf=120_000, revenue=1_000_000, debt=150_000, equity=500_000, ni=80_000):
    snap = MagicMock()
    snap.revenue = revenue; snap.total_equity = equity; snap.total_assets = 900_000
    cf = MagicMock(); cf.free_cash_flow = fcf; cf.operating_cash_flow = 180_000; cf.capex = -60_000
    snap.cashflow_metrics = cf
    im = MagicMock(); im.net_income = ni; snap.income_metrics = im
    bs = MagicMock(); bs.total_debt = debt; bs.cash_and_equivalents = 80_000
    snap.balance_sheet_metrics = bs
    snap.ratios = {"dividend_payout_ratio": 0.30, "dividend_yield": 0.025}
    return snap


def _ear(roic=0.18, overall=78.0, eps_cagr=0.15, profitable=True):
    snap = MagicMock(); snap.overall_score = overall; snap.is_profitable = profitable
    snap.history_depth = 8
    prof = MagicMock(); prof.avg_roic = roic; prof.avg_roe = 0.20
    prof.net_margin = 0.12; prof.avg_net_margin = 0.10; prof.fcf_margin = 0.12
    snap.profitability = prof
    qual = MagicMock(); qual.overall_score = overall; qual.consistency_score = 80.0
    snap.quality = qual
    trend = MagicMock(); trend.cagr_eps = eps_cagr; trend.cagr_revenue = 0.12
    snap.trend = trend
    risk_e = MagicMock(); risk_e.earnings_stability_score = 76.0; risk_e.is_cyclical = False
    snap.risk = risk_e
    return snap


def _bq(moat=72.0, overall=72.0):
    bq = MagicMock(); bq.overall_score = overall
    moat_o = MagicMock(); moat_o.moat_score = moat; moat_o.avg_roic = 0.18
    moat_o.detected_moat_types = ["switching_costs"]
    bq.moat = moat_o
    ops = MagicMock(); ops.operational_quality_score = 70.0; bq.operational = ops
    res = MagicMock(); res.resilience_score = 68.0; bq.resilience = res
    return bq


# ── Engine Lifecycle ──────────────────────────────────────────────────────────

class TestEngineLifecycle:
    def test_evaluate_returns_snapshot(self):
        engine = CompanyOpportunityEngine()
        snap = engine.evaluate("INFY", _fin(), _ear(), _bq())
        assert isinstance(snap, OpportunitySnapshot)

    def test_get_snapshot_after_evaluate(self):
        engine = CompanyOpportunityEngine()
        engine.evaluate("INFY", _fin(), _ear(), _bq())
        snap = engine.get_snapshot("INFY")
        assert snap is not None
        assert snap.ticker == "INFY"

    def test_unknown_ticker_returns_none(self):
        engine = CompanyOpportunityEngine()
        assert engine.get_snapshot("UNKNOWN") is None

    def test_known_tickers(self):
        engine = CompanyOpportunityEngine()
        engine.evaluate("INFY", _fin(), _ear(), _bq())
        engine.evaluate("TCS",  _fin(), _ear(), _bq())
        assert "INFY" in engine.known_tickers()
        assert "TCS"  in engine.known_tickers()

    def test_history_stored(self):
        engine = CompanyOpportunityEngine()
        for _ in range(3):
            engine.evaluate("X", _fin(), _ear(), _bq())
        hist = engine.get_history("X", 5)
        assert len(hist) == 3

    def test_population_size(self):
        engine = CompanyOpportunityEngine()
        engine.evaluate("A", _fin(), _ear(), _bq())
        engine.evaluate("B", _fin(), _ear(), _bq())
        assert engine.population_size() == 2


# ── Snapshot Fields ───────────────────────────────────────────────────────────

class TestSnapshotFields:
    @pytest.fixture
    def snapshot(self):
        engine = CompanyOpportunityEngine()
        return engine.evaluate(
            "INFY", _fin(), _ear(), _bq(),
            company_metadata={"company_name": "Infosys", "sector": "IT", "exchange": "NSE"},
        )

    def test_ticker(self, snapshot): assert snapshot.ticker == "INFY"

    def test_generated_at_aware(self, snapshot):
        assert snapshot.generated_at.tzinfo is not None

    def test_overall_score_range(self, snapshot):
        assert 0.0 <= snapshot.overall_score <= 100.0

    def test_strength_type(self, snapshot):
        from iios.investment.company.opportunity.opportunity_profile import OpportunityStrength
        assert isinstance(snapshot.strength, OpportunityStrength)

    def test_confidence_range(self, snapshot):
        assert 0.0 <= snapshot.confidence <= 1.0

    def test_data_completeness_range(self, snapshot):
        assert 0.0 <= snapshot.data_completeness <= 1.0

    def test_lifecycle_type(self, snapshot):
        assert isinstance(snapshot.lifecycle, OpportunityLifecycle)

    def test_category_type(self, snapshot):
        assert isinstance(snapshot.primary_category, OpportunityCategory)

    def test_data_sources_populated(self, snapshot):
        assert "financials" in snapshot.data_sources
        assert "earnings" in snapshot.data_sources

    def test_opportunity_id_not_empty(self, snapshot):
        assert snapshot.opportunity_id and len(snapshot.opportunity_id) > 5

    def test_thesis_exists(self, snapshot):
        from iios.investment.company.opportunity.investment_thesis import InvestmentThesis
        assert isinstance(snapshot.thesis, InvestmentThesis)

    def test_alerts_list(self, snapshot):
        assert isinstance(snapshot.alerts, list)

    def test_to_dict_complete(self, snapshot):
        d = snapshot.to_dict()
        for key in ["ticker", "overall_score", "lifecycle", "primary_category",
                    "confidence", "thesis", "data_sources"]:
            assert key in d

    def test_is_active(self, snapshot):
        assert snapshot.is_active is True

    def test_headline(self, snapshot):
        assert isinstance(snapshot.headline, str) and "INFY" in snapshot.headline

    def test_opportunity_label(self, snapshot):
        assert isinstance(snapshot.opportunity_label, str)


# ── Score APIs ────────────────────────────────────────────────────────────────

class TestScoreAPIs:
    @pytest.fixture(autouse=True)
    def setup_engine(self):
        self.engine = CompanyOpportunityEngine()
        self.engine.evaluate(
            "TCS", _fin(), _ear(), _bq(),
            company_metadata={"sector": "IT", "industry": "Software"},
        )

    def test_opportunity_rank(self):
        rank = self.engine.get_opportunity_rank("TCS")
        assert rank == 1   # only ticker → rank 1

    def test_unknown_rank(self):
        assert self.engine.get_opportunity_rank("UNKNOWN") is None

    def test_investment_thesis(self):
        thesis = self.engine.get_investment_thesis("TCS")
        assert thesis is not None

    def test_get_alerts_list(self):
        alerts = self.engine.get_alerts("TCS")
        assert isinstance(alerts, list)

    def test_unknown_alerts(self):
        assert self.engine.get_alerts("UNKNOWN") == []

    def test_score_distribution(self):
        dist = self.engine.score_distribution()
        assert dist.get("count") == 1


# ── Search and Filter ─────────────────────────────────────────────────────────

class TestSearchAndFilter:
    def test_search_by_min_score(self):
        engine = CompanyOpportunityEngine()
        engine.evaluate("A", _fin(), _ear(), _bq())
        results = engine.search_opportunities(min_score=0.0)
        assert len(results) >= 1

    def test_search_no_match(self):
        engine = CompanyOpportunityEngine()
        engine.evaluate("A", _fin(), _ear(), _bq())
        results = engine.search_opportunities(min_score=99.9)
        assert len(results) == 0

    def test_compare_companies(self):
        engine = CompanyOpportunityEngine()
        engine.evaluate("A", _fin(), _ear(), _bq())
        engine.evaluate("B", _fin(), _ear(), _bq())
        cmp = engine.compare_companies(["A", "B", "UNKNOWN"])
        assert cmp["A"] is not None
        assert cmp["UNKNOWN"] is None

    def test_get_top_companies(self):
        engine = CompanyOpportunityEngine()
        for t in ["A", "B", "C"]:
            engine.evaluate(t, _fin(), _ear(), _bq())
        top = engine.get_top_companies(n=2)
        assert len(top) == 2


# ── Watchlist ─────────────────────────────────────────────────────────────────

class TestWatchlist:
    def test_add_to_watchlist(self):
        engine = CompanyOpportunityEngine()
        engine.evaluate("X", _fin(), _ear(), _bq())
        result = engine.add_to_watchlist("X", notes="Watching closely")
        assert result is True

    def test_get_watchlist(self):
        engine = CompanyOpportunityEngine()
        engine.evaluate("X", _fin(), _ear(), _bq())
        engine.add_to_watchlist("X")
        wl = engine.get_watchlist()
        assert len(wl) == 1
        assert wl[0].ticker == "X"

    def test_remove_from_watchlist(self):
        engine = CompanyOpportunityEngine()
        engine.evaluate("X", _fin(), _ear(), _bq())
        engine.add_to_watchlist("X")
        engine.remove_from_watchlist("X")
        assert engine.get_watchlist() == []

    def test_unknown_ticker_watchlist(self):
        engine = CompanyOpportunityEngine()
        assert engine.add_to_watchlist("UNKNOWN") is False


# ── Metadata ──────────────────────────────────────────────────────────────────

class TestMetadata:
    def test_sector_stored(self):
        engine = CompanyOpportunityEngine()
        snap = engine.evaluate(
            "X", _fin(), _ear(), _bq(),
            company_metadata={"sector": "Finance", "industry": "Banks"},
        )
        assert snap.sector == "Finance"
        assert snap.industry == "Banks"

    def test_sector_opportunities(self):
        engine = CompanyOpportunityEngine()
        engine.evaluate("X", _fin(), _ear(), _bq(),
                        company_metadata={"sector": "IT"})
        engine.evaluate("Y", _fin(), _ear(), _bq(),
                        company_metadata={"sector": "Finance"})
        it_opps = engine.get_sector_opportunities("IT")
        assert any(s.ticker == "X" for s in it_opps)


# ── Optional Snapshots ────────────────────────────────────────────────────────

class TestOptionalSnapshots:
    def test_no_optional_snapshots(self):
        engine = CompanyOpportunityEngine()
        snap = engine.evaluate("X", _fin(), _ear(), _bq())
        assert isinstance(snap, OpportunitySnapshot)
        assert snap.confidence < 0.80   # lower confidence without optionals

    def test_all_optional_snapshots(self):
        engine = CompanyOpportunityEngine()
        val = MagicMock()
        vs = MagicMock(); vs.overall_score = 65.0; val.valuation_score = vs
        val.is_undervalued = True; val.is_overvalued = False
        mos = MagicMock(); mos.margin_of_safety_pct = 20.0; val.mos = mos

        grw = MagicMock()
        grw.overall_growth_score = 72.0
        gs = MagicMock(); gs.overall_score = 72.0; grw.growth_score = gs

        mgmt = MagicMock()
        mgmt.overall_management_score = 70.0
        ms = MagicMock(); ms.overall_score = 70.0; mgmt.management_score = ms
        mgmt.flags = []

        own = MagicMock()
        own.overall_ownership_score = 68.0; own.promoter_pledge_pct = 5.0
        risk = MagicMock(); risk.alerts = []; own.ownership_risk = risk

        snap = engine.evaluate(
            "X", _fin(), _ear(), _bq(),
            valuation_snapshot=val, growth_snapshot=grw,
            management_snapshot=mgmt, ownership_snapshot=own,
        )
        assert snap.confidence > 0.50
        assert len(snap.data_sources) >= 7


# ── Quality Ordering ──────────────────────────────────────────────────────────

class TestQualityOrdering:
    def test_good_vs_weak(self):
        engine = CompanyOpportunityEngine()
        snap_good = engine.evaluate("G", _fin(fcf=200_000), _ear(roic=0.22), _bq(moat=80.0))
        snap_weak = engine.evaluate("W", _fin(fcf=-30_000), _ear(roic=0.03, overall=25.0), _bq(moat=20.0, overall=25.0))
        assert snap_good.overall_score > snap_weak.overall_score

    def test_good_ranked_higher(self):
        engine = CompanyOpportunityEngine()
        engine.evaluate("G", _fin(fcf=200_000), _ear(roic=0.22), _bq(moat=80.0, overall=82.0))
        engine.evaluate("W", _fin(fcf=-30_000), _ear(roic=0.03, overall=25.0), _bq(moat=20.0, overall=25.0))
        rank_g = engine.get_opportunity_rank("G")
        rank_w = engine.get_opportunity_rank("W")
        assert rank_g < rank_w  # lower number = better rank


# ── Thread Safety ─────────────────────────────────────────────────────────────

class TestThreadSafety:
    def test_concurrent_evaluate(self):
        engine = CompanyOpportunityEngine()
        errors = []

        def run(ticker):
            try:
                engine.evaluate(ticker, _fin(), _ear(), _bq())
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=run, args=(f"T{i}",)) for i in range(20)]
        for t in threads: t.start()
        for t in threads: t.join()

        assert errors == []
        assert engine.population_size() == 20


# ── Plugin System ─────────────────────────────────────────────────────────────

class TestPluginSystem:
    def test_register_plugin(self):
        class DummyPlugin(OpportunityPlugin):
            @property
            def name(self): return "dummy"
            def evaluate(self, inputs): return {"score_adjustment": 5.0}

        engine = CompanyOpportunityEngine()
        engine.register_plugin(DummyPlugin())
        snap = engine.evaluate("X", _fin(), _ear(), _bq())
        assert isinstance(snap, OpportunitySnapshot)

    def test_plugin_alert_propagates(self):
        class AlertPlugin(OpportunityPlugin):
            @property
            def name(self): return "alert_plugin"
            def evaluate(self, inputs):
                return {"alerts": ["PLUGIN_TEST_ALERT"]}

        engine = CompanyOpportunityEngine()
        engine.register_plugin(AlertPlugin())
        engine.evaluate("X", _fin(), _ear(), _bq())
        msgs = engine.get_alerts("X")
        assert "PLUGIN_TEST_ALERT" in msgs

    def test_duplicate_plugin_raises(self):
        class DupPlugin(OpportunityPlugin):
            @property
            def name(self): return "dup"
            def evaluate(self, inputs): return {}

        reg = OpportunityPluginRegistry()
        reg.register(DupPlugin())
        with pytest.raises(ValueError):
            reg.register(DupPlugin())

    def test_broken_plugin_does_not_crash(self):
        class BrokenPlugin(OpportunityPlugin):
            @property
            def name(self): return "broken"
            def evaluate(self, inputs): raise RuntimeError("crash!")

        engine = CompanyOpportunityEngine()
        engine.register_plugin(BrokenPlugin())
        snap = engine.evaluate("X", _fin(), _ear(), _bq())
        assert isinstance(snap, OpportunitySnapshot)
