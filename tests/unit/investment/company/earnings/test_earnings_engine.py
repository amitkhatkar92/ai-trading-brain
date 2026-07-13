"""tests/unit/investment/company/earnings/test_earnings_engine.py
Integration tests for EarningsIntelligenceEngine.
"""
import threading
import pytest

from iios.investment.company.earnings.earnings_intelligence_engine import EarningsIntelligenceEngine
from iios.investment.company.earnings.earnings_report import TrendDirection, EarningsQualityLabel
from iios.investment.company.earnings.earnings_revision import EarningsRevisionTracker
from tests.unit.investment.company.earnings.conftest import make_report


@pytest.fixture
def engine():
    return EarningsIntelligenceEngine()


@pytest.fixture
def populated_engine(growing_history):
    e = EarningsIntelligenceEngine()
    for r in growing_history:
        e.ingest_report("TATA", r)
    return e


class TestIngestReport:
    def test_ingest_returns_snapshot(self, engine, single_report):
        snap = engine.ingest_report("INFY", single_report)
        assert snap.ticker == "INFY"
        assert snap.latest_report is not None

    def test_ingest_multiple_grows_history(self, engine, growing_history):
        for r in growing_history:
            engine.ingest_report("HDFC", r)
        assert engine.history_depth("HDFC") == len(growing_history)

    def test_ingest_updates_snapshot(self, engine, growing_history):
        for r in growing_history[:3]:
            engine.ingest_report("X", r)
        snap1 = engine.get_snapshot("X")
        engine.ingest_report("X", growing_history[3])
        snap2 = engine.get_snapshot("X")
        assert snap2.history_depth > snap1.history_depth

    def test_revision_detected_on_reingestion(self, engine, single_report):
        engine.ingest_report("A", single_report)
        revised = make_report(single_report.fiscal_year, eps=12.0)
        revised.period_label = single_report.period_label
        engine.ingest_report("A", revised)
        rev_summary = engine.revision_summary("A")
        assert rev_summary["total_revisions"] >= 1

    def test_callback_invoked(self, single_report):
        called = []
        e = EarningsIntelligenceEngine(on_snapshot_updated=called.append)
        e.ingest_report("Z", single_report)
        assert len(called) == 1
        assert called[0].ticker == "Z"

    def test_callback_exception_does_not_propagate(self, single_report):
        def bad_callback(snap):
            raise RuntimeError("callback error")
        e = EarningsIntelligenceEngine(on_snapshot_updated=bad_callback)
        snap = e.ingest_report("Z", single_report)
        assert snap.ticker == "Z"


class TestQueryAPIs:
    def test_get_snapshot_unknown_ticker_returns_none(self, engine):
        assert engine.get_snapshot("UNKNOWN") is None

    def test_get_latest_report(self, populated_engine, growing_history):
        r = populated_engine.get_latest_report("TATA")
        assert r is not None
        assert r.fiscal_year == growing_history[-1].fiscal_year

    def test_get_history_returns_list(self, populated_engine, growing_history):
        h = populated_engine.get_history("TATA")
        assert len(h) == len(growing_history)

    def test_get_quality_score_numeric(self, populated_engine):
        q = populated_engine.get_quality_score("TATA")
        assert q is not None
        assert 0.0 <= q <= 100.0

    def test_get_trend_direction(self, populated_engine):
        t = populated_engine.get_trend("TATA")
        assert isinstance(t, TrendDirection)

    def test_get_confidence(self, populated_engine):
        c = populated_engine.get_confidence("TATA")
        assert c is not None
        assert 0.0 <= c <= 100.0

    def test_known_tickers(self, engine, growing_history):
        for r in growing_history:
            engine.ingest_report("WIPRO", r)
        engine.ingest_report("INFY", make_report(2024))
        tickers = engine.known_tickers()
        assert "WIPRO" in tickers
        assert "INFY" in tickers

    def test_get_quality_statistics(self, populated_engine):
        qs = populated_engine.get_quality_statistics("TATA")
        assert qs is not None
        assert qs.periods_assessed == 5
        assert qs.mean_eps is not None

    def test_revision_summary_no_revisions(self, populated_engine):
        s = populated_engine.revision_summary("TATA")
        assert s["total_revisions"] == 0

    def test_get_risk_profile(self, populated_engine):
        rp = populated_engine.get_risk_profile("TATA")
        assert rp is not None
        assert rp.earnings_stability_score >= 0.0

    def test_get_profitability(self, populated_engine):
        p = populated_engine.get_profitability("TATA")
        assert p is not None
        assert p.net_margin is not None


class TestOverallScore:
    def test_overall_score_in_range(self, populated_engine):
        snap = populated_engine.get_snapshot("TATA")
        assert 0.0 <= snap.overall_score <= 100.0

    def test_high_quality_scores_higher(self):
        good_engine = EarningsIntelligenceEngine()
        bad_engine  = EarningsIntelligenceEngine()

        for fy in range(2019, 2025):
            good_engine.ingest_report("G", make_report(
                fy, net_margin=18.0, roe=20.0, roic=18.0, ocf_to_ni=1.5, accruals=0.01,
                eps=float(fy - 2010),
            ))
            bad_engine.ingest_report("B", make_report(
                fy, net_margin=3.0, roe=3.0, roic=2.0, ocf_to_ni=0.3, accruals=0.20,
                eps=2.0,
            ))

        good_snap = good_engine.get_snapshot("G")
        bad_snap  = bad_engine.get_snapshot("B")
        assert good_snap.overall_score > bad_snap.overall_score


class TestThreadSafety:
    def test_concurrent_ingestion(self, growing_history):
        engine  = EarningsIntelligenceEngine()
        errors  = []

        def ingest_all(ticker):
            try:
                for r in growing_history:
                    engine.ingest_report(ticker, r)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=ingest_all, args=(f"T{i}",)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"Errors in threads: {errors}"
        assert len(engine.known_tickers()) == 10


class TestEarningsSnapshotProperties:
    def test_current_eps_property(self, populated_engine):
        snap = populated_engine.get_snapshot("TATA")
        assert snap.current_eps is not None

    def test_is_profitable_property(self, populated_engine):
        snap = populated_engine.get_snapshot("TATA")
        assert snap.is_profitable is True

    def test_roe_property(self, populated_engine):
        snap = populated_engine.get_snapshot("TATA")
        assert snap.roe is not None

    def test_roic_property(self, populated_engine):
        snap = populated_engine.get_snapshot("TATA")
        assert snap.roic is not None
