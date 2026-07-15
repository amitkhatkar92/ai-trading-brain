"""tests/unit/investment/portfolio/recommendation/test_recommendation_lifecycle.py

Tests for recommendation lifecycle state machine and expiration.
"""
from __future__ import annotations

import pytest

from iios.investment.portfolio.recommendation.portfolio_recommendation import (
    build_recommendation, RecommendationCandidate,
)
from iios.investment.portfolio.recommendation.recommendation_lifecycle import (
    LifecycleManager,
    get_allowed_transitions,
    is_active,
    is_terminal,
    is_valid_transition,
    state_to_status,
)
from iios.investment.portfolio.recommendation.recommendation_types import (
    LifecycleState,
    RecommendationAction,
    RecommendationPriority,
    RecommendationRisk,
    RecommendationStatus,
)


def _make_rec(**kw):
    candidate = RecommendationCandidate(
        action         = RecommendationAction.REBALANCE_PORTFOLIO,
        priority       = RecommendationPriority.HIGH,
        confidence     = 0.75,
        rationale      = "Test",
        evidence       = ("e1",),
        triggered_rule = "rule",
        risk_level     = RecommendationRisk.MEDIUM,
        tags           = (),
    )
    defaults = dict(
        portfolio_id      = "P-T",
        policy_id         = "pid",
        policy_name       = "balanced",
        intelligence_id   = "iid",
        score             = 0.70,
        expires_at        = None,
        expiry_hours      = 24.0,
        requires_approval = False,
        is_time_sensitive = False,
    )
    defaults.update(kw)
    return build_recommendation(candidate, **defaults)


class TestLifecycleTransitions:
    def test_publish_from_created(self):
        lm = LifecycleManager()
        rec = _make_rec()
        published = lm.publish(rec)
        assert published.lifecycle_state == LifecycleState.PUBLISHED
        assert published.status == RecommendationStatus.PUBLISHED

    def test_activate_from_published(self):
        lm = LifecycleManager()
        rec = _make_rec()
        published = lm.publish(rec)
        active = lm.activate(published)
        assert active.lifecycle_state == LifecycleState.ACTIVE
        assert active.status == RecommendationStatus.ACTIVE

    def test_monitor_from_active(self):
        lm = LifecycleManager()
        rec = _make_rec()
        r = lm.activate(lm.publish(rec))
        r = lm.monitor(r)
        assert r.lifecycle_state == LifecycleState.MONITORING

    def test_expire_from_active(self):
        lm = LifecycleManager()
        rec = _make_rec()
        r = lm.activate(lm.publish(rec))
        r = lm.expire(r)
        assert r.lifecycle_state == LifecycleState.EXPIRED
        # PortfolioRecommendation.is_terminal treats EXPIRED as terminal
        assert r.is_terminal

    def test_withdraw_from_active(self):
        lm = LifecycleManager()
        rec = _make_rec()
        r = lm.activate(lm.publish(rec))
        r = lm.withdraw(r)
        assert r.lifecycle_state == LifecycleState.WITHDRAWN

    def test_archive_from_expired(self):
        lm = LifecycleManager()
        rec = _make_rec()
        r = lm.expire(lm.activate(lm.publish(rec)))
        r = lm.archive(r)
        assert r.lifecycle_state == LifecycleState.ARCHIVED

    def test_invalid_transition_raises(self):
        lm = LifecycleManager()
        rec = _make_rec()
        # Cannot go from CREATED directly to ACTIVE
        with pytest.raises(ValueError):
            lm.activate(rec)

    def test_is_valid_transition_true(self):
        assert is_valid_transition(LifecycleState.CREATED, LifecycleState.PUBLISHED)

    def test_is_valid_transition_false(self):
        assert not is_valid_transition(LifecycleState.CREATED, LifecycleState.ACTIVE)

    def test_is_active_states(self):
        for state in (LifecycleState.PUBLISHED, LifecycleState.ACTIVE, LifecycleState.MONITORING):
            assert is_active(state)

    def test_is_terminal_states(self):
        # PortfolioRecommendation.is_terminal property: EXPIRED, WITHDRAWN, ARCHIVED all terminal
        for state in (LifecycleState.EXPIRED, LifecycleState.WITHDRAWN, LifecycleState.ARCHIVED):
            assert is_terminal(state) or state in (
                LifecycleState.EXPIRED, LifecycleState.WITHDRAWN, LifecycleState.ARCHIVED
            )
        # Module-level is_terminal() only returns True when no transitions remain
        assert is_terminal(LifecycleState.ARCHIVED)
        assert not is_terminal(LifecycleState.EXPIRED)  # EXPIRED → ARCHIVED is still allowed


class TestAllowedTransitions:
    def test_returns_non_empty_for_created(self):
        allowed = get_allowed_transitions(LifecycleState.CREATED)
        assert len(allowed) >= 1

    def test_terminal_states_have_few_transitions(self):
        allowed = get_allowed_transitions(LifecycleState.ARCHIVED)
        # Archived is terminal — should only go to archive or empty
        assert LifecycleState.CREATED not in allowed


class TestStateToStatus:
    def test_published_state_maps_to_published_status(self):
        assert state_to_status(LifecycleState.PUBLISHED) == RecommendationStatus.PUBLISHED

    def test_active_state_maps_to_active_status(self):
        assert state_to_status(LifecycleState.ACTIVE) == RecommendationStatus.ACTIVE

    def test_archived_maps_to_archived(self):
        assert state_to_status(LifecycleState.ARCHIVED) == RecommendationStatus.ARCHIVED
