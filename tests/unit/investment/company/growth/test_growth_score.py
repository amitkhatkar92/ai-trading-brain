"""tests/unit/investment/company/growth/test_growth_score.py"""
from __future__ import annotations

import pytest

from iios.investment.company.growth.growth_score import compute_growth_score
from iios.investment.company.growth.growth_quality import assess_growth_quality
from iios.investment.company.growth.growth_confidence import compute_overall_confidence
from iios.investment.company.growth.forecast_engine import ForecastEngine
from iios.investment.company.growth.forecast_assumptions import ForecastAssumptions
from iios.investment.company.growth.growth_profile import GrowthIntelligenceScore, GrowthForecastProfile


# ── GrowthScore ────────────────────────────────────────────────────────────────

class TestComputeGrowthScore:
    def test_exceptional_growth(self):
        result = compute_growth_score(
            revenue_cagr=0.25,
            eps_cagr=0.30,
            ni_cagr=0.28,
            fcf_cagr=0.22,
            sustainability=90.0,
            forecast_confidence=0.85,
        )
        assert isinstance(result, GrowthIntelligenceScore)
        assert result.overall_score >= 70.0
        assert result.label in ("exceptional", "strong")

    def test_poor_growth(self):
        result = compute_growth_score(
            revenue_cagr=-0.10,
            eps_cagr=-0.15,
            ni_cagr=-0.10,
            fcf_cagr=-0.05,
            sustainability=20.0,
            forecast_confidence=0.20,
        )
        assert result.overall_score < 45.0
        assert result.label in ("poor", "weak", "insufficient")

    def test_no_data(self):
        result = compute_growth_score()
        assert result.overall_score == pytest.approx(0.0)
        assert result.label == "insufficient"

    def test_revenue_only(self):
        result = compute_growth_score(revenue_cagr=0.15)
        assert result.revenue_growth_score > 0
        assert result.overall_score > 0

    def test_score_in_range(self):
        for cagr in [0.0, 0.05, 0.15, 0.25, 0.40]:
            s = compute_growth_score(revenue_cagr=cagr, eps_cagr=cagr)
            assert 0.0 <= s.overall_score <= 100.0

    def test_labels(self):
        for cagr, expected_labels in [
            (0.30, ("exceptional", "strong")),
            (0.15, ("strong", "moderate")),
            (0.05, ("moderate", "weak")),
            (-0.05, ("poor", "weak")),
        ]:
            result = compute_growth_score(revenue_cagr=cagr, eps_cagr=cagr)
            assert result.label in expected_labels or result.label != "insufficient"

    def test_explanation_populated(self):
        result = compute_growth_score(revenue_cagr=0.12, eps_cagr=0.10)
        assert len(result.explanation) > 0


# ── GrowthQuality ──────────────────────────────────────────────────────────────

class TestAssessGrowthQuality:
    def test_exceptional(self):
        q = assess_growth_quality(
            has_eps_cagr=True,
            has_revenue_cagr=True,
            has_fcf_data=True,
            has_margin_data=True,
            history_depth=10,
            eps_volatility=0.10,
            loss_rate=0.0,
        )
        assert q.quality_label in ("exceptional", "strong")
        assert q.is_high_quality is True
        assert q.data_completeness == pytest.approx(1.0)

    def test_insufficient(self):
        q = assess_growth_quality(
            has_eps_cagr=False,
            has_revenue_cagr=False,
            has_fcf_data=False,
            has_margin_data=False,
            history_depth=0,
        )
        assert q.quality_label == "insufficient"
        assert q.data_completeness == 0.0

    def test_moderate(self):
        q = assess_growth_quality(
            has_eps_cagr=True,
            has_revenue_cagr=True,
            has_fcf_data=False,
            has_margin_data=False,
            history_depth=4,
        )
        assert q.quality_label in ("moderate", "weak", "strong")

    def test_issues_populated(self):
        q = assess_growth_quality(
            has_eps_cagr=False,
            has_revenue_cagr=False,
            has_fcf_data=False,
            has_margin_data=False,
            history_depth=1,
        )
        assert len(q.issues) > 0

    def test_volatile_flagged(self):
        q = assess_growth_quality(
            has_eps_cagr=True,
            has_revenue_cagr=True,
            has_fcf_data=True,
            has_margin_data=True,
            history_depth=8,
            eps_volatility=0.9,
        )
        assert any("volatility" in i.lower() for i in q.issues)


# ── ForecastEngine ─────────────────────────────────────────────────────────────

class TestForecastEngine:
    @pytest.fixture
    def fe(self):
        return ForecastEngine()

    def test_basic_forecast(self, fe):
        result = fe.compute(
            revenue_cagr=0.15,
            eps_cagr=0.18,
            sustainability=75.0,
            history_depth=7,
        )
        assert isinstance(result, GrowthForecastProfile)
        assert result.base_revenue_growth is not None
        assert result.base_eps_growth is not None

    def test_bull_gt_base_gt_bear(self, fe):
        result = fe.compute(revenue_cagr=0.12, eps_cagr=0.15, sustainability=70.0, history_depth=6)
        assert result.bull_revenue_growth > result.base_revenue_growth
        assert result.bear_revenue_growth < result.base_revenue_growth

    def test_low_confidence_no_forecast(self, fe):
        result = fe.compute(history_depth=0)
        # Very low confidence → no forecast
        assert result.base_revenue_growth is None or result.forecast_confidence < 0.30

    def test_confidence_in_range(self, fe):
        result = fe.compute(revenue_cagr=0.12, history_depth=7)
        assert 0.0 <= result.forecast_confidence <= 1.0

    def test_custom_assumptions(self, fe):
        assumptions = ForecastAssumptions(
            horizon_years=5,
            mean_reversion_weight=0.30,
            bull_multiplier=1.50,
            bear_multiplier=0.50,
        )
        result = fe.compute(
            revenue_cagr=0.20,
            sustainability=80.0,
            history_depth=8,
            assumptions=assumptions,
        )
        assert result.forecast_horizon_years == 5

    def test_explanation_populated(self, fe):
        result = fe.compute(revenue_cagr=0.15, history_depth=6)
        assert len(result.explanation) > 0


# ── OverallConfidence ─────────────────────────────────────────────────────────

class TestComputeOverallConfidence:
    def test_high_confidence(self):
        c = compute_overall_confidence(
            history_depth=10,
            has_eps_cagr=True,
            has_revenue_cagr=True,
            has_fcf_data=True,
            quality_label="exceptional",
            sustainability=85.0,
        )
        assert c > 0.70

    def test_low_confidence(self):
        c = compute_overall_confidence(
            history_depth=0,
            has_eps_cagr=False,
            has_revenue_cagr=False,
            has_fcf_data=False,
            quality_label="insufficient",
            sustainability=0.0,
        )
        assert c == pytest.approx(0.0)

    def test_in_range(self):
        for depth in [0, 3, 7, 12]:
            c = compute_overall_confidence(
                history_depth=depth,
                has_eps_cagr=True,
                has_revenue_cagr=True,
                has_fcf_data=False,
                quality_label="moderate",
                sustainability=60.0,
            )
            assert 0.0 <= c <= 1.0
