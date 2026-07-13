"""tests/unit/investment/company/opportunity/test_classification.py
Tests for classification engine, classifier, and lifecycle.
"""
from __future__ import annotations

import pytest

from iios.investment.company.opportunity.classification_engine import ClassificationEngine
from iios.investment.company.opportunity.company_classifier import classify_company
from iios.investment.company.opportunity.opportunity_category import ClassificationResult
from iios.investment.company.opportunity.opportunity_lifecycle import (
    LifecycleChange, determine_lifecycle, is_valid_transition,
)
from iios.investment.company.opportunity.opportunity_profile import (
    OpportunityCategory, OpportunityLifecycle,
)


class TestClassifyCompany:
    def _call(self, **kwargs):
        defaults = dict(
            bq_score=60.0, val_score=55.0, grw_score=60.0, mgmt_score=60.0,
            fin_score=60.0, ear_score=60.0, own_score=60.0, moat_score=55.0,
            overall_score=60.0,
        )
        defaults.update(kwargs)
        return classify_company(**defaults)

    def test_returns_tuple(self):
        primary, secondary, rationale = self._call()
        assert isinstance(primary, OpportunityCategory)
        assert isinstance(secondary, list)
        assert isinstance(rationale, list)

    def test_wide_moat(self):
        primary, _, _ = self._call(moat_score=80.0, bq_score=75.0, fin_score=65.0, overall_score=75.0)
        assert primary == OpportunityCategory.WIDE_MOAT

    def test_compounder(self):
        primary, _, _ = self._call(
            bq_score=70.0, fin_score=65.0, overall_score=70.0,
            avg_roic=0.20, eps_cagr=0.15, moat_score=60.0,
        )
        assert primary == OpportunityCategory.COMPOUNDER

    def test_high_growth(self):
        primary, _, _ = self._call(
            grw_score=70.0, overall_score=66.0, eps_cagr=0.22,
        )
        assert primary == OpportunityCategory.HIGH_GROWTH

    def test_income(self):
        primary, _, _ = self._call(
            overall_score=55.0, fin_score=55.0,
            dividend_yield=0.04, payout_ratio=0.60,
        )
        assert primary == OpportunityCategory.INCOME

    def test_observation_only(self):
        primary, _, rationale = self._call(overall_score=25.0)
        assert primary == OpportunityCategory.OBSERVATION_ONLY
        assert len(rationale) > 0

    def test_watchlist(self):
        primary, _, _ = self._call(overall_score=42.0)
        assert primary == OpportunityCategory.WATCHLIST

    def test_undervalued_quality(self):
        primary, _, _ = self._call(
            bq_score=65.0, ear_score=60.0, is_undervalued=True, overall_score=62.0,
        )
        assert primary == OpportunityCategory.UNDERVALUED_QUALITY

    def test_cyclical_recovery(self):
        primary, _, _ = self._call(
            is_cyclical=True, grw_score=58.0, ear_score=52.0, overall_score=55.0,
        )
        assert primary == OpportunityCategory.CYCLICAL_RECOVERY

    def test_secondary_includes_wide_moat(self):
        _, secondary, _ = self._call(
            moat_score=72.0, bq_score=60.0, grw_score=70.0,
            eps_cagr=0.22, overall_score=66.0,
        )
        # Primary is HIGH_GROWTH; secondary should include WIDE_MOAT
        assert OpportunityCategory.WIDE_MOAT in secondary


class TestClassificationEngine:
    @pytest.fixture
    def engine(self):
        return ClassificationEngine()

    def test_returns_result(self, engine):
        result = engine.classify(
            overall_score=65.0,
            bq_score=65.0, val_score=55.0, grw_score=65.0,
            mgmt_score=65.0, fin_score=65.0, ear_score=65.0, own_score=65.0,
        )
        assert isinstance(result, ClassificationResult)

    def test_confidence_range(self, engine):
        result = engine.classify(
            overall_score=70.0,
            bq_score=70.0, val_score=55.0, grw_score=70.0,
            mgmt_score=70.0, fin_score=70.0, ear_score=70.0, own_score=70.0,
        )
        assert 0.0 <= result.confidence <= 1.0

    def test_classify_with_snapshots(self, engine, mock_earnings, mock_bq, mock_valuation, mock_growth):
        result = engine.classify(
            overall_score=68.0,
            bq_score=72.0, val_score=65.0, grw_score=72.0,
            mgmt_score=70.0, fin_score=70.0, ear_score=78.0, own_score=68.0,
            earnings_snapshot=mock_earnings,
            business_quality=mock_bq,
            valuation_snapshot=mock_valuation,
            growth_snapshot=mock_growth,
        )
        assert result.is_actionable

    def test_low_score_not_actionable(self, engine):
        result = engine.classify(
            overall_score=25.0,
            bq_score=25.0, val_score=25.0, grw_score=25.0,
            mgmt_score=25.0, fin_score=25.0, ear_score=25.0, own_score=25.0,
        )
        assert not result.is_actionable


class TestLifecycle:
    def test_initial_discovered(self):
        state = determine_lifecycle(
            score=45.0, confidence=0.40,
            current=OpportunityLifecycle.DISCOVERED,
            evaluation_count=1, score_trend=0.0,
        )
        assert state == OpportunityLifecycle.DISCOVERED

    def test_high_conviction(self):
        state = determine_lifecycle(
            score=72.0, confidence=0.70,
            current=OpportunityLifecycle.MONITORING,
            evaluation_count=3, score_trend=5.0,
        )
        assert state == OpportunityLifecycle.HIGH_CONVICTION

    def test_confirmed(self):
        state = determine_lifecycle(
            score=72.0, confidence=0.72,
            current=OpportunityLifecycle.HIGH_CONVICTION,
            evaluation_count=5, score_trend=1.0,
        )
        assert state == OpportunityLifecycle.CONFIRMED

    def test_expired_low_score(self):
        state = determine_lifecycle(
            score=20.0, confidence=0.30,
            current=OpportunityLifecycle.MONITORING,
            evaluation_count=4, score_trend=-8.0,
        )
        assert state == OpportunityLifecycle.EXPIRED

    def test_weakening_from_high(self):
        state = determine_lifecycle(
            score=58.0, confidence=0.55,
            current=OpportunityLifecycle.HIGH_CONVICTION,
            evaluation_count=6, score_trend=-8.0,
        )
        assert state == OpportunityLifecycle.WEAKENING

    def test_archived_terminal(self):
        state = determine_lifecycle(
            score=80.0, confidence=0.90,
            current=OpportunityLifecycle.ARCHIVED,
            evaluation_count=10, score_trend=5.0,
        )
        assert state == OpportunityLifecycle.ARCHIVED

    def test_valid_transitions(self):
        assert is_valid_transition(OpportunityLifecycle.DISCOVERED, OpportunityLifecycle.EMERGING)
        assert is_valid_transition(OpportunityLifecycle.HIGH_CONVICTION, OpportunityLifecycle.CONFIRMED)
        assert not is_valid_transition(OpportunityLifecycle.ARCHIVED, OpportunityLifecycle.CONFIRMED)

    def test_lifecycle_change_to_dict(self):
        from datetime import datetime, timezone
        lc = LifecycleChange(
            from_state=OpportunityLifecycle.MONITORING,
            to_state=OpportunityLifecycle.HIGH_CONVICTION,
            score_at_change=68.0,
            changed_at=datetime.now(timezone.utc),
        )
        d = lc.to_dict()
        assert d["from_state"] == "monitoring"
        assert d["to_state"] == "high_conviction"
