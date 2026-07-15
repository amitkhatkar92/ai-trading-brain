"""tests/unit/investment/portfolio/recommendation/test_portfolio_recommendation.py

Tests for PortfolioRecommendation dataclass, RecommendationCandidate, build_recommendation.
"""
from __future__ import annotations

import pytest

from iios.investment.portfolio.recommendation.portfolio_recommendation import (
    PortfolioRecommendation,
    RecommendationCandidate,
    build_recommendation,
)
from iios.investment.portfolio.recommendation.recommendation_score import (
    RecommendationScoreCalculator,
)
from iios.investment.portfolio.recommendation.recommendation_types import (
    LifecycleState,
    RecommendationAction,
    RecommendationGrade,
    RecommendationLevel,
    RecommendationPriority,
    RecommendationRisk,
    RecommendationStatus,
    now_utc,
)


def _make_candidate(**kwargs) -> RecommendationCandidate:
    defaults = dict(
        action         = RecommendationAction.REBALANCE_PORTFOLIO,
        priority       = RecommendationPriority.HIGH,
        confidence     = 0.75,
        rationale      = "Drift exceeds threshold.",
        evidence       = ("drift 8%", "policy breach"),
        triggered_rule = "rebalance_trigger",
        risk_level     = RecommendationRisk.MEDIUM,
        tags           = ("rebalancing",),
    )
    defaults.update(kwargs)
    return RecommendationCandidate(**defaults)


def _make_rec(**kwargs) -> PortfolioRecommendation:
    candidate = kwargs.pop("candidate", _make_candidate())
    defaults = dict(
        portfolio_id      = "P-TEST",
        policy_id         = "pid-001",
        policy_name       = "balanced",
        intelligence_id   = "iid-001",
        score             = 0.70,
        expires_at        = None,
        expiry_hours      = 24.0,
        requires_approval = False,
        is_time_sensitive = True,
    )
    defaults.update(kwargs)
    return build_recommendation(candidate, **defaults)


class TestRecommendationCandidate:
    def test_basic_construction(self):
        c = _make_candidate()
        assert c.action == RecommendationAction.REBALANCE_PORTFOLIO
        assert c.confidence == 0.75

    def test_frozen(self):
        c = _make_candidate()
        with pytest.raises((AttributeError, TypeError)):
            c.confidence = 0.9  # type: ignore

    def test_evidence_is_tuple(self):
        c = _make_candidate(evidence=("a", "b"))
        assert isinstance(c.evidence, tuple)


class TestBuildRecommendation:
    def test_creates_recommendation(self):
        rec = _make_rec()
        assert isinstance(rec, PortfolioRecommendation)

    def test_id_is_uuid(self):
        rec = _make_rec()
        assert len(rec.recommendation_id) == 36

    def test_action_propagated(self):
        rec = _make_rec()
        assert rec.action == RecommendationAction.REBALANCE_PORTFOLIO

    def test_initial_state_is_created(self):
        rec = _make_rec()
        assert rec.lifecycle_state == LifecycleState.CREATED

    def test_grade_assigned(self):
        rec = _make_rec(score=0.85)
        assert rec.grade == RecommendationGrade.A

    def test_level_assigned(self):
        rec = _make_rec(score=0.85)
        assert rec.level == RecommendationLevel.EXCELLENT

    def test_is_not_active_when_created(self):
        rec = _make_rec()
        assert rec.status != RecommendationStatus.ACTIVE

    def test_evidence_is_tuple(self):
        rec = _make_rec()
        assert isinstance(rec.supporting_evidence, tuple)

    def test_to_dict_keys(self):
        rec = _make_rec()
        d = rec.to_dict()
        assert "recommendation_id" in d
        assert "action" in d
        assert "confidence" in d

    def test_is_active_property(self):
        # Not yet ACTIVE after build
        rec = _make_rec()
        assert not rec.is_active   # starts as CREATED

    def test_is_terminal_property(self):
        rec = _make_rec()
        assert not rec.is_terminal


class TestPortfolioRecommendationScore:
    def test_score_bounds(self):
        for s in [0.0, 0.5, 1.0]:
            rec = _make_rec(score=s)
            assert 0.0 <= rec.recommendation_score <= 1.0

    def test_score_drives_grade(self):
        low_rec  = _make_rec(score=0.10)
        high_rec = _make_rec(score=0.90)
        assert low_rec.grade == RecommendationGrade.F
        assert high_rec.grade == RecommendationGrade.A
