"""tests/unit/investment/market/integration/test_aggregation.py"""
from __future__ import annotations

import pytest

from iios.investment.market.integration.aggregation_engine import AggregationEngine
from iios.investment.market.integration.aggregation_history import AggregationHistory
from iios.investment.market.integration.aggregation_state import AggregationState
from iios.investment.market.integration.market_intelligence_aggregator import (
    MarketIntelligenceAggregator,
)
from iios.investment.market.integration.models import (
    EnginePayload,
    EngineSource,
    IntelligenceBundle,
)


class TestAggregationEngine:
    def test_aggregate_full_bundle(self, full_bundle):
        engine = AggregationEngine()
        state  = engine.aggregate(full_bundle)
        assert isinstance(state, AggregationState)
        assert state.market_regime == "bull"
        assert state.trend_direction == "up"
        assert state.trend_strength == pytest.approx(70.0)

    def test_aggregate_extracts_volatility(self, full_bundle):
        engine = AggregationEngine()
        state  = engine.aggregate(full_bundle)
        assert state.volatility_regime == "normal"
        assert state.volatility_percentile == pytest.approx(40.0)
        assert state.vix_equivalent == pytest.approx(18.0)

    def test_aggregate_extracts_breadth(self, full_bundle):
        engine = AggregationEngine()
        state  = engine.aggregate(full_bundle)
        assert state.breadth_regime == "positive"
        assert state.breadth_score == pytest.approx(65.0)

    def test_aggregate_extracts_correlation(self, full_bundle):
        engine = AggregationEngine()
        state  = engine.aggregate(full_bundle)
        assert state.correlation_regime == "normal"
        assert state.avg_correlation == pytest.approx(0.3)

    def test_aggregate_extracts_liquidity(self, full_bundle):
        engine = AggregationEngine()
        state  = engine.aggregate(full_bundle)
        assert state.liquidity_regime == "normal"
        assert state.liquidity_score == pytest.approx(65.0)

    def test_aggregate_extracts_sector_rotation(self, full_bundle):
        engine = AggregationEngine()
        state  = engine.aggregate(full_bundle)
        assert state.sector_rotation_phase == "expansion"
        assert "IT" in state.leading_sectors

    def test_aggregate_extracts_opportunities(self, full_bundle):
        engine = AggregationEngine()
        state  = engine.aggregate(full_bundle)
        assert state.active_opportunities == 5
        assert "AAPL" in state.top_opportunity_symbols

    def test_aggregate_tracks_received_engines(self, full_bundle):
        engine = AggregationEngine()
        state  = engine.aggregate(full_bundle)
        assert "market_regime" in state.engines_received
        assert "trend"         in state.engines_received

    def test_aggregate_empty_bundle(self, empty_bundle):
        engine = AggregationEngine()
        state  = engine.aggregate(empty_bundle)
        assert state.market_regime is None
        assert len(state.engines_received) == 0

    def test_aggregate_partial_bundle(self):
        bundle = IntelligenceBundle(2, 2.0)
        bundle.add(EnginePayload("market_regime", EngineSource.MARKET_REGIME,
                                  {"regime": "neutral"}, 2, 2.0))
        engine = AggregationEngine()
        state  = engine.aggregate(bundle)
        assert state.market_regime == "neutral"
        assert state.trend_direction is None

    def test_aggregate_resilient_to_bad_payload(self):
        bundle = IntelligenceBundle(3, 3.0)
        bundle.add(EnginePayload("market_regime", EngineSource.MARKET_REGIME,
                                  None, 3, 3.0))
        engine = AggregationEngine()
        state  = engine.aggregate(bundle)
        # Should not raise; market_regime stays None
        assert state.market_regime is None

    def test_aggregate_object_payload(self):
        class FakeTrend:
            trend_direction = "down"
            trend_strength  = 80.0
            trend_stage     = "late"
        bundle = IntelligenceBundle(1, 1.0)
        bundle.add(EnginePayload("trend", EngineSource.TREND, FakeTrend(), 1, 1.0))
        engine = AggregationEngine()
        state  = engine.aggregate(bundle)
        assert state.trend_direction == "down"
        assert state.trend_strength  == pytest.approx(80.0)

    def test_aggregate_missing_engines_detected(self):
        bundle = IntelligenceBundle(1, 1.0)
        bundle.add(EnginePayload("market_regime", EngineSource.MARKET_REGIME,
                                  {"regime": "bull"}, 1, 1.0))
        engine = AggregationEngine()
        state  = engine.aggregate(bundle)
        assert len(state.missing_engines) >= 7   # 8 known - 1 received

    def test_coverage_ratio(self, full_bundle):
        engine = AggregationEngine()
        state  = engine.aggregate(full_bundle)
        ratio  = state.coverage_ratio(8)
        assert ratio == pytest.approx(8.0 / 8.0, abs=0.01)


class TestAggregationHistory:
    def test_append_and_latest(self, full_bundle):
        engine  = AggregationEngine()
        history = AggregationHistory()
        state   = engine.aggregate(full_bundle)
        history.append(state)
        assert history.latest() is state

    def test_recent(self, make_bundle):
        engine  = AggregationEngine()
        history = AggregationHistory()
        for i in range(1, 6):
            state = engine.aggregate(make_bundle(bar_index=i))
            history.append(state)
        assert len(history.recent(3)) == 3
        assert len(history.recent(10)) == 5

    def test_trend_strength_series(self, make_bundle):
        engine  = AggregationEngine()
        history = AggregationHistory()
        for i in range(1, 4):
            state = engine.aggregate(make_bundle(bar_index=i, trend_strength=float(60 + i)))
            history.append(state)
        series = history.trend_strength_series(3)
        assert len(series) == 3

    def test_maxlen_respected(self, full_bundle):
        engine  = AggregationEngine()
        history = AggregationHistory(maxlen=3)
        for _ in range(5):
            history.append(engine.aggregate(full_bundle))
        assert len(history) <= 3


class TestMarketIntelligenceAggregator:
    def test_aggregate_returns_state(self, full_bundle):
        aggregator = MarketIntelligenceAggregator()
        state      = aggregator.aggregate(full_bundle)
        assert isinstance(state, AggregationState)

    def test_history_grows(self, make_bundle):
        aggregator = MarketIntelligenceAggregator()
        for i in range(1, 4):
            aggregator.aggregate(make_bundle(bar_index=i))
        assert len(aggregator.history) == 3

    def test_latest_state(self, make_bundle):
        aggregator = MarketIntelligenceAggregator()
        aggregator.aggregate(make_bundle(bar_index=1))
        last = aggregator.aggregate(make_bundle(bar_index=2))
        assert aggregator.latest_state() is last
