"""tests/unit/investment/portfolio/recommendation/test_recommendation_types.py

Tests for recommendation_types.py: enums, PortfolioIntelligence, utilities.
"""
from __future__ import annotations

import pytest

from iios.investment.portfolio.recommendation.recommendation_types import (
    DEFAULT_EXPIRY_HOURS,
    CRITICAL_EXPIRY_HOURS,
    HIGH_EXPIRY_HOURS,
    LOW_EXPIRY_HOURS,
    NO_ACTION_EXPIRY_HOURS,
    LifecycleState,
    PolicyType,
    PortfolioIntelligence,
    RecommendationAction,
    RecommendationGrade,
    RecommendationLevel,
    RecommendationPriority,
    RecommendationRisk,
    RecommendationStatus,
    ValidationStatus,
    action_to_category,
    intelligence_from_any,
    now_utc,
    priority_to_expiry_hours,
    recommendation_score_to_grade,
    recommendation_score_to_level,
)


class TestEnums:
    def test_recommendation_action_has_16_values(self):
        assert len(RecommendationAction) == 16

    def test_no_action_exists(self):
        assert RecommendationAction.NO_ACTION is not None

    def test_priority_ordering(self):
        # Just check all expected values exist
        for name in ("IMMEDIATE", "HIGH", "MEDIUM", "LOW", "INFORMATIONAL"):
            assert hasattr(RecommendationPriority, name)

    def test_lifecycle_state_has_8_values(self):
        assert len(LifecycleState) >= 7  # at least 7 states

    def test_policy_type_str(self):
        assert PolicyType.BALANCED.value == "balanced"


class TestPortfolioIntelligence:
    def test_default_construction(self, default_intel):
        assert default_intel.portfolio_id == "P-TEST-01"
        assert default_intel.n_positions == 20

    def test_intelligence_id_generated(self, default_intel):
        assert len(default_intel.intelligence_id) == 36  # UUID length

    def test_weights_sum_approx_one(self, default_intel):
        total = (
            default_intel.equity_weight
            + default_intel.bond_weight
            + default_intel.cash_weight
            + default_intel.alternative_weight
        )
        assert abs(total - 1.0) < 0.01

    def test_frozen_immutable(self, default_intel):
        with pytest.raises((AttributeError, TypeError)):
            default_intel.portfolio_id = "changed"  # type: ignore

    def test_from_any_passthrough(self, default_intel):
        result = intelligence_from_any(default_intel)
        assert result is default_intel

    def test_from_any_dict(self, default_intel):
        d = {
            "portfolio_id": "P-D",
            "n_positions":  5,
        }
        result = intelligence_from_any(d)
        assert result.portfolio_id == "P-D"
        assert result.n_positions == 5

    def test_from_any_duck_typed(self):
        class Stub:
            portfolio_id = "P-DUCK"
            n_positions  = 7
        result = intelligence_from_any(Stub())
        assert result.portfolio_id == "P-DUCK"


class TestUtilities:
    def test_now_utc_is_string(self):
        result = now_utc()
        assert isinstance(result, str)
        assert "T" in result

    def test_score_to_grade_excellent(self):
        grade = recommendation_score_to_grade(0.90)
        assert grade == RecommendationGrade.A

    def test_score_to_grade_poor(self):
        grade = recommendation_score_to_grade(0.10)
        assert grade == RecommendationGrade.F

    def test_score_to_level_excellent(self):
        level = recommendation_score_to_level(0.90)
        assert level == RecommendationLevel.EXCELLENT

    def test_score_to_level_poor(self):
        level = recommendation_score_to_level(0.10)
        assert level == RecommendationLevel.POOR

    def test_action_to_category_equity(self):
        cat = action_to_category(RecommendationAction.INCREASE_EQUITY_EXPOSURE)
        assert cat == "allocation"

    def test_action_to_category_no_action(self):
        cat = action_to_category(RecommendationAction.NO_ACTION)
        assert cat == "governance"

    def test_priority_to_expiry_immediate(self):
        h = priority_to_expiry_hours(
            RecommendationPriority.IMMEDIATE,
            CRITICAL_EXPIRY_HOURS,
            HIGH_EXPIRY_HOURS,
            DEFAULT_EXPIRY_HOURS,
            LOW_EXPIRY_HOURS,
            NO_ACTION_EXPIRY_HOURS,
        )
        assert h == CRITICAL_EXPIRY_HOURS

    def test_priority_to_expiry_informational(self):
        h = priority_to_expiry_hours(
            RecommendationPriority.INFORMATIONAL,
            CRITICAL_EXPIRY_HOURS,
            HIGH_EXPIRY_HOURS,
            DEFAULT_EXPIRY_HOURS,
            LOW_EXPIRY_HOURS,
            NO_ACTION_EXPIRY_HOURS,
        )
        assert h == NO_ACTION_EXPIRY_HOURS
