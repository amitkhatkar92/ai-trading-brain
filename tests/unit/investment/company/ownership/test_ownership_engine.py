"""tests/unit/investment/company/ownership/test_ownership_engine.py
Integration tests for OwnershipIntelligenceEngine.
"""
from __future__ import annotations

import threading
import pytest
from unittest.mock import MagicMock

from iios.investment.company.ownership import (
    OwnershipIntelligenceEngine, OwnershipSnapshot,
    OwnershipPlugin, OwnershipPluginRegistry,
    InsiderActivityLabel, OwnershipRiskLabel,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_financial(revenue=1_000_000, fcf=120_000, ocf=180_000,
                    ni=80_000, debt=150_000, equity=500_000, assets=900_000):
    snap = MagicMock()
    snap.revenue = revenue; snap.total_equity = equity; snap.total_assets = assets
    cf = MagicMock(); cf.free_cash_flow = fcf; cf.operating_cash_flow = ocf; cf.capex = -60_000
    snap.cashflow_metrics = cf
    im = MagicMock(); im.net_income = ni; snap.income_metrics = im
    bs = MagicMock(); bs.total_debt = debt; bs.cash_and_equivalents = 80_000
    snap.balance_sheet_metrics = bs
    snap.ratios = {"dividend_per_share": 10.0, "dividend_payout_ratio": 0.30}
    return snap


def _make_earnings(roic=0.18, stability=78.0):
    snap = MagicMock()
    snap.history_depth = 8
    trend = MagicMock(); trend.cagr_eps = 0.15; trend.cagr_revenue = 0.12; snap.trend = trend
    prof = MagicMock()
    prof.avg_roic = roic; prof.avg_roe = 0.20
    prof.net_margin = 0.12; prof.avg_net_margin = 0.10; prof.fcf_margin = 0.12
    snap.profitability = prof
    qual = MagicMock()
    qual.overall_score = 78.0; qual.consistency_score = 80.0
    qual.avg_ocf_to_ni = 1.10; qual.avg_accruals_ratio = 0.04
    snap.quality = qual
    risk = MagicMock(); risk.earnings_stability_score = stability; risk.is_cyclical = False
    snap.risk = risk
    return snap


def _make_bq():
    bq = MagicMock()
    moat = MagicMock(); moat.moat_score = 72.0; moat.avg_roic = 0.18
    moat.detected_moat_types = ["switching_costs"]
    bq.moat = moat
    ops = MagicMock(); ops.operational_quality_score = 70.0; bq.operational = ops
    res = MagicMock(); res.resilience_score = 68.0; bq.resilience = res
    return bq


_GOOD_OWNERSHIP = {
    "promoter_holding_pct": 0.52,
    "institutional_holding_pct": 0.28,
    "retail_holding_pct": 0.12,
    "free_float_pct": 0.45,
    "top10_holder_pct": 0.65,
    "promoter_pledge_pct": 0.05,
    "promoter_holding_change_3m": 0.5,
    "promoter_holding_change_1y": 1.2,
    "institutional_holding_change_3m": 0.8,
    "fii_holding_pct": 0.12,
    "dii_holding_pct": 0.10,
    "ownership_jurisdiction": "IN",
}

_RISKY_OWNERSHIP = {
    "promoter_holding_pct": 0.75,
    "institutional_holding_pct": 0.08,
    "free_float_pct": 0.22,
    "top10_holder_pct": 0.85,
    "promoter_pledge_pct": 0.60,
    "promoter_holding_change_3m": -3.0,
    "promoter_holding_change_1y": -7.0,
}

_GOOD_INSIDER = {
    "ceo_ownership_pct": 0.025,
    "insider_buy_count_6m": 5,
    "insider_sell_count_6m": 1,
}


# ── Engine lifecycle ──────────────────────────────────────────────────────────

class TestEngineLifecycle:
    def test_ingest_returns_snapshot(self):
        engine = OwnershipIntelligenceEngine()
        snap = engine.ingest("INFY", _make_financial(), _make_earnings(), _make_bq())
        assert isinstance(snap, OwnershipSnapshot)

    def test_get_snapshot_after_ingest(self):
        engine = OwnershipIntelligenceEngine()
        engine.ingest("INFY", _make_financial(), _make_earnings(), _make_bq())
        snap = engine.get_snapshot("INFY")
        assert snap is not None
        assert snap.ticker == "INFY"

    def test_unknown_ticker_returns_none(self):
        engine = OwnershipIntelligenceEngine()
        assert engine.get_snapshot("UNKNOWN") is None

    def test_known_tickers(self):
        engine = OwnershipIntelligenceEngine()
        engine.ingest("INFY", _make_financial(), _make_earnings(), _make_bq())
        engine.ingest("TCS",  _make_financial(), _make_earnings(), _make_bq())
        tickers = engine.known_tickers()
        assert "INFY" in tickers
        assert "TCS" in tickers

    def test_history_stored(self):
        engine = OwnershipIntelligenceEngine()
        for _ in range(3):
            engine.ingest("X", _make_financial(), _make_earnings(), _make_bq())
        hist = engine.get_ownership_history("X", 5)
        assert len(hist) == 3


# ── Snapshot fields ───────────────────────────────────────────────────────────

class TestSnapshotFields:
    @pytest.fixture
    def snapshot(self):
        engine = OwnershipIntelligenceEngine()
        return engine.ingest(
            "INFY", _make_financial(), _make_earnings(), _make_bq(),
            ownership_data=_GOOD_OWNERSHIP, insider_data=_GOOD_INSIDER,
        )

    def test_ticker(self, snapshot): assert snapshot.ticker == "INFY"

    def test_generated_at(self, snapshot):
        from datetime import timezone
        assert snapshot.generated_at.tzinfo is not None

    def test_overall_score_range(self, snapshot):
        assert 0.0 <= snapshot.overall_ownership_score <= 100.0

    def test_ownership_label(self, snapshot):
        assert snapshot.ownership_label in (
            "exceptional", "strong", "adequate", "weak", "poor", "insufficient",
        )

    def test_confidence_range(self, snapshot):
        assert 0.0 <= snapshot.confidence <= 1.0

    def test_is_promoter_backed(self, snapshot):
        assert snapshot.is_promoter_backed is True

    def test_has_institutional_support(self, snapshot):
        assert snapshot.has_institutional_support is True

    def test_data_sources_populated(self, snapshot):
        assert len(snapshot.data_sources) > 0

    def test_ownership_standard(self, snapshot):
        assert snapshot.ownership_standard == "generic"

    def test_promoter_pledge_pct(self, snapshot):
        assert snapshot.promoter_pledge_pct == pytest.approx(5.0)


# ── Score APIs ────────────────────────────────────────────────────────────────

class TestScoreAPIs:
    @pytest.fixture(autouse=True)
    def setup_engine(self):
        self.engine = OwnershipIntelligenceEngine()
        self.engine.ingest(
            "TCS", _make_financial(), _make_earnings(), _make_bq(),
            ownership_data=_GOOD_OWNERSHIP, insider_data=_GOOD_INSIDER,
        )

    def test_get_ownership_score(self):
        s = self.engine.get_ownership_score("TCS")
        assert s is not None and 0.0 <= s <= 100.0

    def test_get_capital_allocation_score(self):
        s = self.engine.get_capital_allocation_score("TCS")
        assert s is not None and 0.0 <= s <= 100.0

    def test_get_shareholder_value_score(self):
        s = self.engine.get_shareholder_value_score("TCS")
        assert s is not None and 0.0 <= s <= 100.0

    def test_get_insider_alignment_score(self):
        s = self.engine.get_insider_alignment_score("TCS")
        assert s is not None and 0.0 <= s <= 100.0

    def test_get_ownership_risk_score(self):
        s = self.engine.get_ownership_risk_score("TCS")
        assert s is not None and 0.0 <= s <= 100.0

    def test_get_promoter_holding(self):
        p = self.engine.get_promoter_holding("TCS")
        assert p == pytest.approx(52.0)

    def test_get_institutional_holding(self):
        i = self.engine.get_institutional_holding("TCS")
        assert i == pytest.approx(28.0)

    def test_get_alerts_returns_list(self):
        alerts = self.engine.get_alerts("TCS")
        assert isinstance(alerts, list)

    def test_unknown_ticker_apis(self):
        assert self.engine.get_ownership_score("UNKNOWN") is None
        assert self.engine.get_alerts("UNKNOWN") == []


# ── Minimal data graceful degradation ─────────────────────────────────────────

class TestMinimalData:
    def test_no_ownership_data(self):
        engine = OwnershipIntelligenceEngine()
        snap = engine.ingest("X", _make_financial(), _make_earnings(), _make_bq())
        assert 0.0 <= snap.overall_ownership_score <= 100.0
        assert snap.confidence < 0.80

    def test_no_optional_snapshots(self):
        engine = OwnershipIntelligenceEngine()
        snap = engine.ingest(
            "X", _make_financial(), _make_earnings(), _make_bq(),
            valuation_snapshot=None, growth_snapshot=None, management_snapshot=None,
        )
        assert isinstance(snap, OwnershipSnapshot)

    def test_minimal_financial(self):
        fin = MagicMock()
        fin.revenue = None; fin.total_equity = None; fin.total_assets = None
        cf = MagicMock(); cf.free_cash_flow = None; cf.operating_cash_flow = None; cf.capex = None
        fin.cashflow_metrics = cf
        im = MagicMock(); im.net_income = None; fin.income_metrics = im
        bs = MagicMock(); bs.total_debt = None; bs.cash_and_equivalents = None
        fin.balance_sheet_metrics = bs
        fin.ratios = {}

        engine = OwnershipIntelligenceEngine()
        snap = engine.ingest("X", fin, _make_earnings(), _make_bq())
        assert isinstance(snap, OwnershipSnapshot)


# ── Jurisdictions ─────────────────────────────────────────────────────────────

class TestJurisdictions:
    @pytest.mark.parametrize("std", ["generic", "sebi", "sec", "fca", "asx"])
    def test_all_standards(self, std):
        engine = OwnershipIntelligenceEngine()
        snap = engine.ingest(
            "T", _make_financial(), _make_earnings(), _make_bq(),
            ownership_standard=std,
        )
        assert snap.ownership_standard == std
        assert 0.0 <= snap.overall_ownership_score <= 100.0


# ── Risk quality ordering ─────────────────────────────────────────────────────

class TestQualityOrdering:
    def test_good_vs_risky(self):
        eng_good  = OwnershipIntelligenceEngine()
        eng_risky = OwnershipIntelligenceEngine()

        snap_good  = eng_good.ingest(
            "G", _make_financial(), _make_earnings(roic=0.22), _make_bq(),
            ownership_data=_GOOD_OWNERSHIP, insider_data=_GOOD_INSIDER,
        )
        snap_risky = eng_risky.ingest(
            "R", _make_financial(fcf=-50_000), _make_earnings(roic=0.04), _make_bq(),
            ownership_data=_RISKY_OWNERSHIP,
        )
        assert snap_good.overall_ownership_score > snap_risky.overall_ownership_score
        assert snap_risky.ownership_risk.overall_risk_score > snap_good.ownership_risk.overall_risk_score


# ── Thread safety ─────────────────────────────────────────────────────────────

class TestThreadSafety:
    def test_concurrent_ingest(self):
        engine = OwnershipIntelligenceEngine()
        errors: list = []

        def run(ticker):
            try:
                engine.ingest(ticker, _make_financial(), _make_earnings(), _make_bq(),
                              ownership_data=_GOOD_OWNERSHIP)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=run, args=(f"T_{i}",)) for i in range(20)]
        for t in threads: t.start()
        for t in threads: t.join()

        assert errors == []
        assert len(engine.known_tickers()) == 20


# ── Plugin system ─────────────────────────────────────────────────────────────

class TestPluginSystem:
    def test_register_plugin(self):
        class DummyPlugin(OwnershipPlugin):
            @property
            def name(self): return "dummy"
            def evaluate(self, inputs):
                return {"ownership_adjustments": {"overall": 5.0}}

        engine = OwnershipIntelligenceEngine()
        engine.register_ownership_plugin(DummyPlugin())
        snap = engine.ingest(
            "T", _make_financial(), _make_earnings(), _make_bq(),
            ownership_data=_GOOD_OWNERSHIP,
        )
        assert isinstance(snap, OwnershipSnapshot)

    def test_plugin_alert_propagates(self):
        class AlertPlugin(OwnershipPlugin):
            @property
            def name(self): return "alert_plugin"
            def evaluate(self, inputs):
                return {"alerts": ["TEST_ALERT"]}

        engine = OwnershipIntelligenceEngine()
        engine.register_ownership_plugin(AlertPlugin())
        snap = engine.ingest("T", _make_financial(), _make_earnings(), _make_bq())
        assert "TEST_ALERT" in snap.ownership_risk.alerts

    def test_duplicate_plugin_raises(self):
        class DupPlugin(OwnershipPlugin):
            @property
            def name(self): return "dup"
            def evaluate(self, inputs): return {}

        reg = OwnershipPluginRegistry()
        reg.register(DupPlugin())
        with pytest.raises(ValueError):
            reg.register(DupPlugin())

    def test_plugin_exception_does_not_crash_engine(self):
        class BrokenPlugin(OwnershipPlugin):
            @property
            def name(self): return "broken"
            def evaluate(self, inputs): raise RuntimeError("plugin crash")

        engine = OwnershipIntelligenceEngine()
        engine.register_ownership_plugin(BrokenPlugin())
        snap = engine.ingest("T", _make_financial(), _make_earnings(), _make_bq())
        assert isinstance(snap, OwnershipSnapshot)


# ── Snapshot serialization ────────────────────────────────────────────────────

class TestSerialization:
    def test_to_dict_complete(self):
        engine = OwnershipIntelligenceEngine()
        snap = engine.ingest(
            "T", _make_financial(), _make_earnings(), _make_bq(),
            ownership_data=_GOOD_OWNERSHIP,
        )
        d = snap.to_dict()
        assert d["ticker"] == "T"
        assert "ownership_structure" in d
        assert "insider_activity" in d
        assert "capital_allocation" in d
        assert "shareholder_value" in d
        assert "ownership_risk" in d
        assert "ownership_score" in d
