"""tests/unit/investment/portfolio/integration/test_aggregation.py

Tests for aggregation_state.py, aggregation_engine.py,
aggregation_history.py, portfolio_intelligence_aggregator.py.
"""
from __future__ import annotations

import pytest

from iios.investment.portfolio.integration.aggregation_engine import AggregationEngine
from iios.investment.portfolio.integration.aggregation_history import (
    AggregationHistory, AggregationRecord,
)
from iios.investment.portfolio.integration.aggregation_state import (
    AggregationState, EngineContribution,
)
from iios.investment.portfolio.integration.integration_types import (
    AggregationStatus, EngineId, IntegrationParameters, REQUIRED_ENGINES, now_utc,
)
from iios.investment.portfolio.integration.portfolio_intelligence_aggregator import (
    PortfolioIntelligenceAggregator,
)


def _contribute_all(agg: PortfolioIntelligenceAggregator, pid: str) -> None:
    for eid in REQUIRED_ENGINES:
        agg.contribute(pid, eid, {"engine": eid.value, "value": 1.0})


class TestEngineContribution:
    def test_creation(self):
        c = EngineContribution(
            engine_id      = EngineId.RISK,
            portfolio_id   = "P-1",
            contributed_at = now_utc(),
            data           = {"risk": 0.5},
        )
        assert c.engine_id == EngineId.RISK
        assert c.is_valid

    def test_age_hours_recent(self):
        c = EngineContribution(
            engine_id      = EngineId.RISK,
            portfolio_id   = "P-1",
            contributed_at = now_utc(),
            data           = {},
        )
        assert c.age_hours() < 0.01

    def test_frozen(self):
        c = EngineContribution(
            engine_id="risk", portfolio_id="P", contributed_at=now_utc(), data={}  # type: ignore
        )
        with pytest.raises((AttributeError, TypeError)):
            c.is_valid = False  # type: ignore


class TestAggregationState:
    def test_empty_completeness(self):
        state = AggregationState("P-1", IntegrationParameters())
        assert state.completeness() == 0.0

    def test_full_completeness(self):
        state = AggregationState("P-1", IntegrationParameters())
        for eid in REQUIRED_ENGINES:
            c = EngineContribution(
                engine_id=eid, portfolio_id="P-1",
                contributed_at=now_utc(), data={},
            )
            state.update(c)
        assert state.completeness() == 1.0

    def test_partial_completeness(self):
        state = AggregationState("P-1", IntegrationParameters())
        for eid in list(REQUIRED_ENGINES)[:5]:
            c = EngineContribution(
                engine_id=eid, portfolio_id="P-1",
                contributed_at=now_utc(), data={},
            )
            state.update(c)
        assert 0.0 < state.completeness() < 1.0

    def test_status_complete(self):
        state = AggregationState("P-1", IntegrationParameters())
        for eid in REQUIRED_ENGINES:
            c = EngineContribution(
                engine_id=eid, portfolio_id="P-1",
                contributed_at=now_utc(), data={},
            )
            state.update(c)
        assert state.status() == AggregationStatus.COMPLETE

    def test_status_partial(self):
        state = AggregationState("P-1", IntegrationParameters())
        # Only one engine
        c = EngineContribution(
            engine_id=EngineId.RISK, portfolio_id="P-1",
            contributed_at=now_utc(), data={},
        )
        state.update(c)
        assert state.status() == AggregationStatus.PARTIAL

    def test_missing_required_returns_list(self):
        state = AggregationState("P-1", IntegrationParameters())
        missing = state.missing_required()
        assert len(missing) == len(REQUIRED_ENGINES)

    def test_present_engines_valid_only(self):
        state = AggregationState("P-1", IntegrationParameters())
        c_valid = EngineContribution(
            engine_id=EngineId.RISK, portfolio_id="P-1",
            contributed_at=now_utc(), data={}, is_valid=True,
        )
        c_invalid = EngineContribution(
            engine_id=EngineId.ALLOCATION, portfolio_id="P-1",
            contributed_at=now_utc(), data={}, is_valid=False,
        )
        state.update(c_valid)
        state.update(c_invalid)
        present = state.present_engines()
        assert EngineId.RISK in present
        assert EngineId.ALLOCATION not in present


class TestAggregationEngine:
    def test_merge_produces_namespaced_dict(self):
        params = IntegrationParameters()
        state  = AggregationState("P-1", params)
        c = EngineContribution(
            engine_id=EngineId.RISK, portfolio_id="P-1",
            contributed_at=now_utc(), data={"risk_score": 0.5},
        )
        state.update(c)
        eng  = AggregationEngine()
        merged = eng.merge(state)
        assert "risk" in merged
        assert merged["risk"]["risk_score"] == 0.5

    def test_merge_includes_meta(self):
        params = IntegrationParameters()
        state  = AggregationState("P-2", params)
        eng    = AggregationEngine()
        merged = eng.merge(state)
        assert "_meta" in merged
        assert merged["_meta"]["portfolio_id"] == "P-2"

    def test_extract_value(self):
        params = IntegrationParameters()
        state  = AggregationState("P-3", params)
        c = EngineContribution(
            engine_id=EngineId.PERFORMANCE, portfolio_id="P-3",
            contributed_at=now_utc(), data={"sharpe_ratio": 1.20},
        )
        state.update(c)
        eng    = AggregationEngine()
        merged = eng.merge(state)
        v = eng.extract(merged, EngineId.PERFORMANCE, "sharpe_ratio", default=0.0)
        assert v == 1.20

    def test_extract_missing_returns_default(self):
        eng    = AggregationEngine()
        merged = {}
        v = eng.extract(merged, EngineId.RISK, "missing_key", default=-1)
        assert v == -1


class TestAggregationHistory:
    def test_add_and_retrieve(self):
        hist = AggregationHistory()
        rec  = AggregationRecord(
            portfolio_id="P-H",
            status=AggregationStatus.COMPLETE,
            n_engines=9,
            completeness=1.0,
        )
        hist.add(rec)
        results = hist.recent("P-H", 5)
        assert len(results) == 1
        assert results[0].status == AggregationStatus.COMPLETE

    def test_latest(self):
        hist = AggregationHistory()
        for i in range(3):
            hist.add(AggregationRecord(portfolio_id="P-H", status=AggregationStatus.PARTIAL))
        assert hist.latest("P-H") is not None

    def test_all_portfolio_ids(self):
        hist = AggregationHistory()
        hist.add(AggregationRecord(portfolio_id="P-A"))
        hist.add(AggregationRecord(portfolio_id="P-B"))
        pids = hist.all_portfolio_ids()
        assert "P-A" in pids
        assert "P-B" in pids


class TestPortfolioIntelligenceAggregator:
    def test_contribute_stores_state(self):
        agg = PortfolioIntelligenceAggregator()
        agg.contribute("P-1", EngineId.RISK, {"v": 1})
        state = agg.get_state("P-1")
        assert state is not None

    def test_full_contribution_complete(self):
        agg = PortfolioIntelligenceAggregator()
        _contribute_all(agg, "P-FULL")
        status = agg.aggregation_status("P-FULL")
        assert status == AggregationStatus.COMPLETE

    def test_partial_contribution_partial(self):
        agg = PortfolioIntelligenceAggregator()
        agg.contribute("P-PART", EngineId.RISK, {"v": 1})
        status = agg.aggregation_status("P-PART")
        assert status == AggregationStatus.PARTIAL

    def test_merge_returns_dict(self):
        agg = PortfolioIntelligenceAggregator()
        _contribute_all(agg, "P-M")
        merged = agg.merge("P-M")
        assert isinstance(merged, dict)
        assert "risk" in merged

    def test_merge_missing_returns_none(self):
        agg = PortfolioIntelligenceAggregator()
        assert agg.merge("NONEXISTENT") is None

    def test_record_run(self):
        agg = PortfolioIntelligenceAggregator()
        _contribute_all(agg, "P-R")
        record = agg.record_run("P-R", duration_ms=25.0)
        assert record.n_engines == 9

    def test_all_portfolio_ids(self):
        agg = PortfolioIntelligenceAggregator()
        agg.contribute("P-X", EngineId.RISK, {})
        agg.contribute("P-Y", EngineId.RISK, {})
        pids = agg.all_portfolio_ids()
        assert "P-X" in pids
        assert "P-Y" in pids
