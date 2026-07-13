"""tests/unit/investment/company/earnings/test_earnings_confidence.py"""
import pytest

from iios.investment.company.earnings.earnings_confidence import EarningsConfidenceAnalyzer
from iios.investment.company.earnings.earnings_score import (
    EarningsIntelligenceScore, profitability_to_score, trend_to_score,
)
from iios.investment.company.earnings.earnings_quality import EarningsQualityAnalyzer
from tests.unit.investment.company.earnings.conftest import make_report


class TestEarningsConfidenceAnalyzer:
    def test_zero_history_low_confidence(self):
        c = EarningsConfidenceAnalyzer().analyze([], None)
        assert c.label == "insufficient"
        assert c.score < 30.0

    def test_single_period_low_confidence(self):
        history = [make_report(2024)]
        quality = EarningsQualityAnalyzer().analyze(history)
        c = EarningsConfidenceAnalyzer().analyze(history, quality)
        assert c.label in ["insufficient", "low"]

    def test_rich_history_high_confidence(self, high_quality_history):
        quality = EarningsQualityAnalyzer().analyze(high_quality_history)
        c = EarningsConfidenceAnalyzer().analyze(high_quality_history, quality)
        assert c.score > 50.0
        assert c.label in ["high", "medium"]

    def test_revisions_penalise_confidence(self, high_quality_history):
        quality = EarningsQualityAnalyzer().analyze(high_quality_history)
        clean_c = EarningsConfidenceAnalyzer().analyze(high_quality_history, quality, revision_count=0)
        dirty_c = EarningsConfidenceAnalyzer().analyze(high_quality_history, quality, revision_count=8)
        assert dirty_c.score < clean_c.score

    def test_restatements_penalise_confidence(self, high_quality_history):
        quality = EarningsQualityAnalyzer().analyze(high_quality_history)
        clean_c = EarningsConfidenceAnalyzer().analyze(high_quality_history, quality)
        dirty_c = EarningsConfidenceAnalyzer().analyze(
            high_quality_history, quality, restatement_count=3
        )
        assert dirty_c.score < clean_c.score

    def test_data_sufficiency_increases_with_depth(self):
        for n_periods in [1, 3, 6, 10]:
            history = [make_report(2020 + i) for i in range(n_periods)]
            c = EarningsConfidenceAnalyzer().analyze(history, None)
            if n_periods >= 10:
                assert c.data_sufficiency == pytest.approx(100.0, abs=1)


class TestEarningsScore:
    def test_from_components_computes_weighted_sum(self):
        s = EarningsIntelligenceScore.from_components(
            quality_score=80.0,
            profitability_score=70.0,
            trend_score=60.0,
            risk_stability_score=90.0,
            confidence_score=75.0,
        )
        expected = 80.0 * 0.25 + 70.0 * 0.25 + 60.0 * 0.20 + 90.0 * 0.15 + 75.0 * 0.15
        assert s.overall_score == pytest.approx(expected, abs=0.01)

    def test_to_dict_has_all_fields(self):
        s = EarningsIntelligenceScore.from_components(
            quality_score=70.0, profitability_score=65.0, trend_score=55.0,
            risk_stability_score=80.0, confidence_score=60.0,
        )
        d = s.to_dict()
        for key in ["overall_score", "quality_score", "profitability_score",
                    "trend_score", "risk_score", "confidence_score"]:
            assert key in d

    def test_profitability_to_score_zero_margin(self):
        assert profitability_to_score(0.0, 0.0) == pytest.approx(0.0)

    def test_profitability_to_score_twenty_margin(self):
        assert profitability_to_score(20.0, 20.0) == pytest.approx(100.0)

    def test_profitability_to_score_partial(self):
        score = profitability_to_score(10.0, None)
        assert score == pytest.approx(50.0)

    def test_trend_to_score_mapping(self):
        assert trend_to_score("accelerating")      == pytest.approx(90.0)
        assert trend_to_score("stable")            == pytest.approx(60.0)
        assert trend_to_score("deteriorating")     == pytest.approx(20.0)
        assert trend_to_score("insufficient_data") == pytest.approx(50.0)
        assert trend_to_score("unknown_value")     == pytest.approx(50.0)
