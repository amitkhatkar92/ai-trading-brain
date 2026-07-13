"""tests/unit/investment/company/earnings/test_earnings_quality.py"""
import pytest

from iios.investment.company.earnings.earnings_quality import EarningsQualityAnalyzer, _score_to_label
from iios.investment.company.earnings.earnings_consistency import EarningsConsistencyChecker
from iios.investment.company.earnings.earnings_persistence import EarningsPersistenceAnalyzer
from iios.investment.company.earnings.earnings_reliability import EarningsReliabilityAnalyzer
from iios.investment.company.earnings.earnings_report import EarningsQualityLabel
from tests.unit.investment.company.earnings.conftest import make_report


class TestEarningsQualityAnalyzer:
    def test_empty_history_returns_insufficient(self):
        q = EarningsQualityAnalyzer().analyze([])
        assert q.label == EarningsQualityLabel.INSUFFICIENT

    def test_high_quality_history_scores_well(self, high_quality_history):
        q = EarningsQualityAnalyzer().analyze(high_quality_history)
        assert q.overall_score > 60.0
        assert q.label in [EarningsQualityLabel.HIGH, EarningsQualityLabel.ABOVE_AVERAGE, EarningsQualityLabel.AVERAGE]

    def test_high_accruals_lowers_score(self):
        bad_history = [
            make_report(fy, accruals=0.20, ocf_to_ni=0.4)
            for fy in range(2019, 2025)
        ]
        good_history = [
            make_report(fy, accruals=0.01, ocf_to_ni=1.5)
            for fy in range(2019, 2025)
        ]
        bad_q  = EarningsQualityAnalyzer().analyze(bad_history)
        good_q = EarningsQualityAnalyzer().analyze(good_history)
        assert bad_q.overall_score < good_q.overall_score

    def test_cash_quality_score_populated(self, high_quality_history):
        q = EarningsQualityAnalyzer().analyze(high_quality_history)
        assert q.cash_quality_score > 0
        assert q.avg_ocf_to_ni is not None

    def test_score_to_label_mapping(self):
        assert _score_to_label(85.0) == EarningsQualityLabel.HIGH
        assert _score_to_label(67.0) == EarningsQualityLabel.ABOVE_AVERAGE
        assert _score_to_label(55.0) == EarningsQualityLabel.AVERAGE
        assert _score_to_label(40.0) == EarningsQualityLabel.BELOW_AVERAGE
        assert _score_to_label(20.0) == EarningsQualityLabel.LOW

    def test_to_dict(self, high_quality_history):
        d = EarningsQualityAnalyzer().analyze(high_quality_history).to_dict()
        assert "overall_score" in d
        assert "label" in d
        assert "cash_quality_score" in d


class TestEarningsConsistency:
    def test_consistent_history_scores_high(self, growing_history):
        m = EarningsConsistencyChecker().analyze(growing_history)
        assert m.score > 60.0
        assert m.profitability_rate == pytest.approx(1.0)

    def test_volatile_history_scores_lower(self, volatile_history):
        consistent_score  = EarningsConsistencyChecker().analyze(growing_history := [
            make_report(fy, eps=float(fy), net_margin=10.0) for fy in range(2019, 2025)
        ]).score
        volatile_score = EarningsConsistencyChecker().analyze(volatile_history).score
        assert volatile_score < consistent_score

    def test_consecutive_profits(self, growing_history):
        m = EarningsConsistencyChecker().analyze(growing_history)
        assert m.consecutive_profits == 5

    def test_consecutive_profits_breaks_on_loss(self, volatile_history):
        m = EarningsConsistencyChecker().analyze(volatile_history)
        # Last period is profitable (2024), one before is loss (2023)
        assert m.consecutive_profits == 1

    def test_empty_history(self):
        m = EarningsConsistencyChecker().analyze([])
        assert m.score == 0.0


class TestEarningsPersistence:
    def test_high_ocf_boosts_score(self, high_quality_history):
        m = EarningsPersistenceAnalyzer().analyze(high_quality_history)
        assert m.avg_cash_conversion is not None
        assert m.avg_cash_conversion > 1.0
        assert m.score > 60.0

    def test_high_accruals_lowers_score(self):
        history = [make_report(fy, accruals=0.20, ocf_to_ni=0.3) for fy in range(2019, 2025)]
        m = EarningsPersistenceAnalyzer().analyze(history)
        assert m.high_accrual_periods == 6
        assert m.score < 60.0

    def test_accruals_trend_improving(self):
        history = [
            make_report(fy, accruals=0.10 - (fy - 2019) * 0.01)
            for fy in range(2019, 2025)
        ]
        m = EarningsPersistenceAnalyzer().analyze(history)
        assert m.accruals_trend in ("improving", "stable")

    def test_eps_ar1_estimated(self, growing_history):
        m = EarningsPersistenceAnalyzer().analyze(growing_history)
        assert m.eps_ar1 is not None


class TestEarningsReliability:
    def test_no_revisions_high_score(self, growing_history):
        m = EarningsReliabilityAnalyzer().analyze(growing_history)
        assert m.revision_score == pytest.approx(100.0)
        assert m.reporting_score == pytest.approx(100.0)

    def test_revisions_penalise_score(self, growing_history):
        clean = EarningsReliabilityAnalyzer().analyze(growing_history, revision_count=0)
        dirty = EarningsReliabilityAnalyzer().analyze(growing_history, revision_count=5)
        assert dirty.overall_score < clean.overall_score
        assert "frequent_revisions:5" in dirty.flags

    def test_restatements_penalise_reporting(self, growing_history):
        m = EarningsReliabilityAnalyzer().analyze(growing_history, restatement_count=2)
        assert "restatements:2" in m.flags
        assert m.reporting_score < 100.0

    def test_to_dict(self, growing_history):
        d = EarningsReliabilityAnalyzer().analyze(growing_history).to_dict()
        assert "overall_score" in d
        assert "consistency_score" in d
