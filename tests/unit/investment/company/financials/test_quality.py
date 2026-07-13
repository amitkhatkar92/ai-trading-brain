"""tests/unit/investment/company/financials/test_quality.py
Tests for StatementConsistencyChecker, RestatementTracker, QualityStatisticsEngine.
"""
import pytest

from iios.investment.company.financials.statement_consistency import StatementConsistencyChecker
from iios.investment.company.financials.restatement_tracker import RestatementTracker, RestatementEvent
from iios.investment.company.financials.quality_statistics import QualityStatisticsEngine, FinancialQualityScore
from iios.investment.company.financials.balance_sheet import BalanceSheet


class TestStatementConsistency:
    def test_consistent_bs_no_issues(self, sample_bs, sample_is, sample_cf):
        checker = StatementConsistencyChecker()
        report = checker.check(sample_bs, sample_is, sample_cf)
        # assets = 5150, liabilities + equity = 2300 + 2850 = 5150
        bs_issues = [i for i in report.issues if i.check == "assets=liabilities+equity"]
        assert len(bs_issues) == 0
        assert report.score > 0

    def test_inconsistent_bs_detected(self, annual_period):
        bs = BalanceSheet(
            period=annual_period,
            total_assets=1000.0,
            total_liabilities=400.0,
            total_equity=400.0,   # wrong: should be 600
        )
        checker = StatementConsistencyChecker()
        report = checker.check(bs, None, None)
        issues = [i for i in report.issues if i.check == "assets=liabilities+equity"]
        assert len(issues) == 1

    def test_cf_reconciliation(self, sample_cf):
        checker = StatementConsistencyChecker()
        report = checker.check(None, None, sample_cf)
        # OCF=1862.5, ICF=-550, CFF=-350 → expected net=962.5; actual=962.5 → ok
        cf_issues = [i for i in report.issues if i.check == "net_change=OCF+ICF+CFF"]
        assert len(cf_issues) == 0

    def test_gross_profit_check(self, sample_bs, sample_is):
        checker = StatementConsistencyChecker()
        report = checker.check(sample_bs, sample_is, None)
        gp_issues = [i for i in report.issues if i.check == "gross_profit=revenue-cogs"]
        # 3500 == 10000 - 6500 → no issue
        assert len(gp_issues) == 0

    def test_none_inputs(self):
        checker = StatementConsistencyChecker()
        report = checker.check(None, None, None)
        assert report.score == 100.0

    def test_to_dict(self, sample_bs, sample_is, sample_cf):
        checker = StatementConsistencyChecker()
        d = checker.check(sample_bs, sample_is, sample_cf).to_dict()
        assert "is_consistent" in d
        assert "score" in d


class TestRestatementTracker:
    def test_record_and_get(self):
        tracker = RestatementTracker()
        event = RestatementEvent(
            ticker="RELIANCE",
            period_label="FY24",
            version_from=1,
            version_to=2,
            reason="late_amendment",
        )
        tracker.record(event)
        assert tracker.restatement_count("RELIANCE") == 1
        events = tracker.get_events("RELIANCE")
        assert events[0].reason == "late_amendment"

    def test_was_restated(self):
        tracker = RestatementTracker()
        tracker.record(RestatementEvent("X", "FY24", 1, 2, "reason"))
        assert tracker.was_restated("X", "FY24") is True
        assert tracker.was_restated("X", "FY23") is False

    def test_detect_material_change(self):
        tracker = RestatementTracker()
        old = {"total_assets": 1000.0, "total_equity": 500.0}
        new = {"total_assets": 1200.0, "total_equity": 500.0}   # 20% change
        event = tracker.detect_and_record("TCS", "FY24", old, new, 1, 2)
        assert event is not None
        assert "total_assets" in event.fields_changed

    def test_no_event_on_small_change(self):
        tracker = RestatementTracker()
        old = {"total_assets": 1000.0}
        new = {"total_assets": 1005.0}   # 0.5% change < 1% threshold
        event = tracker.detect_and_record("INFY", "FY24", old, new, 1, 2)
        assert event is None

    def test_max_events_enforced(self):
        tracker = RestatementTracker(max_events_per_ticker=3)
        for i in range(10):
            tracker.record(RestatementEvent("Y", f"FY{i}", i, i+1, "r"))
        assert len(tracker.get_events("Y")) == 3

    def test_summary(self):
        tracker = RestatementTracker()
        tracker.record(RestatementEvent("HDFC", "FY24", 1, 2, "revision"))
        s = tracker.summary("HDFC")
        assert s["total_restatements"] == 1
        assert "FY24" in s["periods_restated"]

    def test_unknown_ticker_no_events(self):
        tracker = RestatementTracker()
        assert tracker.restatement_count("UNKNOWN") == 0
        assert tracker.get_events("UNKNOWN") == []


class TestQualityStatisticsEngine:
    def test_perfect_quality(self):
        engine = QualityStatisticsEngine()
        score = engine.compute(
            completeness_pct=100.0,
            consistency_report=None,
            restatement_count=0,
            periods_with_data=8,
            periods_expected=8,
        )
        assert score.overall_score == pytest.approx(100.0)
        assert score.flags == []

    def test_low_completeness_penalty(self):
        engine = QualityStatisticsEngine()
        score = engine.compute(
            completeness_pct=50.0,
            consistency_report=None,
            restatement_count=0,
            periods_with_data=4,
            periods_expected=8,
        )
        # completeness contributes 35% weight; 50*0.35 = 17.5
        # reporting coverage 4/8=50% → 50*0.10 = 5
        # total ~82.5
        assert score.overall_score < 90.0

    def test_restatement_penalty(self):
        engine = QualityStatisticsEngine()
        score_clean = engine.compute(100.0, None, 0, 8, 8)
        score_dirty = engine.compute(100.0, None, 3, 8, 8)
        assert score_dirty.overall_score < score_clean.overall_score

    def test_flags_on_restatements(self):
        engine = QualityStatisticsEngine()
        score = engine.compute(100.0, None, 2, 8, 8)
        assert any("restatements" in f for f in score.flags)

    def test_to_dict(self):
        engine = QualityStatisticsEngine()
        score = engine.compute(80.0, None, 1, 6, 8)
        d = score.to_dict()
        assert "overall_score" in d
        assert "completeness_score" in d
        assert "restatements" in d

    def test_recompute(self):
        score = FinancialQualityScore(
            completeness_score=80.0,
            consistency_score=90.0,
            restatement_score=100.0,
            reporting_score=100.0,
        )
        score.recompute()
        expected = 80*0.35 + 90*0.35 + 100*0.20 + 100*0.10
        assert score.overall_score == pytest.approx(expected)
