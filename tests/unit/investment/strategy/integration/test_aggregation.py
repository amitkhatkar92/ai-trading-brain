"""tests/unit/investment/strategy/integration/test_aggregation.py
Tests for aggregation layer: AggregationEngine, AggregationHistory,
StrategyIntelligenceAggregator, and StrategyAggregationState.
"""
from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone

import pytest

from iios.investment.strategy.integration.aggregation_engine import AggregationEngine
from iios.investment.strategy.integration.aggregation_history import AggregationHistory
from iios.investment.strategy.integration.aggregation_state import (
    IntelligenceUpdate,
    StrategyAggregationState,
    make_update,
)
from iios.investment.strategy.integration.integration_constants import (
    IntelligenceSource,
    UpdateType,
)
from iios.investment.strategy.integration.strategy_intelligence_aggregator import (
    StrategyIntelligenceAggregator,
)
from tests.unit.investment.strategy.integration.conftest import (
    make_eval_update,
    make_risk_update,
    make_lifecycle_update,
    make_framework_update,
    make_full_state,
)


# ===========================================================================
# make_update factory
# ===========================================================================

class TestMakeUpdate:
    def test_basic_fields(self):
        u = make_update(
            source=IntelligenceSource.EVALUATION,
            strategy_id="STRAT-1",
            payload={"score": 80},
            confidence=75.0,
        )
        assert u.source == IntelligenceSource.EVALUATION
        assert u.strategy_id == "STRAT-1"
        assert u.payload["score"] == 80
        assert u.confidence == 75.0
        assert u.update_id  # non-empty UUID
        assert u.update_type == UpdateType.FULL_SNAPSHOT  # default

    def test_confidence_clamped(self):
        u = make_update(IntelligenceSource.RISK, "S1", {}, confidence=999.0)
        assert 0.0 <= u.confidence <= 100.0

    def test_to_dict(self):
        u = make_eval_update("S1")
        d = u.to_dict()
        assert d["source"] == IntelligenceSource.EVALUATION.value
        assert "update_id" in d


# ===========================================================================
# StrategyAggregationState
# ===========================================================================

class TestStrategyAggregationState:
    def test_apply_and_get_latest(self):
        state = StrategyAggregationState("STRAT-A")
        u = make_eval_update("STRAT-A")
        state.apply(u)
        assert state.get_latest(IntelligenceSource.EVALUATION) is u

    def test_version_increments(self):
        state = StrategyAggregationState("STRAT-A")
        assert state.version == 0
        state.apply(make_eval_update("STRAT-A"))
        assert state.version == 1
        state.apply(make_risk_update("STRAT-A"))
        assert state.version == 2

    def test_history_grows(self):
        state = StrategyAggregationState("STRAT-A")
        state.apply(make_eval_update("STRAT-A"))
        state.apply(make_eval_update("STRAT-A"))
        hist = state.history(IntelligenceSource.EVALUATION)
        assert len(hist) == 2

    def test_present_sources(self):
        state = StrategyAggregationState("STRAT-A")
        state.apply(make_eval_update("STRAT-A"))
        state.apply(make_risk_update("STRAT-A"))
        present = state.present_sources()
        assert IntelligenceSource.EVALUATION in present
        assert IntelligenceSource.RISK in present

    def test_all_latest_dict(self):
        state = StrategyAggregationState("STRAT-A")
        u1 = make_eval_update("STRAT-A")
        u2 = make_risk_update("STRAT-A")
        state.apply(u1)
        state.apply(u2)
        latest = state.all_latest()
        assert len(latest) == 2

    def test_to_dict_serialisable(self):
        state = StrategyAggregationState("STRAT-A")
        state.apply(make_eval_update("STRAT-A"))
        d = state.to_dict()
        assert d["strategy_id"] == "STRAT-A"
        assert "version" in d


# ===========================================================================
# AggregationEngine
# ===========================================================================

class TestAggregationEngine:
    def test_apply_stores_state(self):
        eng = AggregationEngine()
        u = make_eval_update("STRAT-X")
        eng.apply(u)
        state = eng.get_state("STRAT-X")
        assert state is not None
        assert state.get_latest(IntelligenceSource.EVALUATION) is u

    def test_known_strategies(self):
        eng = AggregationEngine()
        eng.apply(make_eval_update("A"))
        eng.apply(make_eval_update("B"))
        assert set(eng.known_strategies()) == {"A", "B"}

    def test_completeness_partial(self):
        eng = AggregationEngine()
        eng.apply(make_eval_update("S1"))
        c = eng.completeness("S1")
        assert 0 < c < 1

    def test_completeness_full_required(self):
        sid, state, eng = make_full_state("FULL-1")
        c = eng.completeness("FULL-1")
        # At least 4 required sources covered — completeness >= 0.4
        assert c >= 0.4

    def test_average_confidence(self):
        eng = AggregationEngine()
        eng.apply(make_eval_update("S2", confidence=60.0))
        eng.apply(make_risk_update("S2", confidence=40.0))
        avg = eng.average_confidence("S2")
        assert avg == pytest.approx(50.0, abs=1.0)

    def test_freshness_score_new_updates(self):
        eng = AggregationEngine()
        eng.apply(make_eval_update("S3"))
        fs = eng.freshness_score("S3")
        assert fs > 0.9  # just submitted → very fresh

    def test_stale_sources_empty_for_new(self):
        eng = AggregationEngine()
        eng.apply(make_eval_update("S4"))
        stale = eng.stale_sources("S4")
        assert stale == []

    def test_stats_returns_dict(self):
        eng = AggregationEngine()
        eng.apply(make_eval_update("S5"))
        s = eng.stats()
        assert "total_strategies" in s


# ===========================================================================
# AggregationHistory
# ===========================================================================

class TestAggregationHistory:
    def test_record_and_retrieve(self):
        hist = AggregationHistory(max_size=10)
        u = make_eval_update("H1")
        hist.record(u)
        assert u in hist.for_strategy("H1")

    def test_max_size_ring(self):
        hist = AggregationHistory(max_size=3)
        for _ in range(5):
            hist.record(make_eval_update("R1"))
        assert hist.current_size() <= 3

    def test_for_source(self):
        hist = AggregationHistory()
        hist.record(make_eval_update("S"))
        hist.record(make_risk_update("S"))
        assert len(hist.for_source(IntelligenceSource.EVALUATION)) >= 1

    def test_recent(self):
        hist = AggregationHistory()
        for _ in range(10):
            hist.record(make_eval_update("RR"))
        assert len(hist.recent(5)) == 5

    def test_total_recorded(self):
        hist = AggregationHistory()
        hist.record_all([make_eval_update("T"), make_risk_update("T")])
        assert hist.total_recorded() == 2


# ===========================================================================
# StrategyIntelligenceAggregator (facade)
# ===========================================================================

class TestStrategyIntelligenceAggregator:
    def test_submit_and_state(self):
        agg = StrategyIntelligenceAggregator()
        u = make_eval_update("FAC1")
        agg.submit(u)
        state = agg.state("FAC1")
        assert state is not None

    def test_known_strategies(self):
        agg = StrategyIntelligenceAggregator()
        agg.submit(make_eval_update("K1"))
        agg.submit(make_eval_update("K2"))
        assert set(agg.known_strategies()) >= {"K1", "K2"}

    def test_completeness_increases_with_sources(self):
        agg = StrategyIntelligenceAggregator()
        sid = "COMP1"
        agg.submit(make_eval_update(sid))
        c1 = agg.completeness(sid)
        agg.submit(make_risk_update(sid))
        c2 = agg.completeness(sid)
        assert c2 >= c1

    def test_latest(self):
        agg = StrategyIntelligenceAggregator()
        sid = "LAT1"
        u = make_eval_update(sid)
        agg.submit(u)
        assert agg.latest(sid, IntelligenceSource.EVALUATION) is u

    def test_history_for(self):
        agg = StrategyIntelligenceAggregator()
        sid = "HF1"
        agg.submit(make_eval_update(sid))
        assert len(agg.history_for(sid)) >= 1

    def test_stats(self):
        agg = StrategyIntelligenceAggregator()
        agg.submit(make_eval_update("ST1"))
        s = agg.stats()
        assert "total_strategies" in s

    def test_submit_all(self):
        agg = StrategyIntelligenceAggregator()
        sid = "ALL1"
        updates = [make_eval_update(sid), make_risk_update(sid)]
        agg.submit_all(updates)
        assert agg.completeness(sid) > 0
