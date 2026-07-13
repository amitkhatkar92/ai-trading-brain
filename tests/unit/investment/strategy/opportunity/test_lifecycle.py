"""tests/unit/investment/strategy/opportunity/test_lifecycle.py"""
from __future__ import annotations

import pytest

from iios.investment.strategy.opportunity.strategy_opportunity import (
    StrategyOpportunity, OpportunityState
)
from iios.investment.strategy.opportunity.lifecycle_engine import LifecycleEngine
from iios.investment.strategy.opportunity.lifecycle_history import LifecycleHistory


def _opp(opp_id="o1", strategy_id="s1") -> StrategyOpportunity:
    return StrategyOpportunity(
        opportunity_id=opp_id,
        strategy_id=strategy_id,
        strategy_name="Test",
        market_opportunity_id="mkt-1",
        company_opportunity_id=None,
    )


class TestStrategyOpportunityStateMachine:
    def test_initial_state_discovered(self):
        opp = _opp()
        assert opp.state == OpportunityState.DISCOVERED

    def test_valid_transition_allowed(self):
        opp = _opp()
        assert opp.can_transition_to(OpportunityState.CANDIDATE)
        opp._apply_transition(OpportunityState.CANDIDATE, "test", "test")
        assert opp.state == OpportunityState.CANDIDATE

    def test_invalid_transition_raises(self):
        opp = _opp()
        with pytest.raises(ValueError):
            opp._apply_transition(OpportunityState.APPROVED, "jump", "test")

    def test_terminal_state_no_transitions(self):
        opp = _opp()
        opp._apply_transition(OpportunityState.CANDIDATE, "r", "t")
        opp._apply_transition(OpportunityState.RECOMMENDED, "r", "t")
        opp._apply_transition(OpportunityState.APPROVED, "r", "t")
        opp._apply_transition(OpportunityState.MONITORING, "r", "t")
        opp._apply_transition(OpportunityState.EXPIRED, "r", "t")
        opp._apply_transition(OpportunityState.ARCHIVED, "r", "t")
        assert not opp.can_transition_to(OpportunityState.DISCOVERED)

    def test_state_history_recorded(self):
        opp = _opp()
        opp._apply_transition(OpportunityState.CANDIDATE, "matched", "engine")
        assert len(opp.state_history) == 1
        assert opp.state_history[0].reason == "matched"

    def test_composite_score_formula(self):
        opp = _opp()
        opp.matching_score   = 80.0
        opp.suitability_score = 70.0
        opp.ranking_score    = 90.0
        expected = 0.35 * 80.0 + 0.35 * 70.0 + 0.30 * 90.0
        assert opp.composite_score() == pytest.approx(expected)

    def test_is_active_initial(self):
        assert _opp().is_active()

    def test_is_not_active_after_expiry(self):
        opp = _opp()
        opp._apply_transition(OpportunityState.EXPIRED, "expired", "system")
        assert not opp.is_active()

    def test_to_dict_has_keys(self):
        opp = _opp()
        d   = opp.to_dict()
        for key in ["opportunity_id", "strategy_id", "state", "composite_score"]:
            assert key in d


class TestLifecycleEngine:
    def test_advance_to_candidate(self):
        lc  = LifecycleEngine()
        opp = _opp()
        ok  = lc.advance_to_candidate(opp)
        assert ok
        assert opp.state == OpportunityState.CANDIDATE

    def test_advance_full_pipeline(self):
        lc  = LifecycleEngine()
        opp = _opp()
        assert lc.advance_to_candidate(opp)
        assert lc.advance_to_recommended(opp)
        assert lc.advance_to_approved(opp)
        assert lc.advance_to_monitoring(opp)
        assert lc.expire(opp)
        assert lc.archive(opp)
        assert opp.state == OpportunityState.ARCHIVED

    def test_invalid_advance_returns_false(self):
        lc  = LifecycleEngine()
        opp = _opp()
        # Skip CANDIDATE → jump to MONITORING
        result = lc.advance_to_monitoring(opp)
        assert result is False
        assert opp.state == OpportunityState.DISCOVERED

    def test_check_and_expire_past_ttl(self):
        from datetime import datetime, timedelta, timezone
        lc  = LifecycleEngine()
        opp = _opp()
        lc.advance_to_candidate(opp)
        opp.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        expired = lc.check_and_expire(opp)
        assert expired
        assert opp.state == OpportunityState.EXPIRED

    def test_check_and_expire_future_ttl(self):
        from datetime import datetime, timedelta, timezone
        lc  = LifecycleEngine()
        opp = _opp()
        lc.advance_to_candidate(opp)
        opp.expires_at = datetime.now(timezone.utc) + timedelta(hours=2)
        expired = lc.check_and_expire(opp)
        assert not expired


class TestLifecycleHistory:
    def test_record_and_timeline(self):
        hist = LifecycleHistory()
        opp  = _opp()
        lc   = LifecycleEngine()
        lc.advance_to_candidate(opp)
        hist.record("o1", "s1", opp.state_history[-1])
        tl = hist.timeline("o1")
        assert len(tl) == 1
        assert tl[0].to_state == OpportunityState.CANDIDATE

    def test_state_counts(self):
        hist = LifecycleHistory()
        opp  = _opp("o1")
        lc   = LifecycleEngine()
        lc.advance_to_candidate(opp)
        hist.record("o1", "s1", opp.state_history[-1])
        counts = hist.state_counts()
        assert counts.get("candidate", 0) >= 1

    def test_purge_clears_timeline(self):
        hist = LifecycleHistory()
        opp  = _opp()
        LifecycleEngine().advance_to_candidate(opp)
        hist.record("o1", "s1", opp.state_history[-1])
        hist.purge("o1")
        assert hist.timeline("o1") == []
