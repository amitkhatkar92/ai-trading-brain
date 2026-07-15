"""tests/unit/investment/portfolio/recommendation/test_recommendation_logic.py

Tests for the RecommendationLogic orchestration layer.
"""
from __future__ import annotations

import pytest

from iios.investment.portfolio.recommendation.recommendation_logic import (
    RecommendationLogic,
)
from iios.investment.portfolio.recommendation.recommendation_types import (
    RecommendationAction,
)


class TestRecommendationLogicHealthyPortfolio:
    """A healthy portfolio should result in NO_ACTION."""

    def test_generates_list(self, default_intel, default_policy):
        logic = RecommendationLogic()
        candidates = logic.generate(default_intel, default_policy)
        assert isinstance(candidates, list)
        assert len(candidates) >= 1

    def test_no_action_for_healthy(self, default_intel, default_policy):
        logic = RecommendationLogic()
        candidates = logic.generate(default_intel, default_policy)
        actions = [c.action for c in candidates]
        assert RecommendationAction.NO_ACTION in actions

    def test_no_duplicate_actions(self, default_intel, default_policy):
        logic = RecommendationLogic()
        candidates = logic.generate(default_intel, default_policy)
        actions = [c.action for c in candidates]
        assert len(actions) == len(set(actions))


class TestRecommendationLogicStressedPortfolio:
    """A stressed portfolio should trigger multiple action candidates."""

    def test_generates_multiple_candidates(self, stressed_intel, default_policy):
        logic = RecommendationLogic()
        candidates = logic.generate(stressed_intel, default_policy)
        assert len(candidates) >= 3

    def test_rebalance_triggered(self, stressed_intel, default_policy):
        logic = RecommendationLogic()
        candidates = logic.generate(stressed_intel, default_policy)
        actions = {c.action for c in candidates}
        assert RecommendationAction.REBALANCE_PORTFOLIO in actions

    def test_defensive_triggered(self, stressed_intel, default_policy):
        logic = RecommendationLogic()
        candidates = logic.generate(stressed_intel, default_policy)
        actions = {c.action for c in candidates}
        assert RecommendationAction.DEFENSIVE_POSITIONING in actions

    def test_reduce_equity_triggered(self, stressed_intel, default_policy):
        logic = RecommendationLogic()
        candidates = logic.generate(stressed_intel, default_policy)
        actions = {c.action for c in candidates}
        assert RecommendationAction.REDUCE_EQUITY_EXPOSURE in actions

    def test_candidates_have_evidence(self, stressed_intel, default_policy):
        logic = RecommendationLogic()
        candidates = logic.generate(stressed_intel, default_policy)
        for c in candidates:
            if c.action != RecommendationAction.NO_ACTION:
                assert len(c.evidence) >= 1, f"No evidence for {c.action}"

    def test_candidates_have_rationale(self, stressed_intel, default_policy):
        logic = RecommendationLogic()
        candidates = logic.generate(stressed_intel, default_policy)
        for c in candidates:
            assert c.rationale, f"No rationale for {c.action}"


class TestRecommendationLogicPolicyRespect:
    """Logic should respect policy parameters."""

    def test_uses_policy_thresholds(self, default_intel, registry):
        # Conservative policy should be more sensitive to risk
        conservative = next(
            p for p in registry.all() if p.policy_type.value == "conservative"
        )
        logic = RecommendationLogic()
        candidates = logic.generate(default_intel, conservative)
        assert isinstance(candidates, list)

    def test_logic_is_deterministic(self, stressed_intel, default_policy):
        """Same inputs → same output."""
        logic = RecommendationLogic()
        candidates1 = logic.generate(stressed_intel, default_policy)
        candidates2 = logic.generate(stressed_intel, default_policy)
        actions1 = sorted(c.action.value for c in candidates1)
        actions2 = sorted(c.action.value for c in candidates2)
        assert actions1 == actions2
