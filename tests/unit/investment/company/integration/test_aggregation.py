"""tests/unit/investment/company/integration/test_aggregation.py
Tests for aggregation layer: aggregation state, history, aggregator, and engine.
"""
from __future__ import annotations

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock

from iios.investment.company.integration.aggregation_state import (
    AggregationState, EngineUpdate,
)
from iios.investment.company.integration.aggregation_history import AggregationHistory
from iios.investment.company.integration.company_intelligence_aggregator import (
    AggregatedIntelligence, aggregate_intelligence,
)
from iios.investment.company.integration.aggregation_engine import (
    AggregationEngine, compute_overall_score,
)
from iios.investment.company.integration.company_state import SCORED_ENGINES


class TestAggregationState:
    def test_initial_empty(self):
        state = AggregationState("X")
        assert state.available_engines() == []
        assert state.completeness() == 0.0

    def test_record_update(self, mock_financial):
        state = AggregationState("X")
        update = state.record_update("financials", mock_financial)
        assert isinstance(update, EngineUpdate)
        assert update.engine_name == "financials"
        assert "financials" in state.available_engines()

    def test_get_snapshot(self, mock_financial):
        state = AggregationState("X")
        state.record_update("financials", mock_financial)
        assert state.get_snapshot("financials") is mock_financial

    def test_unknown_engine_returns_none(self):
        state = AggregationState("X")
        assert state.get_snapshot("nonexistent") is None

    def test_completeness_partial(self, mock_financial, mock_earnings):
        state = AggregationState("X")
        state.record_update("financials", mock_financial)
        state.record_update("earnings", mock_earnings)
        expected = 2 / len(SCORED_ENGINES)
        assert state.completeness() == pytest.approx(expected)

    def test_completeness_full(
        self, mock_financial, mock_earnings, mock_bq,
        mock_valuation, mock_growth, mock_management, mock_ownership, mock_opportunity,
    ):
        state = AggregationState("X")
        for engine, snap in [
            ("financials", mock_financial), ("earnings", mock_earnings),
            ("business_quality", mock_bq), ("valuation", mock_valuation),
            ("growth", mock_growth), ("management", mock_management),
            ("ownership", mock_ownership), ("opportunity", mock_opportunity),
        ]:
            state.record_update(engine, snap)
        assert state.completeness() == pytest.approx(1.0)

    def test_missing_engines(self, mock_financial):
        state = AggregationState("X")
        state.record_update("financials", mock_financial)
        missing = state.missing_engines()
        assert "financials" not in missing
        assert "earnings" in missing

    def test_snapshot_map(self, mock_financial):
        state = AggregationState("X")
        state.record_update("financials", mock_financial)
        m = state.snapshot_map()
        assert m["financials"] is mock_financial

    def test_engine_ages(self, mock_financial):
        state = AggregationState("X")
        state.record_update("financials", mock_financial)
        ages = state.engine_ages()
        assert "financials" in ages
        assert ages["financials"] >= 0.0

    def test_eval_count(self):
        state = AggregationState("X")
        state.increment_eval()
        state.increment_eval()
        assert state.eval_count() == 2

    def test_last_update_at(self, mock_financial):
        state = AggregationState("X")
        state.record_update("financials", mock_financial)
        assert isinstance(state.last_update_at(), datetime)

    def test_to_dict(self, mock_financial):
        state = AggregationState("X")
        state.record_update("financials", mock_financial)
        d = state.to_dict()
        assert d["ticker"] == "X"
        assert "financials" in d["available_engines"]


class TestAggregationHistory:
    def test_record_and_retrieve(self):
        hist = AggregationHistory()
        snap = MagicMock(); snap.ticker = "T"; snap.overall_score = 60.0
        hist.record(snap)
        result = hist.get_history("T", 5)
        assert len(result) == 1

    def test_returns_newest_first(self):
        hist = AggregationHistory()
        for i in range(3):
            snap = MagicMock(); snap.ticker = "T"; snap.overall_score = float(50 + i * 10)
            hist.record(snap)
        result = hist.get_history("T", 3)
        assert result[0].overall_score == 70.0

    def test_latest(self):
        hist = AggregationHistory()
        for i in range(3):
            snap = MagicMock(); snap.ticker = "T"; snap.overall_score = float(i * 10)
            hist.record(snap)
        latest = hist.latest("T")
        assert latest.overall_score == 20.0

    def test_score_series(self):
        hist = AggregationHistory()
        for score in [40.0, 50.0, 60.0]:
            snap = MagicMock(); snap.ticker = "T"; snap.overall_score = score
            hist.record(snap)
        series = hist.score_series("T", n=5)
        assert series == [40.0, 50.0, 60.0]

    def test_score_trend_improving(self):
        hist = AggregationHistory()
        for score in [40.0, 50.0, 65.0]:
            snap = MagicMock(); snap.ticker = "T"; snap.overall_score = score
            hist.record(snap)
        assert hist.score_trend("T") > 0

    def test_unknown_ticker(self):
        hist = AggregationHistory()
        assert hist.get_history("UNKNOWN", 5) == []
        assert hist.latest("UNKNOWN") is None

    def test_count(self):
        hist = AggregationHistory()
        for _ in range(3):
            snap = MagicMock(); snap.ticker = "T"; snap.overall_score = 55.0
            hist.record(snap)
        assert hist.count("T") == 3


class TestAggregatedIntelligence:
    def test_aggregate_scores(self, mock_financial, mock_earnings, mock_bq):
        intel = aggregate_intelligence("X", {
            "financials": mock_financial,
            "earnings":   mock_earnings,
            "business_quality": mock_bq,
        })
        assert intel.financial_score == pytest.approx(72.0)
        assert intel.earnings_score  == pytest.approx(75.0)
        assert intel.business_quality_score == pytest.approx(72.0)

    def test_none_snapshot_gives_none_score(self):
        intel = aggregate_intelligence("X", {
            "financials": None,
            "earnings":   None,
        })
        assert intel.financial_score is None
        assert intel.earnings_score  is None

    def test_available_engines(self, mock_financial, mock_earnings):
        intel = aggregate_intelligence("X", {
            "financials": mock_financial,
            "earnings":   mock_earnings,
            "growth":     None,
        })
        assert "financials" in intel.available_engines
        assert "earnings"   in intel.available_engines
        assert "growth"     not in intel.available_engines

    def test_signal_extraction_profitable(self, mock_earnings):
        intel = aggregate_intelligence("X", {"earnings": mock_earnings})
        assert intel.is_profitable is True

    def test_signal_extraction_growing(self, mock_growth):
        intel = aggregate_intelligence("X", {"growth": mock_growth})
        assert intel.is_growing is True

    def test_opportunity_signals(self, mock_opportunity):
        intel = aggregate_intelligence("X", {"opportunity": mock_opportunity})
        assert intel.opportunity_category == "compounder"
        assert intel.opportunity_lifecycle == "high_conviction"


class TestComputeOverallScore:
    def test_all_neutral_gives_50(self):
        intel = AggregatedIntelligence(ticker="X")
        # All None → all use neutral (50)
        score = compute_overall_score(intel)
        assert score == pytest.approx(50.0)

    def test_all_high_gives_high(self):
        intel = AggregatedIntelligence(
            ticker="X",
            financial_score=90.0, earnings_score=90.0, business_quality_score=90.0,
            valuation_score=90.0, growth_score=90.0, management_score=90.0,
            ownership_score=90.0, opportunity_score=90.0,
        )
        score = compute_overall_score(intel)
        assert score == pytest.approx(90.0)

    def test_all_low_gives_low(self):
        intel = AggregatedIntelligence(
            ticker="X",
            financial_score=10.0, earnings_score=10.0, business_quality_score=10.0,
            valuation_score=10.0, growth_score=10.0, management_score=10.0,
            ownership_score=10.0, opportunity_score=10.0,
        )
        score = compute_overall_score(intel)
        assert score == pytest.approx(10.0)

    def test_partial_engines_neutral_for_missing(self):
        intel = AggregatedIntelligence(
            ticker="X",
            financial_score=80.0,   # financials weight 0.20
            earnings_score=None,     # uses neutral 50
        )
        score = compute_overall_score(intel)
        # Score between 50 and 80 (weighted toward neutral)
        assert 50.0 < score < 80.0

    def test_good_beats_weak(self):
        good = AggregatedIntelligence(
            ticker="G",
            financial_score=80.0, earnings_score=78.0, business_quality_score=75.0,
        )
        weak = AggregatedIntelligence(
            ticker="W",
            financial_score=20.0, earnings_score=22.0, business_quality_score=18.0,
        )
        assert compute_overall_score(good) > compute_overall_score(weak)


class TestAggregationEngine:
    def test_aggregate_returns_intel(self, mock_financial, mock_earnings, mock_bq):
        engine = AggregationEngine()
        intel = engine.aggregate("X", {
            "financials": mock_financial,
            "earnings":   mock_earnings,
            "business_quality": mock_bq,
        })
        assert isinstance(intel, AggregatedIntelligence)
        assert intel.ticker == "X"

    def test_overall_score(self, mock_financial, mock_earnings, mock_bq):
        engine = AggregationEngine()
        intel  = engine.aggregate("X", {
            "financials": mock_financial,
            "earnings":   mock_earnings,
            "business_quality": mock_bq,
        })
        score = engine.overall_score(intel)
        assert 0.0 <= score <= 100.0

    def test_build_summary(self, mock_financial, mock_earnings, mock_bq):
        from iios.investment.company.integration.company_summary import CompanySummary
        engine = AggregationEngine()
        intel  = engine.aggregate("X", {
            "financials": mock_financial,
            "earnings":   mock_earnings,
            "business_quality": mock_bq,
        })
        summary = engine.build_summary("X", "TestCo", intel)
        assert isinstance(summary, CompanySummary)
        assert summary.ticker == "X"
        assert summary.company_name == "TestCo"
