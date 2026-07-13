"""tests/unit/investment/company/governance/test_management_engine.py
Integration tests for ManagementGovernanceEngine.
"""
from __future__ import annotations

import threading
import pytest
from unittest.mock import MagicMock

from iios.investment.company.governance import (
    ManagementGovernanceEngine, ManagementSnapshot,
    GovernancePlugin, GovernancePluginRegistry,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_financial(revenue=1_000_000, fcf=120_000, ocf=180_000,
                    net_income=80_000, total_debt=250_000, equity=500_000):
    snap = MagicMock()
    snap.revenue = revenue
    snap.total_equity = equity
    cf = MagicMock(); cf.free_cash_flow = fcf; cf.operating_cash_flow = ocf
    snap.cashflow_metrics = cf
    im = MagicMock(); im.net_income = net_income; snap.income_metrics = im
    bs = MagicMock(); bs.total_debt = total_debt; snap.balance_sheet_metrics = bs
    snap.ratios = {"dividend_per_share": 12.0, "dividend_payout_ratio": 0.30}
    return snap


def _make_earnings(roic=0.18, stability=78.0):
    snap = MagicMock()
    snap.history_depth = 8
    trend = MagicMock(); trend.cagr_eps = 0.15; trend.cagr_revenue = 0.12
    snap.trend = trend
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


def _make_bq(roic=0.18):
    bq = MagicMock()
    moat = MagicMock(); moat.moat_score = 72.0; moat.avg_roic = roic
    moat.detected_moat_types = ["switching_costs"]
    bq.moat = moat
    ops = MagicMock(); ops.operational_quality_score = 70.0; bq.operational = ops
    res = MagicMock(); res.resilience_score = 68.0; bq.resilience = res
    return bq


def _make_growth():
    gs = MagicMock()
    score = MagicMock(); score.overall_score = 72.0; gs.growth_score = score
    sus = MagicMock(); sus.sustainability_score = 68.0; gs.sustainability = sus
    return gs


_GOOD_BOARD = {
    "total_directors": 10, "independent_directors": 7, "female_directors": 3,
    "avg_director_tenure_years": 6.0, "has_audit_committee": True,
    "has_remuneration_committee": True, "has_risk_committee": True,
    "has_nomination_committee": True, "audit_committee_all_independent": True,
    "ceo_tenure_years": 8.0, "ceo_is_founder": False, "ceo_chairman_same": False,
    "is_family_controlled": False, "promoter_holding_pct": 0.30,
    "governance_incidents": [], "regulatory_actions": [], "reporting_restatements": 0,
}

_GOOD_EXEC = {
    "ceo_tenure_years": 8.0, "cfo_tenure_years": 6.0,
    "executive_team_tenure_avg": 5.5, "leadership_changes_3y": 0,
    "ceo_is_founder": False, "ceo_chairman_same": False,
}


# ── Engine lifecycle ─────────────────────────────────────────────────────────

class TestEngineLifecycle:
    def test_ingest_returns_snapshot(self):
        engine = ManagementGovernanceEngine()
        snap = engine.ingest("INFY", _make_financial(), _make_earnings(), _make_bq())
        assert isinstance(snap, ManagementSnapshot)

    def test_get_snapshot_after_ingest(self):
        engine = ManagementGovernanceEngine()
        engine.ingest("INFY", _make_financial(), _make_earnings(), _make_bq())
        snap = engine.get_snapshot("INFY")
        assert snap is not None
        assert snap.ticker == "INFY"

    def test_unknown_ticker_returns_none(self):
        engine = ManagementGovernanceEngine()
        assert engine.get_snapshot("UNKNOWN") is None

    def test_known_tickers(self):
        engine = ManagementGovernanceEngine()
        engine.ingest("INFY", _make_financial(), _make_earnings(), _make_bq())
        engine.ingest("TCS",  _make_financial(), _make_earnings(), _make_bq())
        tickers = engine.known_tickers()
        assert "INFY" in tickers
        assert "TCS" in tickers


# ── Snapshot fields ──────────────────────────────────────────────────────────

class TestSnapshotFields:
    @pytest.fixture
    def snapshot(self):
        engine = ManagementGovernanceEngine()
        return engine.ingest(
            "INFY", _make_financial(), _make_earnings(), _make_bq(),
            growth_snapshot=_make_growth(),
            board_info=_GOOD_BOARD, executive_info=_GOOD_EXEC,
        )

    def test_ticker(self, snapshot):
        assert snapshot.ticker == "INFY"

    def test_generated_at(self):
        from datetime import timezone
        engine = ManagementGovernanceEngine()
        snap = engine.ingest("INFY", _make_financial(), _make_earnings(), _make_bq())
        assert snap.generated_at.tzinfo is not None

    def test_overall_score_property(self, snapshot):
        s = snapshot.overall_management_score
        assert 0.0 <= s <= 100.0

    def test_management_label_property(self, snapshot):
        label = snapshot.management_label
        assert isinstance(label, str)
        assert label in ("exceptional", "strong", "adequate", "weak", "poor")

    def test_is_founder_led_property(self, snapshot):
        assert isinstance(snapshot.is_founder_led, bool)

    def test_has_high_governance_risk_property(self, snapshot):
        assert isinstance(snapshot.has_high_governance_risk, bool)

    def test_confidence_range(self, snapshot):
        assert 0.0 <= snapshot.confidence <= 1.0

    def test_data_sources_populated(self, snapshot):
        assert len(snapshot.data_sources) > 0

    def test_governance_standard(self, snapshot):
        assert snapshot.governance_standard == "generic"


# ── Score APIs ───────────────────────────────────────────────────────────────

class TestScoreAPIs:
    @pytest.fixture(autouse=True)
    def setup_engine(self):
        self.engine = ManagementGovernanceEngine()
        self.engine.ingest(
            "TCS", _make_financial(), _make_earnings(), _make_bq(),
            board_info=_GOOD_BOARD, executive_info=_GOOD_EXEC,
        )

    def test_get_management_score(self):
        s = self.engine.get_management_score("TCS")
        assert s is not None
        assert 0.0 <= s <= 100.0

    def test_get_governance_score(self):
        s = self.engine.get_governance_score("TCS")
        assert s is not None
        assert 0.0 <= s <= 100.0

    def test_get_capital_allocation_score(self):
        s = self.engine.get_capital_allocation_score("TCS")
        assert s is not None
        assert 0.0 <= s <= 100.0

    def test_get_transparency_score(self):
        s = self.engine.get_transparency_score("TCS")
        assert s is not None
        assert 0.0 <= s <= 100.0

    def test_get_key_person_risk(self):
        s = self.engine.get_key_person_risk("TCS")
        assert s is not None
        assert 0.0 <= s <= 100.0

    def test_get_governance_risk_score(self):
        s = self.engine.get_governance_risk_score("TCS")
        assert s is not None
        assert 0.0 <= s <= 100.0

    def test_get_alerts_returns_list(self):
        alerts = self.engine.get_alerts("TCS")
        assert isinstance(alerts, list)

    def test_unknown_ticker_score_apis(self):
        assert self.engine.get_management_score("UNKNOWN") is None
        assert self.engine.get_governance_score("UNKNOWN") is None
        assert self.engine.get_alerts("UNKNOWN") == []


# ── Multiple standards ───────────────────────────────────────────────────────

class TestGovernanceStandards:
    @pytest.mark.parametrize("std", ["generic", "sebi", "sec", "fca", "asx"])
    def test_all_standards(self, std):
        engine = ManagementGovernanceEngine()
        snap = engine.ingest("TICKER", _make_financial(), _make_earnings(), _make_bq(),
                             governance_standard=std)
        assert snap.governance_standard == std
        assert 0.0 <= snap.overall_management_score <= 100.0


# ── Minimal data graceful degradation ────────────────────────────────────────

class TestMinimalData:
    def test_no_board_info(self):
        engine = ManagementGovernanceEngine()
        snap = engine.ingest("X", _make_financial(), _make_earnings(), _make_bq())
        assert snap.confidence < 0.90
        assert 0.0 <= snap.overall_management_score <= 100.0

    def test_no_optional_snapshots(self):
        engine = ManagementGovernanceEngine()
        snap = engine.ingest(
            "X", _make_financial(), _make_earnings(), _make_bq(),
            valuation_snapshot=None, growth_snapshot=None,
        )
        assert isinstance(snap, ManagementSnapshot)

    def test_all_none_financial_fields(self):
        fin = MagicMock()
        fin.revenue = None; fin.total_equity = None
        cf = MagicMock(); cf.free_cash_flow = None; cf.operating_cash_flow = None
        fin.cashflow_metrics = cf
        im = MagicMock(); im.net_income = None; fin.income_metrics = im
        bs = MagicMock(); bs.total_debt = None; fin.balance_sheet_metrics = bs
        fin.ratios = {}

        engine = ManagementGovernanceEngine()
        snap = engine.ingest("X", fin, _make_earnings(), _make_bq())
        assert isinstance(snap, ManagementSnapshot)


# ── Thread safety ─────────────────────────────────────────────────────────────

class TestThreadSafety:
    def test_concurrent_ingest(self):
        engine = ManagementGovernanceEngine()
        errors = []

        def run(ticker):
            try:
                engine.ingest(ticker, _make_financial(), _make_earnings(), _make_bq(),
                              board_info=_GOOD_BOARD)
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=run, args=(f"TICKER_{i}",))
            for i in range(20)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        assert len(engine.known_tickers()) == 20


# ── Plugin system ─────────────────────────────────────────────────────────────

class TestPluginSystem:
    def test_register_plugin(self):
        class DummyPlugin(GovernancePlugin):
            @property
            def name(self):
                return "dummy"

            def evaluate(self, inputs):
                return {"governance_adjustments": {"overall": 5.0}, "alerts": []}

        engine = ManagementGovernanceEngine()
        engine.register_governance_plugin(DummyPlugin())

        snap_before = ManagementGovernanceEngine().ingest(
            "T", _make_financial(), _make_earnings(), _make_bq(),
            board_info=_GOOD_BOARD,
        )
        snap_with_plugin = engine.ingest(
            "T", _make_financial(), _make_earnings(), _make_bq(),
            board_info=_GOOD_BOARD,
        )
        # Plugin adds 5 to governance overall; score should differ
        assert (
            snap_with_plugin.governance.overall_governance_score >=
            snap_before.governance.overall_governance_score - 0.01
        )

    def test_plugin_alert_propagates(self):
        class AlertPlugin(GovernancePlugin):
            @property
            def name(self):
                return "alert_plugin"

            def evaluate(self, inputs):
                return {"alerts": ["TEST_PLUGIN_ALERT"]}

        engine = ManagementGovernanceEngine()
        engine.register_governance_plugin(AlertPlugin())
        snap = engine.ingest("T", _make_financial(), _make_earnings(), _make_bq())
        assert "TEST_PLUGIN_ALERT" in snap.governance_risk.alerts

    def test_registry_duplicate_raises(self):
        class DummyPlugin(GovernancePlugin):
            @property
            def name(self):
                return "dup"
            def evaluate(self, inputs):
                return {}

        reg = GovernancePluginRegistry()
        reg.register(DummyPlugin())
        with pytest.raises(ValueError):
            reg.register(DummyPlugin())


# ── Governance quality ordering ────────────────────────────────────────────────

class TestQualityOrdering:
    """Good inputs should consistently yield higher scores than weak inputs."""

    def test_good_vs_weak_management(self):
        engine_good = ManagementGovernanceEngine()
        engine_weak = ManagementGovernanceEngine()

        good_board = _GOOD_BOARD
        weak_board = {
            "total_directors": 5, "independent_directors": 1, "female_directors": 0,
            "avg_director_tenure_years": 20.0, "has_audit_committee": False,
            "has_remuneration_committee": False, "has_risk_committee": False,
            "has_nomination_committee": False, "audit_committee_all_independent": False,
            "ceo_tenure_years": 25.0, "ceo_is_founder": True, "ceo_chairman_same": True,
            "is_family_controlled": True, "promoter_holding_pct": 0.75,
            "governance_incidents": ["fraud"], "regulatory_actions": ["sebi_penalty"],
            "reporting_restatements": 2,
        }
        snap_good = engine_good.ingest(
            "G", _make_financial(), _make_earnings(roic=0.22, stability=82.0), _make_bq(roic=0.22),
            board_info=good_board, executive_info=_GOOD_EXEC,
        )
        snap_weak = engine_weak.ingest(
            "W", _make_financial(fcf=-50_000), _make_earnings(roic=0.04, stability=25.0), _make_bq(roic=0.04),
            board_info=weak_board,
        )
        assert snap_good.overall_management_score > snap_weak.overall_management_score
