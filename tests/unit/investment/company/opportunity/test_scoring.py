"""tests/unit/investment/company/opportunity/test_scoring.py
Tests for opportunity scoring: quality extraction and composite score computation.
"""
from __future__ import annotations

import pytest

from iios.investment.company.opportunity.opportunity_quality import (
    extract_business_quality,
    extract_earnings_quality,
    extract_financial_strength,
    extract_growth_quality,
    extract_management_quality,
    extract_ownership_quality,
    extract_risk_penalty,
    extract_valuation_attractiveness,
)
from iios.investment.company.opportunity.opportunity_score import (
    compute_opportunity_score,
)
from iios.investment.company.opportunity.opportunity_confidence import (
    compute_opportunity_confidence,
    explain_confidence,
)


class TestExtractFinancialStrength:
    def test_good_financial(self, mock_financial):
        s = extract_financial_strength(mock_financial)
        assert s > 55.0

    def test_weak_financial(self, weak_financial):
        s = extract_financial_strength(weak_financial)
        assert s < 50.0

    def test_none_returns_default(self):
        s = extract_financial_strength(None)
        assert s == 50.0

    def test_range(self, mock_financial):
        assert 0.0 <= extract_financial_strength(mock_financial) <= 100.0


class TestExtractEarningsQuality:
    def test_good_earnings(self, mock_earnings):
        s = extract_earnings_quality(mock_earnings)
        assert s == pytest.approx(78.0)

    def test_weak_earnings(self, weak_earnings):
        s = extract_earnings_quality(weak_earnings)
        assert s < 40.0

    def test_none(self):
        assert extract_earnings_quality(None) == 50.0


class TestExtractBusinessQuality:
    def test_good_bq(self, mock_bq):
        s = extract_business_quality(mock_bq)
        assert s >= 70.0

    def test_weak_bq(self, weak_bq):
        s = extract_business_quality(weak_bq)
        assert s < 35.0

    def test_none(self):
        assert extract_business_quality(None) == 50.0


class TestExtractValuationAttractiveness:
    def test_undervalued(self, mock_valuation):
        s = extract_valuation_attractiveness(mock_valuation)
        assert s >= 55.0

    def test_overvalued(self, overvalued_valuation):
        s = extract_valuation_attractiveness(overvalued_valuation)
        assert s <= 35.0

    def test_none(self):
        assert extract_valuation_attractiveness(None) == 50.0


class TestExtractGrowthQuality:
    def test_good_growth(self, mock_growth):
        s = extract_growth_quality(mock_growth)
        assert s == pytest.approx(72.0)

    def test_weak_growth(self, weak_growth):
        s = extract_growth_quality(weak_growth)
        assert s < 30.0

    def test_none(self):
        assert extract_growth_quality(None) == 50.0


class TestExtractManagementQuality:
    def test_from_snapshot(self, mock_management):
        s = extract_management_quality(mock_management)
        assert s == pytest.approx(70.0)

    def test_none(self):
        assert extract_management_quality(None) == 50.0


class TestExtractOwnershipQuality:
    def test_from_snapshot(self, mock_ownership):
        s = extract_ownership_quality(mock_ownership)
        assert s == pytest.approx(68.0)

    def test_none(self):
        assert extract_ownership_quality(None) == 50.0


class TestExtractRiskPenalty:
    def test_no_snapshots(self):
        assert extract_risk_penalty(None, None) == 0.0

    def test_high_risk(self):
        from unittest.mock import MagicMock
        risk = MagicMock()
        risk.overall_risk_score = 80.0
        penalty = extract_risk_penalty(risk, None)
        assert penalty > 5.0

    def test_penalty_bounded(self):
        from unittest.mock import MagicMock
        risk = MagicMock()
        risk.overall_risk_score = 100.0
        market = MagicMock()
        market.market_stress_score = 100.0
        penalty = extract_risk_penalty(risk, market, max_penalty=20.0)
        assert penalty <= 20.0


class TestComputeOpportunityScore:
    def test_returns_breakdown(self, mock_financial, mock_earnings, mock_bq):
        bd = compute_opportunity_score(mock_financial, mock_earnings, mock_bq)
        assert bd is not None
        assert 0.0 <= bd.final_score <= 100.0

    def test_all_snapshots_higher(
        self, mock_financial, mock_earnings, mock_bq,
        mock_valuation, mock_growth, mock_management, mock_ownership,
    ):
        bd_partial = compute_opportunity_score(mock_financial, mock_earnings, mock_bq)
        bd_full = compute_opportunity_score(
            mock_financial, mock_earnings, mock_bq,
            valuation_snapshot=mock_valuation,
            growth_snapshot=mock_growth,
            management_snapshot=mock_management,
            ownership_snapshot=mock_ownership,
        )
        assert isinstance(bd_full.final_score, float)
        assert 0.0 <= bd_full.final_score <= 100.0

    def test_good_vs_weak(
        self, mock_financial, mock_earnings, mock_bq,
        weak_financial, weak_earnings, weak_bq,
    ):
        bd_good = compute_opportunity_score(mock_financial, mock_earnings, mock_bq)
        bd_weak = compute_opportunity_score(weak_financial, weak_earnings, weak_bq)
        assert bd_good.final_score > bd_weak.final_score

    def test_seven_components(self, mock_financial, mock_earnings, mock_bq):
        bd = compute_opportunity_score(mock_financial, mock_earnings, mock_bq)
        assert len(bd.components()) == 7


class TestOpportunityConfidence:
    def test_full_coverage_higher(
        self, mock_financial, mock_earnings, mock_bq,
        mock_valuation, mock_growth, mock_management, mock_ownership,
    ):
        full = compute_opportunity_confidence(
            mock_financial, mock_earnings, mock_bq,
            mock_valuation, mock_growth, mock_management, mock_ownership,
        )
        partial = compute_opportunity_confidence(
            mock_financial, mock_earnings, mock_bq,
        )
        assert full > partial

    def test_range(self, mock_financial, mock_earnings, mock_bq):
        c = compute_opportunity_confidence(mock_financial, mock_earnings, mock_bq)
        assert 0.0 <= c <= 1.0

    def test_consistency_boost(self, mock_financial, mock_earnings, mock_bq):
        stable_history = [65.0, 66.0, 65.0, 67.0]
        volatile_history = [40.0, 80.0, 30.0, 70.0]
        c_stable = compute_opportunity_confidence(
            mock_financial, mock_earnings, mock_bq, score_history=stable_history
        )
        c_volatile = compute_opportunity_confidence(
            mock_financial, mock_earnings, mock_bq, score_history=volatile_history
        )
        assert c_stable >= c_volatile

    def test_explain_confidence_returns_str(self):
        s = explain_confidence(True, True, True, False, False, False, False, 0.65)
        assert isinstance(s, str) and len(s) > 5
