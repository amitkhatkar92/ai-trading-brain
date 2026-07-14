"""tests/unit/investment/decision/core/test_lifecycle.py
Tests for DecisionState, DecisionLifecycle, DecisionSession, DecisionHistory.
"""
from __future__ import annotations

import pytest
from datetime import datetime, timezone

from iios.investment.decision.core.decision_constants import (
    ApprovalStatus,
    DecisionStatus,
    DecisionType,
    RiskReviewStatus,
    RecommendationType,
    EnvironmentProfile,
)
from iios.investment.decision.core.decision_context import make_context
from iios.investment.decision.core.decision_history import DecisionHistory
from iios.investment.decision.core.decision_lifecycle import DecisionLifecycle
from iios.investment.decision.core.decision_session import DecisionSession
from iios.investment.decision.core.decision_state import DecisionState, InvalidTransitionError


# ===========================================================================
# DecisionState
# ===========================================================================

class TestDecisionState:
    def test_initial_status_is_created(self):
        s = DecisionState("D1")
        assert s.status == DecisionStatus.CREATED

    def test_valid_transition(self):
        s = DecisionState("D1")
        s.transition_to(DecisionStatus.COLLECTING_EVIDENCE)
        assert s.status == DecisionStatus.COLLECTING_EVIDENCE

    def test_invalid_transition_raises(self):
        s = DecisionState("D1")
        with pytest.raises(InvalidTransitionError):
            s.transition_to(DecisionStatus.ARCHIVED)

    def test_fail_sets_status(self):
        s = DecisionState("D2")
        s.fail("some error")
        assert s.status == DecisionStatus.FAILED
        assert s.error_message == "some error"
        assert s.is_failed

    def test_update_score_clamped(self):
        s = DecisionState("D3")
        s.update_score(150.0, -10.0)
        assert s.score == 100.0
        assert s.confidence == 0.0

    def test_update_recommendation(self):
        s = DecisionState("D4")
        s.update_recommendation(RecommendationType.STRONG_BUY, "great signal")
        assert s.recommendation == RecommendationType.STRONG_BUY
        assert s.explanation == "great signal"

    def test_update_risk_review(self):
        s = DecisionState("D5")
        s.update_risk_review(RiskReviewStatus.APPROVED)
        assert s.risk_review_status == RiskReviewStatus.APPROVED

    def test_update_approval(self):
        s = DecisionState("D6")
        s.update_approval(ApprovalStatus.APPROVED)
        assert s.approval_status == ApprovalStatus.APPROVED

    def test_phase_timestamps_populated(self):
        s = DecisionState("D7")
        assert DecisionStatus.CREATED.value in s.phase_timestamps
        s.transition_to(DecisionStatus.COLLECTING_EVIDENCE)
        assert DecisionStatus.COLLECTING_EVIDENCE.value in s.phase_timestamps

    def test_to_dict_keys(self):
        s = DecisionState("D8")
        d = s.to_dict()
        assert "decision_id" in d
        assert "status" in d
        assert "score" in d

    def test_full_happy_path_transitions(self):
        s = DecisionState("D9")
        path = [
            DecisionStatus.COLLECTING_EVIDENCE,
            DecisionStatus.UNDER_REVIEW,
            DecisionStatus.SCORED,
            DecisionStatus.RISK_REVIEWED,
            DecisionStatus.APPROVED,
            DecisionStatus.PUBLISHED,
            DecisionStatus.ARCHIVED,
        ]
        for status in path:
            s.transition_to(status)
        assert s.status == DecisionStatus.ARCHIVED

    def test_rejection_path(self):
        s = DecisionState("D10")
        for st in [
            DecisionStatus.COLLECTING_EVIDENCE,
            DecisionStatus.UNDER_REVIEW,
            DecisionStatus.SCORED,
            DecisionStatus.RISK_REVIEWED,
            DecisionStatus.REJECTED,
            DecisionStatus.ARCHIVED,
        ]:
            s.transition_to(st)
        assert s.status == DecisionStatus.ARCHIVED


# ===========================================================================
# DecisionLifecycle
# ===========================================================================

class TestDecisionLifecycle:
    def test_valid_transition_recorded(self):
        lc = DecisionLifecycle("D11")
        lc.record_transition(DecisionStatus.CREATED, DecisionStatus.COLLECTING_EVIDENCE)
        phases = lc.all_phases()
        assert len(phases) == 1
        assert phases[0].from_status == DecisionStatus.CREATED
        assert phases[0].to_status == DecisionStatus.COLLECTING_EVIDENCE

    def test_invalid_transition_raises(self):
        lc = DecisionLifecycle("D12")
        with pytest.raises(InvalidTransitionError):
            lc.record_transition(DecisionStatus.CREATED, DecisionStatus.PUBLISHED)

    def test_total_duration_none_on_empty(self):
        lc = DecisionLifecycle("D13")
        assert lc.total_duration_ms() is None

    def test_total_duration_after_transitions(self):
        lc = DecisionLifecycle("D14")
        lc.record_transition(DecisionStatus.CREATED, DecisionStatus.COLLECTING_EVIDENCE)
        lc.record_transition(DecisionStatus.COLLECTING_EVIDENCE, DecisionStatus.UNDER_REVIEW)
        dur = lc.total_duration_ms()
        assert dur is not None
        assert dur >= 0

    def test_is_valid_next(self):
        lc = DecisionLifecycle("D15")
        assert lc.is_valid_next(DecisionStatus.CREATED, DecisionStatus.COLLECTING_EVIDENCE)
        assert not lc.is_valid_next(DecisionStatus.CREATED, DecisionStatus.PUBLISHED)

    def test_to_dict(self):
        lc = DecisionLifecycle("D16")
        d  = lc.to_dict()
        assert "decision_id" in d
        assert "phases" in d


# ===========================================================================
# DecisionSession
# ===========================================================================

class TestDecisionSession:
    def test_create_session(self):
        s = DecisionSession(name="test_session")
        assert s.is_open
        assert s.decision_count == 0

    def test_add_and_remove_decision(self):
        s = DecisionSession()
        s.add_decision("D1")
        assert s.decision_count == 1
        s.remove_decision("D1")
        assert s.decision_count == 0

    def test_no_duplicate_decisions(self):
        s = DecisionSession()
        s.add_decision("D1")
        s.add_decision("D1")
        assert s.decision_count == 1

    def test_close_session(self):
        s = DecisionSession()
        s.close()
        assert not s.is_open
        assert s.closed_at is not None

    def test_double_close_idempotent(self):
        s = DecisionSession()
        s.close()
        ts = s.closed_at
        s.close()
        assert s.closed_at == ts

    def test_add_tag(self):
        s = DecisionSession()
        s.add_tag("portfolio_review")
        assert "portfolio_review" in s.to_dict()["tags"]

    def test_decision_ids_list(self):
        s = DecisionSession()
        s.add_decision("X1")
        s.add_decision("X2")
        assert "X1" in s.decision_ids
        assert "X2" in s.decision_ids

    def test_to_dict(self):
        s = DecisionSession(name="s1")
        d = s.to_dict()
        assert "session_id" in d
        assert "is_open" in d


# ===========================================================================
# DecisionHistory
# ===========================================================================

class TestDecisionHistory:
    def _make_context_and_state(self, subject_id: str = "TCS") -> tuple:
        ctx   = make_context(DecisionType.INVESTMENT, subject_id, "equity", "test")
        state = DecisionState(ctx.decision_id)
        state.transition_to(DecisionStatus.COLLECTING_EVIDENCE)
        state.transition_to(DecisionStatus.UNDER_REVIEW)
        state.transition_to(DecisionStatus.SCORED)
        state.transition_to(DecisionStatus.RISK_REVIEWED)
        state.transition_to(DecisionStatus.APPROVED)
        state.transition_to(DecisionStatus.PUBLISHED)
        state.transition_to(DecisionStatus.ARCHIVED)
        state.update_recommendation(RecommendationType.BUY, "good buy")
        state.update_score(75.0)
        return ctx, state

    def test_record_and_retrieve(self):
        history = DecisionHistory()
        ctx, state = self._make_context_and_state("TCS")
        history.record(ctx, state, datetime.now(timezone.utc))
        assert history.count() == 1

    def test_for_subject(self):
        history = DecisionHistory()
        ctx, state = self._make_context_and_state("WIPRO")
        history.record(ctx, state, datetime.now(timezone.utc))
        records = history.for_subject("WIPRO")
        assert len(records) >= 1

    def test_for_type(self):
        history = DecisionHistory()
        ctx, state = self._make_context_and_state("INFY")
        history.record(ctx, state, datetime.now(timezone.utc))
        records = history.for_type(DecisionType.INVESTMENT)
        assert len(records) >= 1

    def test_recent(self):
        history = DecisionHistory()
        for sid in ["A", "B", "C"]:
            ctx, state = self._make_context_and_state(sid)
            history.record(ctx, state, datetime.now(timezone.utc))
        assert len(history.recent(2)) == 2

    def test_get_by_id(self):
        history = DecisionHistory()
        ctx, state = self._make_context_and_state("HDFC")
        history.record(ctx, state, datetime.now(timezone.utc))
        rec = history.get(ctx.decision_id)
        assert rec is not None
        assert rec.subject_id == "HDFC"

    def test_get_missing_returns_none(self):
        history = DecisionHistory()
        assert history.get("nonexistent") is None

    def test_stats(self):
        history = DecisionHistory()
        ctx, state = self._make_context_and_state("SBI")
        history.record(ctx, state, datetime.now(timezone.utc))
        s = history.stats()
        assert "total" in s
        assert s["total"] == 1

    def test_max_size_ring(self):
        history = DecisionHistory(max_size=3)
        for i in range(5):
            ctx, state = self._make_context_and_state(f"X{i}")
            history.record(ctx, state, datetime.now(timezone.utc))
        assert history.count() == 3
