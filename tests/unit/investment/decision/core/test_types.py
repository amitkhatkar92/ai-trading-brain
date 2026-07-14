"""tests/unit/investment/decision/core/test_types.py
Tests for enumerations, type/recommendation/action descriptors.
"""
from __future__ import annotations

import pytest

from iios.investment.decision.core.decision_constants import (
    VALID_TRANSITIONS,
    ActionType,
    ApprovalStatus,
    ConfidenceLevel,
    DecisionEventType,
    DecisionFrameworkStatus,
    DecisionPriority,
    DecisionStatus,
    DecisionType,
    EnvironmentProfile,
    RecommendationType,
    RiskReviewStatus,
)
from iios.investment.decision.core.action_types import (
    ACTION_DESCRIPTORS,
    get_action_descriptor,
)
from iios.investment.decision.core.decision_types import (
    DECISION_TYPE_DESCRIPTORS,
    get_descriptor,
)
from iios.investment.decision.core.recommendation_types import (
    RECOMMENDATION_DESCRIPTORS,
    get_recommendation_descriptor,
)


# ===========================================================================
# DecisionStatus
# ===========================================================================

class TestDecisionStatus:
    def test_all_values_accessible(self):
        for status in DecisionStatus:
            assert isinstance(status.value, str)

    def test_terminal_statuses(self):
        assert DecisionStatus.ARCHIVED.is_terminal
        assert DecisionStatus.EXPIRED.is_terminal
        assert not DecisionStatus.CREATED.is_terminal

    def test_active_statuses(self):
        assert DecisionStatus.CREATED.is_active
        assert DecisionStatus.COLLECTING_EVIDENCE.is_active
        assert DecisionStatus.UNDER_REVIEW.is_active
        assert DecisionStatus.SCORED.is_active
        assert DecisionStatus.RISK_REVIEWED.is_active
        assert not DecisionStatus.PUBLISHED.is_active

    def test_final_statuses(self):
        assert DecisionStatus.APPROVED.is_final
        assert DecisionStatus.REJECTED.is_final
        assert DecisionStatus.PUBLISHED.is_final
        assert DecisionStatus.FAILED.is_final
        assert not DecisionStatus.CREATED.is_final


# ===========================================================================
# VALID_TRANSITIONS state machine
# ===========================================================================

class TestValidTransitions:
    def test_created_can_go_to_collecting(self):
        assert DecisionStatus.COLLECTING_EVIDENCE in VALID_TRANSITIONS[DecisionStatus.CREATED]

    def test_created_can_fail(self):
        assert DecisionStatus.FAILED in VALID_TRANSITIONS[DecisionStatus.CREATED]

    def test_archived_is_terminal(self):
        assert VALID_TRANSITIONS[DecisionStatus.ARCHIVED] == set()

    def test_approved_leads_to_published(self):
        assert DecisionStatus.PUBLISHED in VALID_TRANSITIONS[DecisionStatus.APPROVED]

    def test_risk_reviewed_can_approve_or_reject(self):
        transitions = VALID_TRANSITIONS[DecisionStatus.RISK_REVIEWED]
        assert DecisionStatus.APPROVED in transitions
        assert DecisionStatus.REJECTED in transitions

    def test_all_statuses_have_entry(self):
        for status in DecisionStatus:
            assert status in VALID_TRANSITIONS


# ===========================================================================
# RecommendationType
# ===========================================================================

class TestRecommendationType:
    def test_bullish_types(self):
        assert RecommendationType.STRONG_BUY.is_bullish
        assert RecommendationType.BUY.is_bullish
        assert RecommendationType.ACCUMULATE.is_bullish
        assert not RecommendationType.SELL.is_bullish

    def test_bearish_types(self):
        assert RecommendationType.SELL.is_bearish
        assert RecommendationType.STRONG_SELL.is_bearish
        assert RecommendationType.REDUCE.is_bearish
        assert not RecommendationType.BUY.is_bearish

    def test_neutral_types(self):
        assert RecommendationType.HOLD.is_neutral
        assert RecommendationType.WATCHLIST.is_neutral
        assert not RecommendationType.SELL.is_neutral

    def test_direction_score(self):
        assert RecommendationType.STRONG_BUY.direction_score == 2
        assert RecommendationType.HOLD.direction_score == 0
        assert RecommendationType.STRONG_SELL.direction_score == -2


# ===========================================================================
# ConfidenceLevel
# ===========================================================================

class TestConfidenceLevel:
    def test_from_score_very_high(self):
        assert ConfidenceLevel.from_score(90.0) == ConfidenceLevel.VERY_HIGH

    def test_from_score_high(self):
        assert ConfidenceLevel.from_score(75.0) == ConfidenceLevel.HIGH

    def test_from_score_medium(self):
        assert ConfidenceLevel.from_score(55.0) == ConfidenceLevel.MEDIUM

    def test_from_score_low(self):
        assert ConfidenceLevel.from_score(35.0) == ConfidenceLevel.LOW

    def test_from_score_very_low(self):
        assert ConfidenceLevel.from_score(10.0) == ConfidenceLevel.VERY_LOW


# ===========================================================================
# EnvironmentProfile
# ===========================================================================

class TestEnvironmentProfile:
    def test_live_is_production(self):
        assert EnvironmentProfile.LIVE.is_production
        assert not EnvironmentProfile.PAPER.is_production

    def test_requires_approval(self):
        assert EnvironmentProfile.PAPER.requires_approval
        assert EnvironmentProfile.LIVE.requires_approval
        assert not EnvironmentProfile.DEVELOPMENT.requires_approval
        assert not EnvironmentProfile.BACKTEST.requires_approval


# ===========================================================================
# DecisionPriority
# ===========================================================================

class TestDecisionPriority:
    def test_sort_keys_ordered(self):
        priorities = [
            DecisionPriority.LOW,
            DecisionPriority.NORMAL,
            DecisionPriority.HIGH,
            DecisionPriority.URGENT,
            DecisionPriority.CRITICAL,
        ]
        keys = [p.sort_key for p in priorities]
        assert keys == sorted(keys)


# ===========================================================================
# ApprovalStatus / RiskReviewStatus
# ===========================================================================

class TestApprovalStatus:
    def test_positive_statuses(self):
        assert ApprovalStatus.APPROVED.is_positive
        assert ApprovalStatus.OVERRIDE.is_positive
        assert not ApprovalStatus.REJECTED.is_positive
        assert not ApprovalStatus.PENDING.is_positive

class TestRiskReviewStatus:
    def test_allows_approval(self):
        assert RiskReviewStatus.APPROVED.allows_approval
        assert RiskReviewStatus.CONDITIONAL.allows_approval
        assert not RiskReviewStatus.REJECTED.allows_approval
        assert not RiskReviewStatus.PENDING.allows_approval


# ===========================================================================
# DecisionFrameworkStatus
# ===========================================================================

class TestDecisionFrameworkStatus:
    def test_operational(self):
        assert DecisionFrameworkStatus.READY.is_operational
        assert DecisionFrameworkStatus.BUSY.is_operational
        assert not DecisionFrameworkStatus.STOPPED.is_operational
        assert not DecisionFrameworkStatus.INITIALIZING.is_operational


# ===========================================================================
# DecisionTypeDescriptor
# ===========================================================================

class TestDecisionTypeDescriptor:
    def test_all_builtin_types_have_descriptor(self):
        for dt in DecisionType:
            desc = DECISION_TYPE_DESCRIPTORS.get(dt)
            assert desc is not None, f"Missing descriptor for {dt}"

    def test_to_dict_contains_keys(self):
        desc = get_descriptor(DecisionType.INVESTMENT)
        d = desc.to_dict()
        assert "decision_type" in d
        assert "allowed_recommendations" in d
        assert "capabilities" in d

    def test_investment_requires_evidence(self):
        desc = get_descriptor(DecisionType.INVESTMENT)
        assert desc.requires_evidence
        assert desc.requires_risk_review
        assert desc.requires_approval

    def test_risk_action_no_evidence_required(self):
        desc = get_descriptor(DecisionType.RISK_ACTION)
        assert not desc.requires_evidence
        assert not desc.requires_approval


# ===========================================================================
# RecommendationDescriptor
# ===========================================================================

class TestRecommendationDescriptor:
    def test_all_recommendation_types_have_descriptor(self):
        for rec in RecommendationType:
            assert rec in RECOMMENDATION_DESCRIPTORS

    def test_strong_buy_highest_strength(self):
        desc = get_recommendation_descriptor(RecommendationType.STRONG_BUY)
        assert desc.strength == 3
        assert desc.direction == "bullish"

    def test_to_dict(self):
        desc = get_recommendation_descriptor(RecommendationType.HOLD)
        d = desc.to_dict()
        assert "recommendation" in d
        assert "direction" in d
        assert "minimum_score" in d


# ===========================================================================
# ActionDescriptor
# ===========================================================================

class TestActionDescriptor:
    def test_all_action_types_have_descriptor(self):
        for at in ActionType:
            assert at in ACTION_DESCRIPTORS

    def test_exit_is_irreversible(self):
        desc = get_action_descriptor(ActionType.EXIT)
        assert not desc.is_reversible
        assert desc.requires_execution

    def test_monitor_no_execution(self):
        desc = get_action_descriptor(ActionType.MONITOR)
        assert not desc.requires_execution

    def test_to_dict(self):
        desc = get_action_descriptor(ActionType.BUY_ORDER)
        d = desc.to_dict()
        assert "action_type" in d
        assert "urgency" in d
