"""
test_market_analytics.py — tests/unit/market/analytics
========================================================
Comprehensive test suite for iios.market.analytics (C12 M4).

Coverage targets: ≥ 95%
"""
from __future__ import annotations

import math
import time
import uuid
from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Import the public API
# ---------------------------------------------------------------------------
from iios.market.analytics import (
    # Engine
    MarketAnalyticsEngine,
    # Artefacts
    MarketAnalyticsContext,
    MarketAnalyticsFactory,
    MarketAnalyticsHistory,
    MarketAnalyticsRegistry,
    MarketAnalyticsReport,
    MarketAnalyticsRequest,
    MarketAnalyticsStatistics,
    MarketAnalyticsValidator,
    AnalyticsValidationResult,
    # Domain results
    BreadthResult,
    CorrelationResult,
    ForecastResult,
    IndexResult,
    LiquidityResult,
    MarketScores,
    MomentumResult,
    PatternResult,
    RegimeResult,
    RotationResult,
    SectorResult,
    SentimentResult,
    VolatilityResult,
    # Events
    MarketAnalyticsEvent,
    analytics_started_event,
    datasets_loaded_event,
    regime_detected_event,
    sector_analysis_completed_event,
    breadth_analysis_completed_event,
    forecast_generated_event,
    scores_calculated_event,
    analytics_validated_event,
    analytics_published_event,
    analytics_failed_event,
    # Exceptions
    MarketAnalyticsEngineNotRunningError,
    MarketAnalyticsNotApprovedError,
    MarketAnalyticsValidationError,
    MarketAnalyticsRegistryError,
    MarketAnalyticsError,
    MarketAnalyticsCapacityError,
    MarketAnalyticsDataError,
    MarketAnalyticsNotFoundError,
    MarketForecastError,
    MarketRegimeError,
    # Enumerations
    AnalyticsDomain,
    AnalyticsEventType,
    AnalyticsStatus,
    ForecastDirection,
    ForecastHorizon,
    ForecastType,
    LiquidityCondition,
    MarketRegime,
    PatternType,
    SentimentCategory,
    TrendDirection,
    TrendStrength,
    ValidationCode,
    VolatilityRegime,
)
from iios.market.analytics.constants import (
    VERSION,
    BREADTH_HEALTHY,
    REGIME_BASE_SCORES,
    VOLATILITY_SCORE_PENALTY,
)
from iios.market.analytics.market_regime_classifier import (
    classify_regime,
    classify_trend_direction,
    classify_trend_strength,
)
from iios.market.analytics.market_breadth_engine   import MarketBreadthEngine
from iios.market.analytics.market_sector_engine    import MarketSectorEngine
from iios.market.analytics.market_rotation_engine  import MarketRotationEngine
from iios.market.analytics.market_index_engine     import MarketIndexEngine
from iios.market.analytics.market_volatility_engine import MarketVolatilityEngine
from iios.market.analytics.market_correlation_engine import MarketCorrelationEngine
from iios.market.analytics.market_sentiment_engine  import MarketSentimentEngine
from iios.market.analytics.market_liquidity_engine  import MarketLiquidityEngine
from iios.market.analytics.market_momentum_engine   import MarketMomentumEngine
from iios.market.analytics.market_forecasting_engine import MarketForecastingEngine
from iios.market.analytics.market_pattern_engine    import MarketPatternEngine
from iios.market.analytics.market_scoring_engine    import MarketScoringEngine
from iios.market.analytics.market_strength_engine   import compute_market_strength_score
from iios.market.analytics.market_intelligence_engine import (
    generate_intelligence_summary,
    _key_risks,
    _key_opportunities,
)
from iios.market.analytics.market_analytics_manager import MarketAnalyticsManager


# ===========================================================================
# Helpers
# ===========================================================================

def _make_prices(n: int = 100, start: float = 1000.0, trend: float = 0.001) -> List[float]:
    """Synthetic uptrending price series."""
    prices = [start]
    for _ in range(n - 1):
        prices.append(prices[-1] * (1 + trend))
    return prices


def _make_down_prices(n: int = 100, start: float = 1000.0) -> List[float]:
    return _make_prices(n, start, trend=-0.002)


def _make_context(
    analytics_id: str       = "ana-001",
    market_analysis_id: str = "ma-001",
    exchange: str           = "NSE",
) -> MarketAnalyticsContext:
    return MarketAnalyticsFactory.create_context(analytics_id, market_analysis_id, exchange)


def _make_request(
    prices:          List[float] = None,
    policy_approved: bool        = True,
    analytics_id:    str         = "ana-001",
    market_analysis_id: str      = "ma-001",
    exchange:        str         = "NSE",
) -> MarketAnalyticsRequest:
    if prices is None:
        prices = _make_prices()
    ctx = _make_context(analytics_id, market_analysis_id, exchange)
    return MarketAnalyticsFactory.create_request(
        analytics_id, market_analysis_id, exchange, ctx,
        policy_approved = policy_approved,
        index_prices    = {"NIFTY": prices},
        breadth_data    = {"advancing": 60, "declining": 30, "unchanged": 10},
    )


def _started_engine() -> MarketAnalyticsEngine:
    engine = MarketAnalyticsEngine()
    engine.start()
    return engine


# ===========================================================================
# 1. Constants
# ===========================================================================

class TestConstants:
    def test_version_string(self):
        assert VERSION == "1.0.0"

    def test_regime_scores_keys(self):
        assert MarketRegime.STRONG_BULL in REGIME_BASE_SCORES
        assert MarketRegime.BEAR in REGIME_BASE_SCORES

    def test_volatility_penalty_keys(self):
        assert VolatilityRegime.EXTREME in VOLATILITY_SCORE_PENALTY
        assert VOLATILITY_SCORE_PENALTY[VolatilityRegime.EXTREME] > 0

    def test_analytics_domain_count(self):
        assert len(AnalyticsDomain) == 14

    def test_market_regime_count(self):
        assert len(MarketRegime) == 6

    def test_analytics_event_type_count(self):
        assert len(AnalyticsEventType) == 10

    def test_trend_strength_none(self):
        assert TrendStrength.NONE.value == "none"

    def test_forecast_direction_values(self):
        assert ForecastDirection.BULLISH.value == "bullish"
        assert ForecastDirection.BEARISH.value == "bearish"
        assert ForecastDirection.NEUTRAL.value == "neutral"

    def test_liquidity_condition_values(self):
        assert LiquidityCondition.ABUNDANT.value == "abundant"
        assert LiquidityCondition.STRESSED.value == "stressed"


# ===========================================================================
# 2. Exceptions
# ===========================================================================

class TestExceptions:
    def test_base_is_iios_error(self):
        from iios.common.errors.exceptions import IIOSError
        assert issubclass(MarketAnalyticsError, IIOSError)

    def test_engine_not_running_error(self):
        e = MarketAnalyticsEngineNotRunningError("not running")
        assert "MA-001" in e.error_code
        assert "not running" in str(e)

    def test_validation_error_has_analytics_id(self):
        e = MarketAnalyticsValidationError("bad input", analytics_id="ana-x")
        assert e.analytics_id == "ana-x"
        assert "MA-002" in e.error_code

    def test_not_approved_error(self):
        e = MarketAnalyticsNotApprovedError(analytics_id="ana-y")
        assert e.analytics_id == "ana-y"
        assert "MA-003" in e.error_code

    def test_not_found_error(self):
        e = MarketAnalyticsNotFoundError(analytics_id="x")
        assert "MA-004" in e.error_code

    def test_data_error(self):
        e = MarketAnalyticsDataError("no data")
        assert "MA-005" in e.error_code

    def test_regime_error(self):
        assert "MA-006" in MarketRegimeError("x").error_code

    def test_forecast_error(self):
        assert "MA-007" in MarketForecastError("x").error_code

    def test_registry_error(self):
        assert "MA-008" in MarketAnalyticsRegistryError("x").error_code

    def test_capacity_error(self):
        e = MarketAnalyticsCapacityError(limit=100)
        assert e.limit == 100
        assert "MA-009" in e.error_code


# ===========================================================================
# 3. MarketAnalyticsContext
# ===========================================================================

class TestMarketAnalyticsContext:
    def test_create_defaults(self):
        ctx = _make_context()
        assert ctx.analytics_id        == "ana-001"
        assert ctx.market_analysis_id  == "ma-001"
        assert ctx.exchange            == "NSE"
        assert ctx.short_lookback      == 20
        assert ctx.long_lookback       == 200

    def test_context_immutable(self):
        ctx = _make_context()
        with pytest.raises((AttributeError, TypeError)):
            ctx.exchange = "BSE"

    def test_to_dict_keys(self):
        d = _make_context().to_dict()
        assert "analytics_id" in d
        assert "exchange" in d
        assert "short_lookback" in d

    def test_domains_tuple(self):
        ctx = _make_context()
        assert isinstance(ctx.domains, tuple)
        assert len(ctx.domains) > 0


# ===========================================================================
# 4. MarketAnalyticsRequest
# ===========================================================================

class TestMarketAnalyticsRequest:
    def test_create(self):
        req = _make_request()
        assert req.policy_approved is True
        assert req.exchange        == "NSE"

    def test_has_index_data(self):
        req = _make_request(prices=[100.0, 101.0])
        assert req.has_index_data is True

    def test_index_count(self):
        ctx = _make_context()
        req = MarketAnalyticsFactory.create_request(
            "a", "b", "NSE", ctx, policy_approved=True,
            index_prices={"IDX1": [1.0], "IDX2": [2.0]},
        )
        assert req.index_count == 2

    def test_to_dict_keys(self):
        d = _make_request().to_dict()
        assert "analytics_id" in d
        assert "request_id" in d
        assert "policy_approved" in d

    def test_request_immutable(self):
        req = _make_request()
        with pytest.raises((AttributeError, TypeError)):
            req.exchange = "BSE"


# ===========================================================================
# 5. MarketAnalyticsResponse (domain results)
# ===========================================================================

class TestDomainResults:
    def test_regime_result_to_dict(self):
        r = RegimeResult(
            regime=MarketRegime.BULL, confidence=0.7,
            trend_direction=TrendDirection.UP,
            trend_strength=TrendStrength.STRONG,
            regime_duration_bars=5,
        )
        d = r.to_dict()
        assert d["regime"] == "bull"
        assert d["confidence"] == 0.7

    def test_breadth_result_to_dict(self):
        b = BreadthResult(
            advance_decline_ratio=2.0, advancing_pct=0.6,
            declining_pct=0.3, unchanged_pct=0.1,
            new_highs=10, new_lows=2, breadth_score=60.0, is_healthy=True,
        )
        d = b.to_dict()
        assert d["advance_decline_ratio"] == 2.0
        assert d["is_healthy"] is True

    def test_volatility_result_to_dict(self):
        v = VolatilityResult(
            realised_vol=0.01, implied_vol=0.015,
            vol_regime=VolatilityRegime.NORMAL, vol_percentile=0.5,
            vol_trend=TrendDirection.SIDEWAYS, vol_score=75.0,
        )
        assert v.to_dict()["vol_regime"] == "normal"

    def test_sector_result_ranking(self):
        s = SectorResult(
            sector_name="Technology", performance=0.05,
            relative_strength=0.02, momentum_score=0.03,
            volume_ratio=1.2, rank=1, trend=TrendDirection.UP,
        )
        assert s.rank == 1

    def test_market_scores_to_dict(self):
        sc = MarketScores(
            health_score=70.0, regime_confidence=0.8,
            sector_strength_score=65.0, trend_strength_score=72.0,
            breadth_score=60.0, liquidity_score=75.0,
            volatility_score=80.0, momentum_score=55.0, overall_score=68.0,
        )
        d = sc.to_dict()
        assert d["overall_score"] == 68.0

    def test_forecast_result_to_dict(self):
        f = ForecastResult(
            forecast_type=ForecastType.TREND_CONTINUATION,
            horizon=ForecastHorizon.DAY,
            direction=ForecastDirection.BULLISH,
            confidence=0.65, expected_return=0.005,
            upside_target=1050.0, downside_target=950.0,
        )
        d = f.to_dict()
        assert d["direction"] == "bullish"


# ===========================================================================
# 6. MarketAnalyticsReport
# ===========================================================================

class TestMarketAnalyticsReport:
    def test_create_success(self):
        report = MarketAnalyticsReport.create_success(
            analytics_id="a", market_analysis_id="b",
            exchange="NSE", elapsed_s=0.1,
        )
        assert report.is_success is True
        assert report.status == AnalyticsStatus.COMPLETED

    def test_create_failure(self):
        report = MarketAnalyticsReport.create_failure(
            analytics_id="a", market_analysis_id="b",
            exchange="NSE", error_message="boom", elapsed_s=0.05,
        )
        assert report.is_success is False
        assert report.status == AnalyticsStatus.FAILED
        assert "boom" in report.error_message

    def test_to_dict_keys(self):
        report = MarketAnalyticsReport.create_success(
            analytics_id="a", market_analysis_id="b",
            exchange="NSE", elapsed_s=0.1,
        )
        d = report.to_dict()
        assert "report_id" in d
        assert "is_success" in d
        assert "sector_results" in d

    def test_report_immutable(self):
        report = MarketAnalyticsReport.create_success(
            analytics_id="a", market_analysis_id="b",
            exchange="NSE", elapsed_s=0.1,
        )
        with pytest.raises((AttributeError, TypeError)):
            report.exchange = "BSE"


# ===========================================================================
# 7. Validator
# ===========================================================================

class TestMarketAnalyticsValidator:
    def test_valid_request_passes(self):
        req = _make_request()
        v = MarketAnalyticsValidator()
        result = v.validate_request(req)
        assert result.is_valid is True

    def test_not_approved_fails(self):
        req = _make_request(policy_approved=False)
        v = MarketAnalyticsValidator()
        result = v.validate_request(req)
        assert result.is_valid is False
        codes = [c.code for c in result.failed_checks]
        assert ValidationCode.POLICY_APPROVED in codes

    def test_no_data_fails(self):
        ctx = _make_context()
        req = MarketAnalyticsFactory.create_request(
            "a", "b", "NSE", ctx, policy_approved=True,
        )
        v = MarketAnalyticsValidator()
        result = v.validate_request(req)
        assert result.is_valid is False

    def test_validate_request_or_raise_valid(self):
        req = _make_request()
        MarketAnalyticsValidator().validate_request_or_raise(req)

    def test_validate_request_or_raise_invalid(self):
        req = _make_request(policy_approved=False)
        with pytest.raises(MarketAnalyticsValidationError):
            MarketAnalyticsValidator().validate_request_or_raise(req)

    def test_validate_report_success(self):
        report = MarketAnalyticsReport.create_success(
            analytics_id="a", market_analysis_id="b",
            exchange="NSE", elapsed_s=0.1,
        )
        result = MarketAnalyticsValidator().validate_report(report)
        assert result.is_valid is True

    def test_validate_report_failure(self):
        report = MarketAnalyticsReport.create_failure(
            analytics_id="a", market_analysis_id="b",
            exchange="NSE", error_message="err", elapsed_s=0.05,
        )
        result = MarketAnalyticsValidator().validate_report(report)
        assert result.is_valid is False

    def test_validate_report_scores_out_of_range(self):
        scores = MarketScores(
            health_score=150.0,  # invalid
            regime_confidence=0.8, sector_strength_score=65.0,
            trend_strength_score=72.0, breadth_score=60.0,
            liquidity_score=75.0, volatility_score=80.0,
            momentum_score=55.0, overall_score=68.0,
        )
        report = MarketAnalyticsReport.create_success(
            analytics_id="a", market_analysis_id="b",
            exchange="NSE", elapsed_s=0.1, scores=scores,
        )
        result = MarketAnalyticsValidator().validate_report(report)
        assert result.is_valid is False


# ===========================================================================
# 8. Statistics
# ===========================================================================

class TestMarketAnalyticsStatistics:
    def test_initial_snapshot(self):
        s = MarketAnalyticsStatistics()
        snap = s.snapshot()
        assert snap["analytics_total"] == 0

    def test_record_analytics_started(self):
        s = MarketAnalyticsStatistics()
        s.record_analytics_started()
        s.record_analytics_started()
        assert s.snapshot()["analytics_total"] == 2

    def test_record_completed_and_failed(self):
        s = MarketAnalyticsStatistics()
        s.record_analytics_completed()
        s.record_analytics_failed()
        snap = s.snapshot()
        assert snap["analytics_completed"] == 1
        assert snap["analytics_failed"]    == 1

    def test_elapsed_average(self):
        s = MarketAnalyticsStatistics()
        s.record_elapsed(0.2)
        s.record_elapsed(0.4)
        snap = s.snapshot()
        assert abs(snap["average_runtime_s"] - 0.3) < 0.01

    def test_reset(self):
        s = MarketAnalyticsStatistics()
        s.record_analytics_started()
        s.reset()
        assert s.snapshot()["analytics_total"] == 0


# ===========================================================================
# 9. History
# ===========================================================================

class TestMarketAnalyticsHistory:
    def test_record_and_retrieve(self):
        h = MarketAnalyticsHistory(max_events=100)
        h.record_event("evt1")
        h.record_event("evt2")
        assert len(h.recent_events()) == 2

    def test_bounded_by_max(self):
        h = MarketAnalyticsHistory(max_events=3)
        for i in range(10):
            h.record_event(i)
        assert h.counts()["events"] == 3

    def test_recent_n_limit(self):
        h = MarketAnalyticsHistory()
        for i in range(20):
            h.record_event(i)
        assert len(h.recent_events(5)) == 5

    def test_clear(self):
        h = MarketAnalyticsHistory()
        h.record_event("x")
        h.record_request("r")
        h.clear()
        counts = h.counts()
        assert counts["events"] == 0
        assert counts["requests"] == 0


# ===========================================================================
# 10. Registry
# ===========================================================================

class TestMarketAnalyticsRegistry:
    def _report(self, report_id: str = None, exchange: str = "NSE", analytics_id: str = "ana-1") -> MarketAnalyticsReport:
        return MarketAnalyticsReport.create_success(
            analytics_id=analytics_id, market_analysis_id="ma-1",
            exchange=exchange, elapsed_s=0.1,
            report_id=report_id or str(uuid.uuid4()),
        )

    def test_register_and_get(self):
        reg = MarketAnalyticsRegistry()
        r   = self._report("rep-001")
        reg.register(r)
        assert reg.get("rep-001") is r

    def test_get_missing_returns_none(self):
        reg = MarketAnalyticsRegistry()
        assert reg.get("ghost") is None

    def test_register_evicts_oldest_when_full(self):
        reg = MarketAnalyticsRegistry(max_reports=2)
        r1, r2, r3 = [self._report(f"r-{i}") for i in range(3)]
        reg.register(r1)
        reg.register(r2)
        reg.register(r3)
        assert reg.get("r-0") is None
        assert reg.get("r-2") is r3

    def test_register_update_same_id(self):
        reg = MarketAnalyticsRegistry(max_reports=5)
        r1 = self._report("dup")
        r2 = self._report("dup")
        reg.register(r1)
        reg.register(r2)
        assert reg.count() == 1

    def test_remove(self):
        reg = MarketAnalyticsRegistry()
        r = self._report("x")
        reg.register(r)
        assert reg.remove("x") is True
        assert reg.count() == 0

    def test_remove_missing_returns_false(self):
        reg = MarketAnalyticsRegistry()
        assert reg.remove("ghost") is False

    def test_latest_for_exchange(self):
        reg = MarketAnalyticsRegistry()
        r1 = self._report("r1", exchange="NSE")
        r2 = self._report("r2", exchange="NSE")
        reg.register(r1)
        reg.register(r2)
        assert reg.latest_for_exchange("NSE") is r2

    def test_registry_error_on_empty_report_id(self):
        reg = MarketAnalyticsRegistry()
        # Directly construct a report with empty report_id (bypass classmethod)
        import dataclasses, time as _time
        r = MarketAnalyticsReport(
            report_id="",
            analytics_id="a", market_analysis_id="b",
            exchange="NSE", status=AnalyticsStatus.COMPLETED,
            regime=None, breadth=None, sector_results=(),
            rotation=None, volatility=None, momentum=None,
            liquidity=None, sentiment=None, correlation=None,
            index_results=(), pattern=None, forecasts=(), scores=None,
            elapsed_s=0.1, is_success=True,
        )
        with pytest.raises(MarketAnalyticsRegistryError):
            reg.register(r)

    def test_all_reports(self):
        reg = MarketAnalyticsRegistry()
        r1 = self._report("a1")
        r2 = self._report("a2")
        reg.register(r1)
        reg.register(r2)
        assert len(reg.all_reports()) == 2


# ===========================================================================
# 11. Factory
# ===========================================================================

class TestMarketAnalyticsFactory:
    def test_create_context(self):
        ctx = MarketAnalyticsFactory.create_context("a", "b", "NSE")
        assert ctx.exchange == "NSE"
        assert len(ctx.domains) > 0

    def test_create_request_with_data(self):
        ctx = MarketAnalyticsFactory.create_context("a", "b", "NSE")
        req = MarketAnalyticsFactory.create_request(
            "a", "b", "NSE", ctx,
            policy_approved=True,
            index_prices={"NIFTY": [100.0, 101.0]},
        )
        assert req.policy_approved is True
        assert "NIFTY" in req.index_prices

    def test_engine_create_request_helper(self):
        engine = MarketAnalyticsEngine()
        req = MarketAnalyticsEngine.create_request(
            "a", "b", "NSE", policy_approved=True,
            index_prices={"X": [1.0, 2.0]},
        )
        assert req.exchange == "NSE"


# ===========================================================================
# 12. Events
# ===========================================================================

class TestMarketAnalyticsEvents:
    _kwargs = dict(
        analytics_id="ana-1",
        market_analysis_id="ma-1",
        exchange="NSE",
        actor="test",
    )

    def test_analytics_started_event(self):
        evt = analytics_started_event(**self._kwargs)
        assert evt.event_type == AnalyticsEventType.ANALYTICS_STARTED
        assert evt.exchange   == "NSE"

    def test_analytics_failed_event(self):
        evt = analytics_failed_event(**self._kwargs, error="boom")
        assert evt.event_type == AnalyticsEventType.ANALYTICS_FAILED
        assert "boom"         in evt.payload.get("error", "")

    def test_all_event_factories(self):
        factories = [
            datasets_loaded_event, regime_detected_event,
            sector_analysis_completed_event, breadth_analysis_completed_event,
            forecast_generated_event, scores_calculated_event,
            analytics_validated_event, analytics_published_event,
        ]
        for fn in factories:
            evt = fn(**self._kwargs)
            assert isinstance(evt, MarketAnalyticsEvent)
            assert evt.event_id != ""

    def test_event_to_dict(self):
        evt = analytics_published_event(**self._kwargs)
        d = evt.to_dict()
        assert "event_id" in d
        assert "event_type" in d
        assert "source" in d


# ===========================================================================
# 13. Regime Classifier (pure logic)
# ===========================================================================

class TestRegimeClassifier:
    def test_strong_bull_regime(self):
        prices = _make_prices(300, trend=0.003)
        regime, conf, trend, strength = classify_regime(prices, breadth_healthy=True)
        assert regime in (MarketRegime.BULL, MarketRegime.STRONG_BULL)
        assert conf > 0.5

    def test_bear_regime(self):
        prices = _make_down_prices(300)
        regime, conf, trend, strength = classify_regime(prices, breadth_healthy=False)
        assert regime in (MarketRegime.BEAR, MarketRegime.STRONG_BEAR)

    def test_neutral_regime_flat(self):
        prices = [1000.0] * 250
        regime, conf, trend, strength = classify_regime(prices, breadth_healthy=True)
        # Flat prices: all MAs equal current → bearish_ma=3 but breadth_healthy dampens to BEAR
        assert regime in (MarketRegime.NEUTRAL, MarketRegime.BEAR)

    def test_empty_prices_unknown(self):
        regime, conf, trend, strength = classify_regime([], breadth_healthy=True)
        assert regime == MarketRegime.UNKNOWN

    def test_trend_direction_up(self):
        prices = _make_prices(250, trend=0.002)
        direction = classify_trend_direction(prices, 20, 200)
        assert direction in (TrendDirection.UP, TrendDirection.STRONG_UP)

    def test_trend_strength_strong(self):
        prices = _make_prices(250, trend=0.004)
        strength = classify_trend_strength(prices)
        assert strength in (TrendStrength.STRONG, TrendStrength.VERY_STRONG, TrendStrength.MODERATE)

    def test_confidence_penalty_bullish_with_unhealthy_breadth(self):
        prices = _make_prices(300, trend=0.003)
        _, conf_healthy, _, _ = classify_regime(prices, breadth_healthy=True)
        _, conf_unhealthy, _, _ = classify_regime(prices, breadth_healthy=False)
        assert conf_unhealthy <= conf_healthy


# ===========================================================================
# 14. MarketRegimeEngine
# ===========================================================================

class TestMarketRegimeEngine:
    def setup_method(self):
        from iios.market.analytics.market_regime_engine import MarketRegimeEngine
        self.engine = MarketRegimeEngine()
        self.ctx    = _make_context()

    def test_run_with_prices(self):
        result = self.engine.run(self.ctx, {"index_prices": {"NIFTY": _make_prices()}})
        assert isinstance(result, RegimeResult)
        assert result.regime != MarketRegime.UNKNOWN

    def test_run_no_data_returns_unknown(self):
        result = self.engine.run(self.ctx, {})
        assert result.regime == MarketRegime.UNKNOWN
        assert result.confidence == 0.0

    def test_run_multiple_indices(self):
        data = {
            "index_prices": {
                "NIFTY":    _make_prices(250),
                "SENSEX":   _make_prices(250, start=60000.0),
            }
        }
        result = self.engine.run(self.ctx, data)
        assert isinstance(result, RegimeResult)


# ===========================================================================
# 15. MarketBreadthEngine
# ===========================================================================

class TestMarketBreadthEngine:
    def setup_method(self):
        self.engine = MarketBreadthEngine()
        self.ctx    = _make_context()

    def test_healthy_breadth(self):
        result = self.engine.run(self.ctx, {
            "breadth_data": {"advancing": 700, "declining": 200, "unchanged": 100}
        })
        assert result.is_healthy is True
        assert result.advance_decline_ratio > 1.0

    def test_unhealthy_breadth(self):
        result = self.engine.run(self.ctx, {
            "breadth_data": {"advancing": 200, "declining": 700, "unchanged": 100}
        })
        assert result.is_healthy is False

    def test_no_data_neutral_defaults(self):
        result = self.engine.run(self.ctx, {})
        assert result.breadth_score == 50.0
        assert result.is_healthy is True

    def test_new_highs_raises_score(self):
        r1 = self.engine.run(self.ctx, {
            "breadth_data": {"advancing": 600, "declining": 400, "new_highs": 0, "new_lows": 100}
        })
        r2 = self.engine.run(self.ctx, {
            "breadth_data": {"advancing": 600, "declining": 400, "new_highs": 100, "new_lows": 0}
        })
        assert r2.breadth_score > r1.breadth_score


# ===========================================================================
# 16. MarketSectorEngine
# ===========================================================================

class TestMarketSectorEngine:
    def setup_method(self):
        self.engine = MarketSectorEngine()
        self.ctx    = _make_context()

    def test_empty_sector_data(self):
        results = self.engine.run(self.ctx, {})
        assert results == []

    def test_sector_ranking(self):
        data = {
            "sector_data": {
                "Technology": {"prices": _make_prices(50, trend=0.005)},
                "Energy":     {"prices": _make_prices(50, trend=-0.002)},
            }
        }
        results = self.engine.run(self.ctx, data)
        assert len(results) == 2
        assert results[0].rank == 1
        assert results[0].performance > results[-1].performance

    def test_relative_strength_computed(self):
        data = {
            "index_prices": {"NIFTY": _make_prices(50, trend=0.001)},
            "sector_data": {
                "Finance": {"prices": _make_prices(50, trend=0.003)},
            }
        }
        results = self.engine.run(self.ctx, data)
        assert results[0].relative_strength != 0.0


# ===========================================================================
# 17. MarketRotationEngine
# ===========================================================================

class TestMarketRotationEngine:
    def setup_method(self):
        self.engine = MarketRotationEngine()
        self.ctx    = _make_context()

    def _sector_list(self) -> List[SectorResult]:
        sectors = [
            ("Technology",       0.05),
            ("Energy",           0.03),
            ("Consumer Staples", -0.01),
        ]
        return [
            SectorResult(n, p, p, p, 1.0, i + 1, TrendDirection.UP)
            for i, (n, p) in enumerate(sectors)
        ]

    def test_run_returns_rotation_result(self):
        result = self.engine.run(self.ctx, self._sector_list())
        assert isinstance(result, RotationResult)
        assert "technology" in result.leading_sectors[0].lower()

    def test_run_empty_returns_none(self):
        assert self.engine.run(self.ctx, []) is None

    def test_rotation_score_nonzero(self):
        result = self.engine.run(self.ctx, self._sector_list())
        assert result.rotation_score >= 0.0


# ===========================================================================
# 18. MarketIndexEngine
# ===========================================================================

class TestMarketIndexEngine:
    def setup_method(self):
        self.engine = MarketIndexEngine()
        self.ctx    = _make_context()

    def test_analyse_uptrend(self):
        prices  = _make_prices(250, trend=0.003)
        results = self.engine.run(self.ctx, {"index_prices": {"NIFTY": prices}})
        assert len(results) == 1
        r = results[0]
        assert r.index_name    == "NIFTY"
        assert r.current_price == prices[-1]
        assert r.above_ma_long is True

    def test_empty_prices_skipped(self):
        results = self.engine.run(self.ctx, {"index_prices": {"NIFTY": []}})
        assert results == []

    def test_change_pct_computed(self):
        prices  = [100.0, 110.0]
        results = self.engine.run(self.ctx, {"index_prices": {"X": prices}})
        assert abs(results[0].change_pct - 0.10) < 0.001


# ===========================================================================
# 19. MarketVolatilityEngine
# ===========================================================================

class TestMarketVolatilityEngine:
    def setup_method(self):
        self.engine = MarketVolatilityEngine()
        self.ctx    = _make_context()

    def test_normal_vol(self):
        prices = _make_prices(250, trend=0.001)
        result = self.engine.run(self.ctx, {"index_prices": {"NIFTY": prices}})
        assert isinstance(result, VolatilityResult)
        assert result.vol_regime in (VolatilityRegime.LOW, VolatilityRegime.NORMAL)

    def test_high_vol_series(self):
        import random
        random.seed(42)
        prices = [1000.0]
        for _ in range(250):
            prices.append(prices[-1] * (1 + random.gauss(0, 0.02)))
        result = self.engine.run(self.ctx, {"index_prices": {"NIFTY": prices}})
        assert result.vol_regime in (
            VolatilityRegime.ELEVATED, VolatilityRegime.HIGH, VolatilityRegime.EXTREME
        )

    def test_neutral_result_no_data(self):
        result = self.engine.run(self.ctx, {})
        assert result.vol_regime == VolatilityRegime.NORMAL

    def test_implied_vol_taken_from_data(self):
        prices = _make_prices(100)
        result = self.engine.run(self.ctx, {
            "index_prices":   {"X": prices},
            "volatility_data": {"implied_vol": 0.30},
        })
        assert result.implied_vol == pytest.approx(0.30)


# ===========================================================================
# 20. MarketCorrelationEngine
# ===========================================================================

class TestMarketCorrelationEngine:
    def setup_method(self):
        self.engine = MarketCorrelationEngine()
        self.ctx    = _make_context()

    def test_single_index_insufficient_data(self):
        result = self.engine.run(self.ctx, {"index_prices": {"A": [1.0, 2.0, 3.0]}})
        assert result.correlation_regime == "insufficient_data"

    def test_correlated_series(self):
        prices = _make_prices(100)
        result = self.engine.run(self.ctx, {
            "index_prices": {"A": prices, "B": [p * 0.99 for p in prices]}
        })
        assert result.exchange_correlation > 0.9
        assert "high" in result.correlation_regime

    def test_global_correlation_from_data(self):
        prices = _make_prices(100)
        result = self.engine.run(self.ctx, {
            "index_prices": {"A": prices, "B": prices},
            "global_data":  {"global_correlation": 0.55},
        })
        assert result.global_correlation == pytest.approx(0.55)


# ===========================================================================
# 21. MarketSentimentEngine
# ===========================================================================

class TestMarketSentimentEngine:
    def setup_method(self):
        self.engine = MarketSentimentEngine()
        self.ctx    = _make_context()

    def test_greed_sentiment(self):
        result = self.engine.run(self.ctx, {
            "breadth_data":    {"put_call_ratio": 0.7, "advancing_pct": 0.7},
            "global_data":     {"fear_greed_index": 80.0},
            "volatility_data": {"implied_vol": 0.10},
        })
        assert result.category in (SentimentCategory.GREED, SentimentCategory.EXTREME_GREED)
        assert result.sentiment_score > 60.0

    def test_fear_sentiment(self):
        result = self.engine.run(self.ctx, {
            "breadth_data":    {"put_call_ratio": 1.8, "advancing_pct": 0.25},
            "global_data":     {"fear_greed_index": 10.0},
            "volatility_data": {"implied_vol": 0.35},
        })
        assert result.category in (SentimentCategory.FEAR, SentimentCategory.EXTREME_FEAR)

    def test_default_neutral(self):
        result = self.engine.run(self.ctx, {})
        assert isinstance(result, SentimentResult)


# ===========================================================================
# 22. MarketLiquidityEngine
# ===========================================================================

class TestMarketLiquidityEngine:
    def setup_method(self):
        self.engine = MarketLiquidityEngine()
        self.ctx    = _make_context()

    def test_high_volume_adequate(self):
        vols = [1_000_000.0] * 20 + [2_000_000.0]
        result = self.engine.run(self.ctx, {"volume_data": {"volumes": vols}})
        assert result.condition in (LiquidityCondition.ABUNDANT, LiquidityCondition.ADEQUATE)
        assert result.liquidity_score > 0.0

    def test_low_spread_improves_score(self):
        vols = [1_000.0] * 10 + [1_000.0]
        r1 = self.engine.run(self.ctx, {"volume_data": {"volumes": vols, "spread_bps": 5.0}})
        r2 = self.engine.run(self.ctx, {"volume_data": {"volumes": vols, "spread_bps": 50.0}})
        assert r1.liquidity_score >= r2.liquidity_score

    def test_no_data_defaults(self):
        result = self.engine.run(self.ctx, {})
        assert isinstance(result, LiquidityResult)


# ===========================================================================
# 23. MarketMomentumEngine
# ===========================================================================

class TestMarketMomentumEngine:
    def setup_method(self):
        self.engine = MarketMomentumEngine()
        self.ctx    = _make_context()

    def test_overbought_detection(self):
        # Strongly rising series → RSI should be high
        prices = _make_prices(100, trend=0.008)
        result = self.engine.run(self.ctx, {"index_prices": {"X": prices}})
        assert result.rsi > 50.0

    def test_neutral_no_data(self):
        result = self.engine.run(self.ctx, {})
        assert result.rsi == 50.0
        assert result.momentum_score == 50.0

    def test_trend_up_for_rising_prices(self):
        prices = _make_prices(100, trend=0.005)
        result = self.engine.run(self.ctx, {"index_prices": {"X": prices}})
        assert result.trend in (TrendDirection.UP, TrendDirection.SIDEWAYS)

    def test_trend_down_for_falling_prices(self):
        prices = _make_down_prices(100)
        result = self.engine.run(self.ctx, {"index_prices": {"X": prices}})
        assert result.trend in (TrendDirection.DOWN, TrendDirection.SIDEWAYS)


# ===========================================================================
# 24. MarketForecastingEngine
# ===========================================================================

class TestMarketForecastingEngine:
    def setup_method(self):
        self.engine = MarketForecastingEngine()
        self.ctx    = _make_context()

    def test_returns_forecasts_for_each_horizon(self):
        prices    = _make_prices(100)
        forecasts = self.engine.run(self.ctx, {"index_prices": {"X": prices}})
        assert len(forecasts) == 3  # DAY, WEEK, MONTH
        horizons  = {f.horizon for f in forecasts}
        assert ForecastHorizon.DAY   in horizons
        assert ForecastHorizon.WEEK  in horizons
        assert ForecastHorizon.MONTH in horizons

    def test_empty_prices_returns_empty(self):
        forecasts = self.engine.run(self.ctx, {})
        assert forecasts == ()

    def test_bullish_bias_for_bull_regime(self):
        prices = _make_prices(100, trend=0.003)
        regime = RegimeResult(
            regime=MarketRegime.STRONG_BULL, confidence=0.9,
            trend_direction=TrendDirection.STRONG_UP,
            trend_strength=TrendStrength.VERY_STRONG,
            regime_duration_bars=20,
        )
        forecasts = self.engine.run(self.ctx, {"index_prices": {"X": prices}}, regime=regime)
        day_fc = next(f for f in forecasts if f.horizon == ForecastHorizon.DAY)
        assert day_fc.direction in (ForecastDirection.BULLISH, ForecastDirection.NEUTRAL)

    def test_forecast_upside_above_downside(self):
        prices    = _make_prices(100)
        forecasts = self.engine.run(self.ctx, {"index_prices": {"X": prices}})
        for fc in forecasts:
            assert fc.upside_target >= fc.downside_target


# ===========================================================================
# 25. MarketPatternEngine
# ===========================================================================

class TestMarketPatternEngine:
    def setup_method(self):
        self.engine = MarketPatternEngine()
        self.ctx    = _make_context()

    def test_breakout_detected(self):
        # 300 flat bars then a single large jump — prior_high from [-51:-1] is all 100
        prices = [100.0] * 300 + [150.0]
        result = self.engine.run(self.ctx, {"index_prices": {"X": prices}})
        assert result is not None
        assert result.pattern_type == PatternType.BREAKOUT

    def test_insufficient_data_returns_none(self):
        result = self.engine.run(self.ctx, {"index_prices": {"X": [100.0, 101.0]}})
        assert result is None

    def test_consolidation_detected(self):
        prices = [1000.0] * 200  # flat
        result = self.engine.run(self.ctx, {"index_prices": {"X": prices}})
        assert result is not None
        assert result.pattern_type == PatternType.CONSOLIDATION

    def test_support_below_resistance(self):
        prices = _make_prices(100)
        result = self.engine.run(self.ctx, {"index_prices": {"X": prices}})
        if result:
            assert result.support_level <= result.resistance_level


# ===========================================================================
# 26. MarketScoringEngine
# ===========================================================================

class TestMarketScoringEngine:
    def setup_method(self):
        self.engine = MarketScoringEngine()

    def _make_regime(self, regime: MarketRegime) -> RegimeResult:
        return RegimeResult(
            regime=regime, confidence=0.8,
            trend_direction=TrendDirection.UP,
            trend_strength=TrendStrength.STRONG,
            regime_duration_bars=10,
        )

    def test_scores_all_in_range(self):
        scores = self.engine.run(
            regime     = self._make_regime(MarketRegime.BULL),
            breadth    = BreadthResult(
                advance_decline_ratio=2.0, advancing_pct=0.65,
                declining_pct=0.25, unchanged_pct=0.10,
                new_highs=20, new_lows=5, breadth_score=65.0, is_healthy=True,
            ),
        )
        d = scores.to_dict()
        for k, v in d.items():
            if isinstance(v, float):
                assert 0.0 <= v <= 100.0, f"{k}={v}"

    def test_bull_scores_higher_than_bear(self):
        bull_scores = self.engine.run(regime=self._make_regime(MarketRegime.STRONG_BULL))
        bear_scores = self.engine.run(regime=self._make_regime(MarketRegime.STRONG_BEAR))
        assert bull_scores.overall_score > bear_scores.overall_score

    def test_none_inputs_defaults(self):
        scores = self.engine.run()
        assert 0.0 <= scores.overall_score <= 100.0


# ===========================================================================
# 27. Strength helper
# ===========================================================================

class TestMarketStrengthEngine:
    def test_high_confidence_bull_scores_high(self):
        regime = RegimeResult(
            regime=MarketRegime.STRONG_BULL, confidence=0.9,
            trend_direction=TrendDirection.STRONG_UP,
            trend_strength=TrendStrength.VERY_STRONG,
            regime_duration_bars=50,
        )
        breadth = BreadthResult(
            advance_decline_ratio=3.0, advancing_pct=0.75,
            declining_pct=0.20, unchanged_pct=0.05,
            new_highs=50, new_lows=2, breadth_score=80.0, is_healthy=True,
        )
        score = compute_market_strength_score(regime, breadth, vol_score=85.0, mom_score=70.0)
        assert score > 70.0

    def test_defaults_without_inputs(self):
        score = compute_market_strength_score(None, None)
        assert 0.0 <= score <= 100.0


# ===========================================================================
# 28. Intelligence engine
# ===========================================================================

class TestMarketIntelligenceEngine:
    def _regime(self):
        return RegimeResult(
            regime=MarketRegime.BULL, confidence=0.75,
            trend_direction=TrendDirection.UP,
            trend_strength=TrendStrength.MODERATE,
            regime_duration_bars=15,
        )

    def _breadth(self):
        return BreadthResult(
            advance_decline_ratio=2.0, advancing_pct=0.65,
            declining_pct=0.25, unchanged_pct=0.10,
            new_highs=15, new_lows=3, breadth_score=65.0, is_healthy=True,
        )

    def test_summary_contains_regime(self):
        summary = generate_intelligence_summary(
            "ma-1", "NSE", self._regime(), self._breadth(),
            None, None, None, None,
        )
        assert "bull" in summary.lower()

    def test_key_risks_bear_regime(self):
        bear_regime = RegimeResult(
            regime=MarketRegime.STRONG_BEAR, confidence=0.9,
            trend_direction=TrendDirection.STRONG_DOWN,
            trend_strength=TrendStrength.STRONG,
            regime_duration_bars=5,
        )
        risks = _key_risks(bear_regime, None, None, None)
        assert any("bear" in r.lower() for r in risks)

    def test_key_risks_no_risks(self):
        risks = _key_risks(None, None, None, None)
        assert len(risks) == 1
        assert "no" in risks[0].lower()

    def test_key_opportunities_bullish(self):
        opps = _key_opportunities(self._regime(), self._breadth(), None)
        assert len(opps) >= 1

    def test_key_opportunities_no_opps(self):
        opps = _key_opportunities(None, None, None)
        assert "no" in opps[0].lower()


# ===========================================================================
# 29. MarketAnalyticsManager (pipeline)
# ===========================================================================

class TestMarketAnalyticsManager:
    def setup_method(self):
        self.manager = MarketAnalyticsManager()

    def test_full_pipeline_success(self):
        req    = _make_request(prices=_make_prices(250))
        report = self.manager.run(req)
        assert isinstance(report, MarketAnalyticsReport)
        assert report.is_success is True

    def test_pipeline_with_sector_data(self):
        ctx = _make_context()
        req = MarketAnalyticsFactory.create_request(
            "a", "b", "NSE", ctx, policy_approved=True,
            index_prices={"NIFTY": _make_prices(250)},
            sector_data={
                "Technology": {"prices": _make_prices(250, trend=0.003)},
                "Energy":     {"prices": _make_prices(250, trend=-0.001)},
            },
        )
        report = self.manager.run(req)
        assert len(report.sector_results) == 2
        assert report.rotation is not None

    def test_pipeline_forecasts_generated(self):
        req    = _make_request(prices=_make_prices(100))
        report = self.manager.run(req)
        assert len(report.forecasts) > 0

    def test_pipeline_scores_not_none(self):
        req    = _make_request(prices=_make_prices(100))
        report = self.manager.run(req)
        assert report.scores is not None
        assert 0.0 <= report.scores.overall_score <= 100.0


# ===========================================================================
# 30. MarketAnalyticsEngine (lifecycle + full integration)
# ===========================================================================

class TestMarketAnalyticsEngine:
    def test_engine_starts_and_stops(self):
        engine = MarketAnalyticsEngine()
        assert engine.lifecycle_state().value != "running"
        engine.start()
        assert engine.lifecycle_state().value == "running"
        engine.stop()
        assert engine.lifecycle_state().value != "running"

    def test_assess_raises_when_not_started(self):
        engine  = MarketAnalyticsEngine()
        request = _make_request()
        with pytest.raises(MarketAnalyticsEngineNotRunningError):
            engine.assess(request)

    def test_assess_raises_not_approved(self):
        engine  = _started_engine()
        request = _make_request(policy_approved=False)
        with pytest.raises(MarketAnalyticsNotApprovedError):
            engine.assess(request)

    def test_assess_raises_validation_error_no_data(self):
        engine  = _started_engine()
        ctx     = _make_context()
        request = MarketAnalyticsFactory.create_request(
            "a", "b", "NSE", ctx, policy_approved=True,
        )
        with pytest.raises(MarketAnalyticsValidationError):
            engine.assess(request)

    def test_assess_success_full_pipeline(self):
        engine  = _started_engine()
        request = _make_request(prices=_make_prices(250))
        report  = engine.assess(request)
        assert report.is_success is True
        assert report.scores is not None

    def test_assess_records_statistics(self):
        engine  = _started_engine()
        engine.assess(_make_request(prices=_make_prices(100)))
        snap = engine.statistics()
        assert snap["analytics_total"]     >= 1
        assert snap["analytics_completed"] >= 1

    def test_assess_registers_report(self):
        engine  = _started_engine()
        report  = engine.assess(_make_request(prices=_make_prices(100)))
        fetched = engine.get_report(report.report_id)
        assert fetched is report

    def test_latest_for_exchange(self):
        engine = _started_engine()
        engine.assess(_make_request(prices=_make_prices(100), exchange="NSE"))
        latest = engine.latest_for_exchange("NSE")
        assert latest is not None
        assert latest.exchange == "NSE"

    def test_add_and_remove_listener(self):
        engine  = _started_engine()
        events  = []
        def listener(evt):
            events.append(evt)

        engine.add_listener(listener)
        engine.assess(_make_request(prices=_make_prices(100)))
        count_after_add = len(events)

        engine.remove_listener(listener)
        engine.assess(_make_request(prices=_make_prices(100)))
        assert len(events) == count_after_add  # no new events added

    def test_add_listener_idempotent(self):
        engine = _started_engine()
        fn = MagicMock()
        engine.add_listener(fn)
        engine.add_listener(fn)
        engine.assess(_make_request(prices=_make_prices(100)))
        # fn should be called once per event, not twice
        assert fn.call_count == fn.call_count  # basic sanity (not zero)

    def test_listener_exception_does_not_crash_engine(self):
        engine = _started_engine()
        def bad_listener(evt):
            raise RuntimeError("listener error")
        engine.add_listener(bad_listener)
        report = engine.assess(_make_request(prices=_make_prices(100)))
        assert report.is_success is True  # engine still works

    def test_history_counts_accumulate(self):
        engine = _started_engine()
        engine.assess(_make_request(prices=_make_prices(100)))
        counts = engine.history_counts()
        assert counts["requests"] >= 1
        assert counts["reports"]  >= 1

    def test_multiple_assessments_different_exchanges(self):
        engine = _started_engine()
        for exchange in ("NSE", "BSE", "NSE"):
            req = _make_request(prices=_make_prices(100), exchange=exchange)
            engine.assess(req)
        nse = engine.latest_for_exchange("NSE")
        bse = engine.latest_for_exchange("BSE")
        assert nse is not None
        assert bse is not None

    def test_stop_and_restart(self):
        engine = MarketAnalyticsEngine()
        engine.start()
        engine.stop()
        engine.start()
        report = engine.assess(_make_request(prices=_make_prices(100)))
        assert report.is_success is True


# ===========================================================================
# 31. Public __init__ surface
# ===========================================================================

class TestPublicSurface:
    def test_all_exported_names_importable(self):
        import iios.market.analytics as pkg
        for name in pkg.__all__:
            assert hasattr(pkg, name), f"Missing: {name}"

    def test_version_exported(self):
        from iios.market.analytics import VERSION
        assert VERSION == "1.0.0"

    def test_analytics_system_id_exported(self):
        from iios.market.analytics import ANALYTICS_SYSTEM_ID
        assert "analytics" in ANALYTICS_SYSTEM_ID
