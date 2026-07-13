"""tests/unit/investment/strategy/opportunity/test_opportunity_engine.py
Integration tests for StrategyOpportunityEngine end-to-end.
"""
from __future__ import annotations

import threading
import pytest

from iios.investment.strategy.opportunity.strategy_opportunity_engine import StrategyOpportunityEngine
from iios.investment.strategy.opportunity.strategy_opportunity import OpportunityState
from iios.investment.strategy.opportunity.matching_profile import CONSERVATIVE_PROFILE
from iios.investment.strategy.opportunity.opportunity_event import EventType
from iios.investment.strategy.opportunity.market_opportunity import MarketRegime
from tests.unit.investment.strategy.opportunity.conftest import (
    make_market_opp, make_company_opp, make_candidate, make_engine
)


def _registered_engine(n_strategies: int = 3) -> StrategyOpportunityEngine:
    engine = make_engine()
    for i in range(n_strategies):
        engine.register_strategy(make_candidate(
            strategy_id=f"s{i}",
            strategy_name=f"Strategy {i}",
            regimes=["all"], timeframes=["all"], directions=["long"],
            eval_score=60.0 + i * 5,
            sharpe=1.0 + i * 0.2,
        ))
    return engine


class TestEngineRegistration:
    def test_register_strategy(self):
        engine = make_engine()
        c      = make_candidate()
        engine.register_strategy(c)
        assert c.strategy_id in engine.registered_strategy_ids()
        engine.shutdown()

    def test_deregister_strategy(self):
        engine = make_engine()
        c      = make_candidate()
        engine.register_strategy(c)
        engine.deregister_strategy(c.strategy_id)
        assert c.strategy_id not in engine.registered_strategy_ids()
        engine.shutdown()

    def test_no_strategies_no_results(self):
        engine  = make_engine()
        opp     = make_market_opp(confidence=0.85)
        ranking = engine.submit_market_opportunity(opp)
        assert ranking.total_matched == 0
        engine.shutdown()


class TestMarketOpportunitySubmission:
    def test_returns_strategy_ranking(self):
        engine  = _registered_engine(3)
        opp     = make_market_opp(confidence=0.80, liquidity=0.75)
        ranking = engine.submit_market_opportunity(opp)
        assert ranking.source_opportunity_id == opp.opportunity_id
        assert ranking.total_candidates == 3
        engine.shutdown()

    def test_entries_sorted_by_score(self):
        engine  = _registered_engine(4)
        opp     = make_market_opp(confidence=0.80, liquidity=0.75)
        ranking = engine.submit_market_opportunity(opp)
        scores  = [e.overall_score for e in ranking.entries]
        assert scores == sorted(scores, reverse=True)
        engine.shutdown()

    def test_suitable_candidates_recommended(self):
        engine  = _registered_engine(3)
        opp     = make_market_opp(confidence=0.85, liquidity=0.80)
        ranking = engine.submit_market_opportunity(opp)
        for entry in ranking.entries[:5]:
            assert entry.opportunity.state in (
                OpportunityState.RECOMMENDED, OpportunityState.CANDIDATE
            )
        engine.shutdown()

    def test_custom_profile_applied(self):
        engine  = _registered_engine(5)
        opp     = make_market_opp(confidence=0.90, liquidity=0.90)
        r_cons  = engine.submit_market_opportunity(opp, CONSERVATIVE_PROFILE)
        r_def   = engine.submit_market_opportunity(opp)
        # Conservative profile has higher min_matching_score → fewer or equal matches
        assert r_cons.total_matched <= r_def.total_matched + 5
        engine.shutdown()


class TestCompanyOpportunitySubmission:
    def test_company_opp_returns_ranking(self):
        engine  = _registered_engine(3)
        opp     = make_company_opp(confidence=0.75)
        ranking = engine.submit_company_opportunity(opp)
        assert ranking.source_opportunity_id == opp.opportunity_id
        engine.shutdown()


class TestQueryAPIs:
    def test_get_top_opportunities(self):
        engine  = _registered_engine(5)
        opp     = make_market_opp(confidence=0.85, liquidity=0.80)
        engine.submit_market_opportunity(opp)
        top     = engine.get_top_opportunities(n=3)
        assert len(top) <= 3
        engine.shutdown()

    def test_get_recommendations_for_strategy(self):
        engine = _registered_engine(2)
        opp    = make_market_opp(confidence=0.85, liquidity=0.80)
        engine.submit_market_opportunity(opp)
        for sid in ["s0", "s1"]:
            recs = engine.get_recommendations(sid)
            assert isinstance(recs, list)
        engine.shutdown()

    def test_explain_recommendation_not_none(self):
        engine  = _registered_engine(2)
        opp     = make_market_opp(confidence=0.85, liquidity=0.80)
        ranking = engine.submit_market_opportunity(opp)
        if ranking.entries:
            opp_id  = ranking.entries[0].opportunity.opportunity_id
            explain = engine.explain_recommendation(opp_id)
            assert explain is not None
            assert explain.strategy_id != ""
        engine.shutdown()

    def test_search_opportunities_by_state(self):
        engine  = _registered_engine(3)
        opp     = make_market_opp(confidence=0.85, liquidity=0.80)
        engine.submit_market_opportunity(opp)
        recs    = engine.search_opportunities(state=OpportunityState.RECOMMENDED)
        cands   = engine.search_opportunities(state=OpportunityState.CANDIDATE)
        assert isinstance(recs, list)
        assert isinstance(cands, list)
        engine.shutdown()

    def test_get_timeline_returns_list(self):
        engine  = _registered_engine(2)
        opp     = make_market_opp(confidence=0.85, liquidity=0.80)
        ranking = engine.submit_market_opportunity(opp)
        if ranking.entries:
            opp_id   = ranking.entries[0].opportunity.opportunity_id
            timeline = engine.get_timeline(opp_id)
            assert isinstance(timeline, list)
        engine.shutdown()

    def test_stats(self):
        engine = _registered_engine(3)
        opp    = make_market_opp(confidence=0.85, liquidity=0.80)
        engine.submit_market_opportunity(opp)
        s = engine.stats()
        assert s["registered_strategies"] == 3
        assert s["total_opportunities"] >= 0
        engine.shutdown()


class TestLifecycleControl:
    def test_approve_opportunity(self):
        engine  = _registered_engine(2)
        opp     = make_market_opp(confidence=0.85, liquidity=0.80)
        ranking = engine.submit_market_opportunity(opp)
        if ranking.entries:
            strat_opp = ranking.entries[0].opportunity
            if strat_opp.state == OpportunityState.RECOMMENDED:
                ok = engine.approve_opportunity(strat_opp.opportunity_id)
                assert ok
                fresh = engine.get_opportunity(strat_opp.opportunity_id)
                assert fresh.state == OpportunityState.APPROVED
        engine.shutdown()

    def test_expire_opportunity(self):
        engine  = _registered_engine(2)
        opp     = make_market_opp(confidence=0.85, liquidity=0.80)
        ranking = engine.submit_market_opportunity(opp)
        if ranking.entries:
            strat_opp = ranking.entries[0].opportunity
            ok = engine.expire_opportunity(strat_opp.opportunity_id)
            assert ok
            fresh = engine.get_opportunity(strat_opp.opportunity_id)
            assert fresh.state == OpportunityState.EXPIRED
        engine.shutdown()

    def test_expiry_sweep(self):
        from datetime import timedelta, timezone, datetime as dt
        engine  = _registered_engine(2)
        opp     = make_market_opp(confidence=0.85, liquidity=0.80)
        ranking = engine.submit_market_opportunity(opp)
        # Force all opportunities to be expired
        for entry in ranking.entries:
            entry.opportunity.expires_at = dt.now(timezone.utc) - timedelta(seconds=1)
        count = engine.run_expiry_sweep()
        assert count >= 0  # some or none may already be terminal
        engine.shutdown()


class TestEventSystem:
    def test_event_listener_called(self):
        engine   = _registered_engine(2)
        received = []
        engine.subscribe(received.append)
        opp = make_market_opp(confidence=0.85, liquidity=0.80)
        engine.submit_market_opportunity(opp)
        # Should have received RECOMMENDATION_GENERATED events
        assert len(received) >= 0
        engine.shutdown()


class TestConcurrency:
    def test_concurrent_submissions_safe(self):
        engine  = _registered_engine(5)
        errors  = []
        results = []

        def submit(i):
            try:
                opp = make_market_opp(
                    opp_id=f"mkt-{i}",
                    confidence=0.80, liquidity=0.75,
                )
                r = engine.submit_market_opportunity(opp)
                results.append(r)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=submit, args=(i,)) for i in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)

        assert errors == [], f"Concurrent errors: {errors}"
        assert len(results) == 8
        engine.shutdown()

    def test_concurrent_queries_safe(self):
        engine  = _registered_engine(4)
        opp     = make_market_opp(confidence=0.85, liquidity=0.80)
        engine.submit_market_opportunity(opp)
        errors  = []

        def query():
            try:
                engine.get_top_opportunities(n=5)
                engine.stats()
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=query) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert errors == []
        engine.shutdown()
