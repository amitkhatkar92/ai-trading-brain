"""tests/unit/investment/company/opportunity/test_opportunity_models.py
Tests for core models: profiles, statistics, score breakdown.
"""
from __future__ import annotations

import pytest

from iios.investment.company.opportunity.opportunity_profile import (
    AlertSeverity, ChangeSignal, ComponentScore, ConfidenceLevel,
    OpportunityAlert, OpportunityCategory, OpportunityLifecycle,
    OpportunityPriority, OpportunityScoreBreakdown, OpportunityStrength,
    WatchlistEntry,
)
from iios.investment.company.opportunity.opportunity_statistics import (
    clamp, compute_data_completeness, confidence_to_level,
    moving_average, percentile_rank, safe_average, score_to_priority,
    score_to_strength, trend_slope, weighted_average,
)
from iios.investment.company.opportunity.opportunity_category import (
    ClassificationResult, get_category_description,
)


class TestOpportunityEnums:
    def test_category_values(self):
        cats = [c.value for c in OpportunityCategory]
        assert "undervalued_quality" in cats
        assert "compounder" in cats
        assert "wide_moat" in cats
        assert len(cats) == 16

    def test_lifecycle_values(self):
        states = [s.value for s in OpportunityLifecycle]
        assert "discovered" in states
        assert "high_conviction" in states
        assert "archived" in states
        assert len(states) == 8

    def test_priority_values(self):
        assert len(list(OpportunityPriority)) == 5

    def test_strength_values(self):
        assert len(list(OpportunityStrength)) == 6

    def test_confidence_level_values(self):
        assert len(list(ConfidenceLevel)) == 5


class TestComponentScore:
    def test_to_dict(self):
        c = ComponentScore("business_quality", 72.0, 0.25, 18.0, True)
        d = c.to_dict()
        assert d["name"] == "business_quality"
        assert d["score"] == 72.0
        assert d["available"] is True

    def test_unavailable(self):
        c = ComponentScore("growth_quality", 50.0, 0.15, 7.5, False)
        assert not c.available


class TestOpportunityScoreBreakdown:
    @pytest.fixture
    def breakdown(self):
        def _c(name, score, w):
            return ComponentScore(name, score, w, score * w, True)
        return OpportunityScoreBreakdown(
            financial_strength=_c("financial_strength", 70.0, 0.20),
            earnings_quality=_c("earnings_quality", 75.0, 0.10),
            business_quality=_c("business_quality", 80.0, 0.25),
            valuation_attractiveness=_c("valuation_attractiveness", 65.0, 0.15),
            growth_quality=_c("growth_quality", 70.0, 0.15),
            management_quality=_c("management_quality", 68.0, 0.08),
            ownership_quality=_c("ownership_quality", 65.0, 0.07),
            risk_penalty=5.0,
            raw_score=72.0,
            final_score=67.0,
        )

    def test_components_count(self, breakdown):
        assert len(breakdown.components()) == 7

    def test_available_components(self, breakdown):
        assert len(breakdown.available_components()) == 7

    def test_to_dict_keys(self, breakdown):
        d = breakdown.to_dict()
        assert "final_score" in d
        assert "risk_penalty" in d
        assert "business_quality" in d

    def test_final_score_range(self, breakdown):
        assert 0.0 <= breakdown.final_score <= 100.0


class TestOpportunityAlert:
    def test_creation(self):
        a = OpportunityAlert("test alert", AlertSeverity.HIGH, "test")
        assert a.message == "test alert"
        assert a.severity == AlertSeverity.HIGH

    def test_to_dict(self):
        a = OpportunityAlert("alert", AlertSeverity.MEDIUM, "src")
        d = a.to_dict()
        assert d["severity"] == "medium"
        assert d["source"] == "src"


class TestStatistics:
    def test_clamp(self):
        assert clamp(150.0) == 100.0
        assert clamp(-10.0) == 0.0
        assert clamp(50.0) == 50.0
        assert clamp(50.0, 0.0, 40.0) == 40.0

    def test_safe_average_none(self):
        assert safe_average([None, None]) == 50.0

    def test_safe_average_mixed(self):
        assert safe_average([60.0, None, 80.0]) == pytest.approx(70.0)

    def test_weighted_average(self):
        result = weighted_average([(80.0, 0.6), (40.0, 0.4)])
        assert result == pytest.approx(64.0)

    def test_weighted_average_zero(self):
        assert weighted_average([]) == 50.0

    def test_percentile_rank(self):
        pop = [10.0, 20.0, 30.0, 40.0, 50.0]
        assert percentile_rank(50.0, pop) == 80.0
        assert percentile_rank(10.0, pop) == 0.0

    def test_trend_slope_positive(self):
        assert trend_slope([1.0, 2.0, 3.0, 4.0, 5.0]) > 0

    def test_trend_slope_negative(self):
        assert trend_slope([5.0, 4.0, 3.0, 2.0, 1.0]) < 0

    def test_trend_slope_flat(self):
        assert trend_slope([50.0, 50.0, 50.0]) == pytest.approx(0.0)

    def test_moving_average(self):
        result = moving_average([10.0, 20.0, 30.0], 2)
        assert result[-1] == pytest.approx(25.0)

    def test_score_to_strength(self):
        assert score_to_strength(85.0) == OpportunityStrength.EXCEPTIONAL
        assert score_to_strength(67.0) == OpportunityStrength.STRONG
        assert score_to_strength(55.0) == OpportunityStrength.MODERATE
        assert score_to_strength(38.0) == OpportunityStrength.WEAK
        assert score_to_strength(20.0) == OpportunityStrength.POOR

    def test_score_to_priority(self):
        p = score_to_priority(78.0, OpportunityLifecycle.HIGH_CONVICTION)
        assert p == OpportunityPriority.CRITICAL
        p = score_to_priority(30.0, OpportunityLifecycle.EXPIRED)
        assert p == OpportunityPriority.WATCHLIST

    def test_confidence_to_level(self):
        assert confidence_to_level(0.90) == ConfidenceLevel.VERY_HIGH
        assert confidence_to_level(0.70) == ConfidenceLevel.HIGH
        assert confidence_to_level(0.55) == ConfidenceLevel.MODERATE
        assert confidence_to_level(0.40) == ConfidenceLevel.LOW
        assert confidence_to_level(0.20) == ConfidenceLevel.VERY_LOW

    def test_data_completeness(self):
        assert compute_data_completeness(7, 7) == pytest.approx(1.0)
        assert compute_data_completeness(3, 7) == pytest.approx(3 / 7)
        assert compute_data_completeness(0, 7) == pytest.approx(0.0)


class TestClassificationResult:
    def test_is_actionable(self):
        r = ClassificationResult(OpportunityCategory.COMPOUNDER)
        assert r.is_actionable is True

    def test_not_actionable(self):
        r = ClassificationResult(OpportunityCategory.OBSERVATION_ONLY)
        assert r.is_actionable is False

    def test_is_value_oriented(self):
        r = ClassificationResult(OpportunityCategory.UNDERVALUED_QUALITY)
        assert r.is_value_oriented is True

    def test_is_growth_oriented(self):
        r = ClassificationResult(OpportunityCategory.HIGH_GROWTH)
        assert r.is_growth_oriented is True

    def test_all_categories(self):
        r = ClassificationResult(
            OpportunityCategory.COMPOUNDER,
            secondary=[OpportunityCategory.WIDE_MOAT],
        )
        assert len(r.all_categories) == 2

    def test_to_dict(self):
        r = ClassificationResult(OpportunityCategory.INCOME, confidence=0.75)
        d = r.to_dict()
        assert d["primary"] == "income"
        assert d["confidence"] == pytest.approx(0.75, abs=0.001)

    def test_category_description(self):
        desc = get_category_description(OpportunityCategory.COMPOUNDER)
        assert isinstance(desc, str) and len(desc) > 10
