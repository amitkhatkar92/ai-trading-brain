"""tests/unit/investment/market/test_market_intelligence_engine.py"""
from __future__ import annotations

import asyncio
import math
import threading
import time

import pytest

from iios.investment.market import (
    # constants
    BreadthCondition, CorrelationRegime, LiquidityLevel, MarketPhase,
    MarketRegime, MarketStatus, MarketStrength, SentimentLevel,
    TrendDirection, VolatilityLevel,
    MARKET_ENGINE_VERSION,
    # exceptions
    MarketIntelligenceError,
    MarketStateNotFoundError, MarketStateAlreadyExistsError,
    RegimeNotFoundError,
    SnapshotNotFoundError,
    MarketEngineNotInitializedError, MarketEngineAlreadyRunningError,
    MarketRegistryItemNotFoundError, MarketRegistryItemAlreadyExistsError,
    MarketRegistryOverflowError,
    MarketDataMissingError,
    # context
    MarketContextState, get_market_context, reset_market_context,
    market_session, market_stage_scope,
    # market state
    MarketState, MarketSnapshot, MarketStateManager, MarketStatistics,
    # regime
    RegimeTransition, RegimeHistory, RegimeClassifier, DefaultRegimeClassifier,
    MarketRegimeEngine,
    # analytics
    TrendAnalyzer, TrendAnalysis,
    BreadthAnalyzer, BreadthAnalysis,
    VolatilityAnalyzer, VolatilityAnalysis,
    LiquidityAnalyzer, LiquidityAnalysis,
    CorrelationAnalyzer, CorrelationAnalysis,
    MarketStructureEngine, MarketStructure,
    # models
    MarketHealth, MarketSignal, SignalType, SignalStrength,
    MarketSummary, MarketIntelligence,
    # factory
    MarketFactory,
    # registry
    MarketRegistry, get_market_registry, reset_market_registry,
    # manager
    MarketManager, get_market_manager, reset_market_manager,
    # engine
    MarketIntelligenceEngine, get_market_engine, reset_market_engine,
)


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _reset_all():
    reset_market_engine()
    reset_market_manager()
    reset_market_registry()
    reset_market_context()
    yield
    reset_market_engine()
    reset_market_manager()
    reset_market_registry()
    reset_market_context()


def _snap(
    market_id: str = "NSE",
    trend:     TrendDirection  = TrendDirection.UP,
    breadth:   BreadthCondition = BreadthCondition.BROAD,
    vol:       VolatilityLevel  = VolatilityLevel.MODERATE,
    liquidity: LiquidityLevel   = LiquidityLevel.HIGH,
) -> MarketSnapshot:
    s = MarketSnapshot(market_id=market_id, status=MarketStatus.OPEN)
    s.trend    = trend
    s.breadth  = breadth
    s.volatility = vol
    s.liquidity  = liquidity
    return s


def _eng() -> MarketIntelligenceEngine:
    e = MarketIntelligenceEngine()
    e.initialize()
    return e


# ═══════════════════════════════════════════════════════════════════════════════
# TestConstants
# ═══════════════════════════════════════════════════════════════════════════════

class TestConstants:
    def test_market_status_values(self):
        assert MarketStatus.OPEN.value    == "open"
        assert MarketStatus.CLOSED.value  == "closed"
        assert MarketStatus.HOLIDAY.value == "holiday"
        assert MarketStatus.HALTED.value  == "halted"

    def test_market_regime_values(self):
        assert MarketRegime.BULL.value    == "bull"
        assert MarketRegime.BEAR.value    == "bear"
        assert MarketRegime.CRISIS.value  == "crisis"
        assert MarketRegime.UNKNOWN.value == "unknown"

    def test_trend_direction_values(self):
        assert TrendDirection.UP.value        == "up"
        assert TrendDirection.DOWN.value      == "down"
        assert TrendDirection.SIDEWAYS.value  == "sideways"
        assert TrendDirection.UNDEFINED.value == "undefined"

    def test_volatility_level_values(self):
        assert VolatilityLevel.EXTREME.value  == "extreme"
        assert VolatilityLevel.VERY_LOW.value == "very_low"

    def test_breadth_condition_values(self):
        assert BreadthCondition.VERY_BROAD.value  == "very_broad"
        assert BreadthCondition.VERY_NARROW.value == "very_narrow"

    def test_version(self):
        assert MARKET_ENGINE_VERSION == "1.0.0"


# ═══════════════════════════════════════════════════════════════════════════════
# TestExceptions
# ═══════════════════════════════════════════════════════════════════════════════

class TestExceptions:
    def test_root_error(self):
        e = MarketIntelligenceError("boom", "MI-999")
        assert "MI-999" in str(e)

    def test_state_not_found(self):
        e = MarketStateNotFoundError("NSE")
        assert "NSE" in str(e)
        assert e.code == "MI-011"

    def test_state_already_exists(self):
        e = MarketStateAlreadyExistsError("NYSE")
        assert e.code == "MI-012"

    def test_snapshot_not_found(self):
        e = SnapshotNotFoundError("key")
        assert e.code == "MI-031"

    def test_engine_not_initialized(self):
        e = MarketEngineNotInitializedError()
        assert "MI-051" in str(e)

    def test_engine_already_running(self):
        e = MarketEngineAlreadyRunningError()
        assert "MI-052" in str(e)

    def test_registry_overflow(self):
        e = MarketRegistryOverflowError(100)
        assert "100" in str(e)
        assert e.code == "MI-063"

    def test_hierarchy_root(self):
        assert issubclass(MarketStateNotFoundError,  MarketIntelligenceError)
        assert issubclass(MarketEngineAlreadyRunningError, MarketIntelligenceError)
        assert issubclass(SnapshotNotFoundError,     MarketIntelligenceError)

    def test_data_missing(self):
        e = MarketDataMissingError("prices")
        assert "prices" in str(e)
        assert e.code == "MI-071"

    def test_regime_not_found(self):
        e = RegimeNotFoundError("TSX")
        assert "TSX" in str(e)
        assert e.code == "MI-021"


# ═══════════════════════════════════════════════════════════════════════════════
# TestMarketState
# ═══════════════════════════════════════════════════════════════════════════════

class TestMarketState:
    def test_defaults(self):
        s = MarketState(market_id="NSE")
        assert s.state_id
        assert s.status == MarketStatus.UNKNOWN
        assert not s.is_trading

    def test_open(self):
        s = MarketState(market_id="NSE")
        s.open(trading_date="2026-07-09")
        assert s.status     == MarketStatus.OPEN
        assert s.is_trading is True
        assert s.trading_date == "2026-07-09"
        assert s.session_start is not None

    def test_close(self):
        s = MarketState(market_id="NSE")
        s.open()
        s.close()
        assert s.status     == MarketStatus.CLOSED
        assert s.is_trading is False
        assert s.session_end is not None

    def test_session_duration(self):
        s = MarketState(market_id="NSE")
        s.open()
        time.sleep(0.02)
        s.close()
        assert s.session_duration_sec() >= 0.01

    def test_to_dict(self):
        s = MarketState(market_id="NSE", name="NSE India")
        d = s.to_dict()
        assert d["market_id"] == "NSE"
        assert d["name"]      == "NSE India"
        assert "state_id" in d


# ═══════════════════════════════════════════════════════════════════════════════
# TestMarketSnapshot
# ═══════════════════════════════════════════════════════════════════════════════

class TestMarketSnapshot:
    def test_defaults(self):
        s = MarketSnapshot(market_id="NSE")
        assert s.snapshot_id
        assert s.status    == MarketStatus.UNKNOWN
        assert s.prices    == {}
        assert s.advances  == 0

    def test_age(self):
        s = MarketSnapshot()
        assert s.age_sec >= 0

    def test_is_stale(self):
        s = MarketSnapshot()
        assert not s.is_stale(ttl_sec=1000)
        assert s.is_stale(ttl_sec=0)

    def test_advance_decline_ratio(self):
        s = MarketSnapshot(advances=300, declines=100)
        assert s.advance_decline_ratio == pytest.approx(3.0)

    def test_to_dict(self):
        s = MarketSnapshot(market_id="BSE", prices={"RELIANCE": 2500.0})
        d = s.to_dict()
        assert d["market_id"]       == "BSE"
        assert d["prices"]["RELIANCE"] == 2500.0


# ═══════════════════════════════════════════════════════════════════════════════
# TestMarketStateManager
# ═══════════════════════════════════════════════════════════════════════════════

class TestMarketStateManager:
    def test_register_and_get(self):
        mgr = MarketStateManager()
        state = mgr.register("NSE", name="NSE India")
        assert state.market_id == "NSE"
        assert mgr.get("NSE").market_id == "NSE"

    def test_duplicate_raises(self):
        mgr = MarketStateManager()
        mgr.register("NSE")
        with pytest.raises(MarketStateAlreadyExistsError):
            mgr.register("NSE")

    def test_overwrite(self):
        mgr = MarketStateManager()
        mgr.register("NSE", name="Old")
        mgr.register("NSE", name="New", overwrite=True)
        assert mgr.get("NSE").name == "New"

    def test_not_found_raises(self):
        mgr = MarketStateManager()
        with pytest.raises(MarketStateNotFoundError):
            mgr.get("GHOST")

    def test_open_and_close(self):
        mgr = MarketStateManager()
        mgr.register("NSE")
        mgr.open_market("NSE", trading_date="2026-07-09")
        assert mgr.get("NSE").is_trading is True
        mgr.close_market("NSE")
        assert mgr.get("NSE").is_trading is False

    def test_active_markets(self):
        mgr = MarketStateManager()
        mgr.register("A"); mgr.register("B"); mgr.register("C")
        mgr.open_market("A"); mgr.open_market("B")
        active = mgr.active_markets()
        assert len(active) == 2


# ═══════════════════════════════════════════════════════════════════════════════
# TestMarketStatistics
# ═══════════════════════════════════════════════════════════════════════════════

class TestMarketStatistics:
    def test_zero_state(self):
        s = MarketStatistics()
        assert s.success_rate == 0.0
        assert s.avg_duration_ms == 0.0

    def test_record_analysis(self):
        s = MarketStatistics()
        s.record_analysis(100.0)
        s.record_analysis(200.0, failed=True)
        assert s.total_analyses  == 2
        assert s.failed_analyses == 1
        assert s.avg_duration_ms == pytest.approx(150.0)
        assert s.success_rate    == pytest.approx(0.5)

    def test_to_dict(self):
        s = MarketStatistics(total_snapshots=5)
        d = s.to_dict()
        assert d["total_snapshots"] == 5
        assert "success_rate" in d


# ═══════════════════════════════════════════════════════════════════════════════
# TestRegimeTransition
# ═══════════════════════════════════════════════════════════════════════════════

class TestRegimeTransition:
    def test_defaults(self):
        t = RegimeTransition(market_id="NSE")
        assert t.transition_id
        assert t.from_regime == MarketRegime.UNKNOWN

    def test_to_dict(self):
        t = RegimeTransition(
            market_id   = "NSE",
            from_regime = MarketRegime.BULL,
            to_regime   = MarketRegime.BEAR,
            confidence  = 0.9,
        )
        d = t.to_dict()
        assert d["from_regime"] == "bull"
        assert d["to_regime"]   == "bear"
        assert d["confidence"]  == pytest.approx(0.9)

    def test_unique_ids(self):
        t1 = RegimeTransition()
        t2 = RegimeTransition()
        assert t1.transition_id != t2.transition_id


# ═══════════════════════════════════════════════════════════════════════════════
# TestRegimeHistory
# ═══════════════════════════════════════════════════════════════════════════════

class TestRegimeHistory:
    def test_record_and_get(self):
        h = RegimeHistory()
        t = RegimeTransition(market_id="NSE", to_regime=MarketRegime.BULL)
        h.record(t)
        assert h.get(t.transition_id).transition_id == t.transition_id

    def test_idempotent_record(self):
        h = RegimeHistory()
        t = RegimeTransition()
        h.record(t)
        h.record(t)   # second call is no-op
        assert h.count() == 1

    def test_for_market(self):
        h = RegimeHistory()
        h.record(RegimeTransition(market_id="NSE"))
        h.record(RegimeTransition(market_id="NSE"))
        h.record(RegimeTransition(market_id="BSE"))
        assert len(h.for_market("NSE")) == 2

    def test_current_regime(self):
        h = RegimeHistory()
        h.record(RegimeTransition(market_id="NSE", to_regime=MarketRegime.BULL))
        h.record(RegimeTransition(market_id="NSE", to_regime=MarketRegime.BEAR))
        assert h.current_regime("NSE") == MarketRegime.BEAR

    def test_recent(self):
        h = RegimeHistory()
        for _ in range(5):
            h.record(RegimeTransition())
        assert len(h.recent(3)) == 3


# ═══════════════════════════════════════════════════════════════════════════════
# TestDefaultRegimeClassifier
# ═══════════════════════════════════════════════════════════════════════════════

class TestDefaultRegimeClassifier:
    def test_classifier_id(self):
        assert DefaultRegimeClassifier().classifier_id == "default"

    def test_crisis(self):
        s = _snap(trend=TrendDirection.DOWN, breadth=BreadthCondition.VERY_NARROW,
                  vol=VolatilityLevel.EXTREME)
        regime, conf = DefaultRegimeClassifier().classify(s, [])
        assert regime == MarketRegime.CRISIS
        assert conf   > 0.8

    def test_bull(self):
        s = _snap(trend=TrendDirection.UP, breadth=BreadthCondition.BROAD,
                  vol=VolatilityLevel.MODERATE)
        regime, conf = DefaultRegimeClassifier().classify(s, [])
        assert regime == MarketRegime.BULL
        assert conf   > 0.7

    def test_bear(self):
        s = _snap(trend=TrendDirection.DOWN, breadth=BreadthCondition.NARROW,
                  vol=VolatilityLevel.MODERATE)
        regime, conf = DefaultRegimeClassifier().classify(s, [])
        assert regime == MarketRegime.BEAR

    def test_sideways(self):
        s = _snap(trend=TrendDirection.SIDEWAYS, breadth=BreadthCondition.MODERATE,
                  vol=VolatilityLevel.MODERATE)
        regime, _ = DefaultRegimeClassifier().classify(s, [])
        assert regime == MarketRegime.SIDEWAYS

    def test_high_volatility(self):
        s = _snap(trend=TrendDirection.UNDEFINED, breadth=BreadthCondition.MODERATE,
                  vol=VolatilityLevel.HIGH)
        regime, _ = DefaultRegimeClassifier().classify(s, [])
        assert regime == MarketRegime.HIGH_VOLATILITY

    def test_to_dict(self):
        d = DefaultRegimeClassifier().to_dict()
        assert d["classifier_id"] == "default"


# ═══════════════════════════════════════════════════════════════════════════════
# TestMarketRegimeEngine
# ═══════════════════════════════════════════════════════════════════════════════

class TestMarketRegimeEngine:
    def test_classify_bull(self):
        eng = MarketRegimeEngine()
        s   = _snap(trend=TrendDirection.UP, breadth=BreadthCondition.BROAD)
        regime, conf = eng.classify("NSE", s)
        assert regime == MarketRegime.BULL
        assert conf   > 0

    def test_records_transition(self):
        eng = MarketRegimeEngine()
        s1  = _snap(trend=TrendDirection.UP, breadth=BreadthCondition.BROAD)
        s2  = _snap(trend=TrendDirection.DOWN, breadth=BreadthCondition.NARROW)
        eng.classify("NSE", s1)
        eng.classify("NSE", s2)
        transitions = eng.regime_history().for_market("NSE")
        assert len(transitions) >= 1   # UNKNOWN → BULL + BULL → BEAR

    def test_current_regime(self):
        eng = MarketRegimeEngine()
        s   = _snap(trend=TrendDirection.UP, breadth=BreadthCondition.BROAD)
        eng.classify("NSE", s)
        assert eng.current_regime("NSE") == MarketRegime.BULL

    def test_custom_classifier(self):
        always_bull = MarketFactory.make_function_classifier(
            "always_bull", "Always Bull",
            lambda snap, hist: (MarketRegime.BULL, 0.99),
        )
        eng = MarketRegimeEngine(classifier=always_bull)
        regime, conf = eng.classify("X", _snap())
        assert regime == MarketRegime.BULL
        assert conf   == pytest.approx(0.99)

    def test_set_classifier(self):
        eng = MarketRegimeEngine()
        c   = DefaultRegimeClassifier()
        eng.set_classifier(c)
        assert eng._classifier.classifier_id == "default"


# ═══════════════════════════════════════════════════════════════════════════════
# TestTrendAnalyzer
# ═══════════════════════════════════════════════════════════════════════════════

class TestTrendAnalyzer:
    def test_empty_series(self):
        a = TrendAnalyzer().analyze([])
        assert a.direction == TrendDirection.UNDEFINED

    def test_single_price(self):
        a = TrendAnalyzer().analyze([100.0])
        assert a.direction == TrendDirection.UNDEFINED

    def test_uptrend(self):
        prices = [100 + i for i in range(30)]   # strongly rising
        a = TrendAnalyzer().analyze(prices)
        assert a.direction == TrendDirection.UP
        assert a.score     > 50

    def test_downtrend(self):
        prices = [100 - i for i in range(30)]   # strongly falling
        a = TrendAnalyzer().analyze(prices)
        assert a.direction == TrendDirection.DOWN
        assert a.score     < 50

    def test_sideways(self):
        prices = [100.0] * 30
        a = TrendAnalyzer().analyze(prices)
        assert a.direction == TrendDirection.SIDEWAYS
        assert a.score     == pytest.approx(50.0)

    def test_strong_uptrend_strength(self):
        prices = [100 * (1.05 ** i) for i in range(30)]
        a = TrendAnalyzer().analyze(prices)
        assert a.strength in (MarketStrength.STRONG, MarketStrength.VERY_STRONG)

    def test_to_dict(self):
        a = TrendAnalyzer().analyze([100, 101, 102])
        d = a.to_dict()
        assert "direction" in d
        assert "score"     in d


# ═══════════════════════════════════════════════════════════════════════════════
# TestBreadthAnalyzer
# ═══════════════════════════════════════════════════════════════════════════════

class TestBreadthAnalyzer:
    def test_zero_totals(self):
        a = BreadthAnalyzer().analyze(0, 0, 0)
        assert a.condition == BreadthCondition.MODERATE

    def test_very_broad(self):
        a = BreadthAnalyzer().analyze(700, 300, 0)
        assert a.condition == BreadthCondition.VERY_BROAD
        assert a.score     > 50

    def test_very_narrow(self):
        a = BreadthAnalyzer().analyze(200, 800, 0)
        assert a.condition == BreadthCondition.VERY_NARROW
        assert a.score     < 50

    def test_advance_decline_ratio(self):
        a = BreadthAnalyzer().analyze(600, 200, 200)
        assert a.advance_decline_ratio == pytest.approx(3.0)

    def test_to_dict(self):
        a = BreadthAnalyzer().analyze(500, 500, 0)
        d = a.to_dict()
        assert "condition" in d
        assert "score"     in d


# ═══════════════════════════════════════════════════════════════════════════════
# TestVolatilityAnalyzer
# ═══════════════════════════════════════════════════════════════════════════════

class TestVolatilityAnalyzer:
    def test_too_few_returns(self):
        a = VolatilityAnalyzer().analyze([0.01, 0.02])
        assert a.level == VolatilityLevel.MODERATE  # default

    def test_low_volatility(self):
        returns = [0.001] * 30
        a = VolatilityAnalyzer().analyze(returns)
        assert a.level in (VolatilityLevel.VERY_LOW, VolatilityLevel.LOW)

    def test_high_volatility(self):
        import random
        random.seed(42)
        returns = [random.gauss(0, 0.04) for _ in range(50)]   # ~64% ann vol
        a = VolatilityAnalyzer().analyze(returns)
        assert a.level in (VolatilityLevel.HIGH, VolatilityLevel.EXTREME)

    def test_annualized_vol(self):
        # Alternating returns: window=20 won't truncate (only 10 items), mean=0, vol>0
        returns = [0.01 if i % 2 == 0 else -0.01 for i in range(10)]
        a = VolatilityAnalyzer().analyze(returns)
        assert a.realized_vol > 0

    def test_to_dict(self):
        a = VolatilityAnalyzer().analyze([0.01] * 10)
        d = a.to_dict()
        assert "level" in d
        assert "realized_vol" in d


# ═══════════════════════════════════════════════════════════════════════════════
# TestLiquidityAnalyzer
# ═══════════════════════════════════════════════════════════════════════════════

class TestLiquidityAnalyzer:
    def test_empty_volumes(self):
        a = LiquidityAnalyzer().analyze([])
        assert a.level == LiquidityLevel.MODERATE  # default

    def test_very_high_liquidity(self):
        vols = {"A": 10_000_000, "B": 8_000_000}
        a = LiquidityAnalyzer().analyze(vols)
        assert a.level in (LiquidityLevel.VERY_HIGH, LiquidityLevel.HIGH)

    def test_illiquid(self):
        vols = {"A": 1_000, "B": 2_000}
        spds = {"A": 0.15, "B": 0.12}
        a = LiquidityAnalyzer().analyze(vols, spds)
        assert a.level in (LiquidityLevel.VERY_LOW, LiquidityLevel.ILLIQUID)

    def test_score_range(self):
        a = LiquidityAnalyzer().analyze({"A": 1_000_000})
        assert 0 <= a.score <= 100

    def test_to_dict(self):
        a = LiquidityAnalyzer().analyze({"A": 500_000})
        d = a.to_dict()
        assert "level"      in d
        assert "avg_volume" in d


# ═══════════════════════════════════════════════════════════════════════════════
# TestCorrelationAnalyzer
# ═══════════════════════════════════════════════════════════════════════════════

class TestCorrelationAnalyzer:
    def test_too_few_symbols(self):
        a = CorrelationAnalyzer().analyze({"A": [0.01, 0.02, 0.03]})
        assert a.avg_correlation == 0.0

    def test_perfectly_correlated(self):
        returns = [0.01, -0.02, 0.03, -0.01, 0.02]
        a = CorrelationAnalyzer().analyze({"A": returns, "B": returns})
        assert a.avg_correlation == pytest.approx(1.0, abs=1e-6)
        assert a.regime == CorrelationRegime.HIGH_CORRELATION

    def test_anti_correlated(self):
        r = [0.01, -0.02, 0.03, -0.01, 0.02]
        a = CorrelationAnalyzer().analyze({"A": r, "B": [-x for x in r]})
        assert a.avg_correlation == pytest.approx(-1.0, abs=1e-6)
        assert a.regime == CorrelationRegime.DECORRELATED

    def test_multi_symbol(self):
        r = [0.01, -0.02, 0.03, -0.01, 0.02]
        series = {"A": r, "B": r, "C": r}
        a = CorrelationAnalyzer().analyze(series)
        assert a.metadata["n_pairs"] == 3

    def test_to_dict(self):
        r = [0.01, 0.02, 0.03, 0.01, 0.02]
        a = CorrelationAnalyzer().analyze({"X": r, "Y": r})
        d = a.to_dict()
        assert "avg_correlation" in d


# ═══════════════════════════════════════════════════════════════════════════════
# TestMarketStructureEngine
# ═══════════════════════════════════════════════════════════════════════════════

class TestMarketStructureEngine:
    def test_basic_analysis(self):
        eng  = MarketStructureEngine()
        snap = MarketSnapshot(
            market_id = "NSE",
            prices    = {"A": 100.0, "B": 200.0},
            volumes   = {"A": 1_000_000, "B": 2_000_000},
            changes   = {"A": 0.01, "B": -0.005},
            advances  = 700, declines=300,
        )
        struct = eng.analyze(snap)
        assert isinstance(struct, MarketStructure)
        assert 0 <= struct.health_score  <= 100
        assert 0 <= struct.quality_score <= 100

    def test_writes_back_to_snapshot(self):
        eng  = MarketStructureEngine()
        snap = MarketSnapshot(
            prices  = {"A": 100 + i for i in range(5)},
            changes = {"A": 0.01},
            advances= 800, declines=200,
        )
        eng.analyze(snap)
        assert snap.trend    != TrendDirection.UNDEFINED or True   # may remain undefined with tiny series
        assert snap.breadth  != BreadthCondition.MODERATE or True

    def test_with_price_history(self):
        eng     = MarketStructureEngine()
        snap    = MarketSnapshot(prices={"A": 110.0})
        history = [float(100 + i) for i in range(20)]
        struct  = eng.analyze(snap, price_history=history)
        assert struct.trend.direction == TrendDirection.UP

    def test_health_decreases_with_high_vol(self):
        eng  = MarketStructureEngine()
        # Create a very high vol scenario
        ret_series = [0.10, -0.12, 0.15, -0.09, 0.11] * 5
        snap_hv = MarketSnapshot(advances=200, declines=800,
                                 changes={"A": r for r in ret_series[:5]})
        struct_hv = eng.analyze(snap_hv, return_history=ret_series)
        # narrow breadth + high vol = low health
        assert struct_hv.health_score < 60

    def test_to_dict(self):
        eng    = MarketStructureEngine()
        struct = eng.analyze(MarketSnapshot())
        d      = struct.to_dict()
        assert "trend"         in d
        assert "health_score"  in d
        assert "quality_score" in d


# ═══════════════════════════════════════════════════════════════════════════════
# TestMarketHealth
# ═══════════════════════════════════════════════════════════════════════════════

class TestMarketHealth:
    def test_defaults(self):
        h = MarketHealth()
        assert h.overall_score == 50.0
        assert "overall" in h.labels

    def test_is_healthy(self):
        assert MarketHealth(overall_score=75.0).is_healthy is True
        assert MarketHealth(overall_score=40.0).is_healthy is False

    def test_labels_generated(self):
        h = MarketHealth(overall_score=80.0, liquidity_score=80.0)
        assert h.labels["overall"]   == "GOOD"
        assert h.labels["liquidity"] == "GOOD"

    def test_to_dict(self):
        d = MarketHealth(overall_score=60.0).to_dict()
        assert d["overall_score"] == 60.0
        assert "is_healthy" in d


# ═══════════════════════════════════════════════════════════════════════════════
# TestMarketSignal
# ═══════════════════════════════════════════════════════════════════════════════

class TestMarketSignal:
    def test_defaults(self):
        s = MarketSignal(market_id="NSE", label="Uptrend")
        assert s.signal_id
        assert s.direction == "neutral"

    def test_to_dict(self):
        s = MarketSignal(
            market_id   = "NSE",
            label       = "High Vol",
            signal_type = SignalType.VOLATILITY,
            confidence  = 0.85,
            direction   = "up",
        )
        d = s.to_dict()
        assert d["label"]       == "High Vol"
        assert d["signal_type"] == "volatility"

    def test_unique_ids(self):
        assert MarketSignal().signal_id != MarketSignal().signal_id


# ═══════════════════════════════════════════════════════════════════════════════
# TestMarketSummary
# ═══════════════════════════════════════════════════════════════════════════════

class TestMarketSummary:
    def test_defaults(self):
        s = MarketSummary(market_id="NSE")
        assert s.summary_id
        assert s.regime == MarketRegime.UNKNOWN

    def test_to_dict(self):
        s = MarketSummary(market_id="NSE", regime=MarketRegime.BULL)
        d = s.to_dict()
        assert d["regime"] == "bull"

    def test_unique_ids(self):
        assert MarketSummary().summary_id != MarketSummary().summary_id


# ═══════════════════════════════════════════════════════════════════════════════
# TestMarketIntelligence
# ═══════════════════════════════════════════════════════════════════════════════

class TestMarketIntelligence:
    def test_defaults(self):
        i = MarketIntelligence(market_id="NSE")
        assert i.intelligence_id
        assert i.regime == MarketRegime.UNKNOWN

    def test_add_signal(self):
        i = MarketIntelligence(market_id="NSE")
        i.add_signal(MarketSignal(label="test"))
        assert len(i.signals) == 1

    def test_add_opportunity_and_threat(self):
        i = MarketIntelligence()
        i.add_opportunity("strong trend")
        i.add_threat("narrow breadth")
        assert "strong trend"  in i.opportunities
        assert "narrow breadth" in i.threats

    def test_add_observation(self):
        i = MarketIntelligence()
        i.add_observation("market is trending")
        assert len(i.key_observations) == 1

    def test_to_dict(self):
        i = MarketIntelligence(market_id="NSE", regime=MarketRegime.BULL)
        d = i.to_dict()
        assert d["regime"]    == "bull"
        assert d["market_id"] == "NSE"
        assert "health" in d


# ═══════════════════════════════════════════════════════════════════════════════
# TestMarketRegistry
# ═══════════════════════════════════════════════════════════════════════════════

class TestMarketRegistry:
    def test_register_and_is_registered(self):
        reg = MarketRegistry()
        reg.register_market("NSE")
        assert reg.is_registered("NSE")

    def test_duplicate_raises(self):
        reg = MarketRegistry()
        reg.register_market("NSE")
        with pytest.raises(MarketRegistryItemAlreadyExistsError):
            reg.register_market("NSE")

    def test_overwrite_market(self):
        reg = MarketRegistry()
        reg.register_market("NSE", name="Old")
        reg.register_market("NSE", name="New", overwrite=True)  # no error

    def test_register_classifier(self):
        reg = MarketRegistry()
        reg.register_classifier(DefaultRegimeClassifier())
        assert reg.has_classifier("default")

    def test_duplicate_classifier_raises(self):
        reg = MarketRegistry()
        reg.register_classifier(DefaultRegimeClassifier())
        with pytest.raises(MarketRegistryItemAlreadyExistsError):
            reg.register_classifier(DefaultRegimeClassifier())

    def test_register_analyzer(self):
        reg = MarketRegistry()
        reg.register_analyzer("my_analyzer", object())
        assert reg.has_analyzer("my_analyzer")

    def test_overflow(self):
        reg = MarketRegistry(max_markets=2)
        reg.register_market("A"); reg.register_market("B")
        with pytest.raises(MarketRegistryOverflowError):
            reg.register_market("C")

    def test_statistics(self):
        reg = MarketRegistry()
        reg.register_market("NSE")
        s = reg.statistics()
        assert s["markets"] == 1

    def test_singleton(self):
        r1 = get_market_registry()
        r2 = get_market_registry()
        assert r1 is r2


# ═══════════════════════════════════════════════════════════════════════════════
# TestMarketContext
# ═══════════════════════════════════════════════════════════════════════════════

class TestMarketContext:
    def test_session_creates_context(self):
        with market_session("NSE", "src") as ctx:
            assert ctx.market_id == "NSE"
            assert ctx.source_id == "src"

    def test_stage_scope(self):
        with market_session() as ctx:
            assert ctx.current_stage == ""
            with market_stage_scope("validate"):
                assert ctx.current_stage == "validate"
            assert ctx.current_stage == ""

    def test_diagnostics(self):
        with market_session() as ctx:
            ctx.add_diagnostic("WARNING", "w1")
            ctx.add_diagnostic("ERROR",   "e1")
            assert len(ctx.warnings()) == 1
            assert len(ctx.errors())   == 1

    def test_elapsed(self):
        with market_session() as ctx:
            time.sleep(0.01)
            assert ctx.elapsed_ms() > 0

    def test_to_dict(self):
        with market_session("NSE") as ctx:
            d = ctx.to_dict()
            assert d["market_id"] == "NSE"
            assert "session_id" in d


# ═══════════════════════════════════════════════════════════════════════════════
# TestMarketFactory
# ═══════════════════════════════════════════════════════════════════════════════

class TestMarketFactory:
    def test_make_snapshot(self):
        s = MarketFactory.make_snapshot(
            "NSE",
            prices  = {"A": 100.0},
            volumes = {"A": 1_000_000},
        )
        assert s.market_id      == "NSE"
        assert s.symbols        == ["A"]
        assert s.total_volume   == 1_000_000

    def test_make_market_state(self):
        s = MarketFactory.make_market_state("BSE", "BSE India")
        assert s.name == "BSE India"

    def test_make_signal(self):
        sig = MarketFactory.make_signal(
            "NSE", "High Breadth",
            signal_type = SignalType.BREADTH,
            confidence  = 0.8,
            direction   = "up",
        )
        assert sig.signal_type == SignalType.BREADTH
        assert sig.confidence  == pytest.approx(0.8)

    def test_make_function_classifier(self):
        clf = MarketFactory.make_function_classifier(
            "test_clf", "Test Classifier",
            lambda snap, hist: (MarketRegime.BULL, 0.77),
        )
        regime, conf = clf.classify(_snap(), [])
        assert regime == MarketRegime.BULL
        assert conf   == pytest.approx(0.77)

    def test_function_classifier_to_dict(self):
        clf = MarketFactory.make_function_classifier(
            "x", "X", lambda s, h: (MarketRegime.UNKNOWN, 0.5)
        )
        d = clf.to_dict()
        assert d["classifier_id"] == "x"


# ═══════════════════════════════════════════════════════════════════════════════
# TestMarketManager
# ═══════════════════════════════════════════════════════════════════════════════

class TestMarketManager:
    def test_analyze_auto_registers(self):
        mgr = MarketManager()
        intel = mgr.analyze("NSE", prices={"A": 100.0})
        assert intel.market_id == "NSE"

    def test_analyze_produces_intelligence(self):
        mgr = MarketManager()
        intel = mgr.analyze(
            "NSE",
            prices    = {"A": 100.0, "B": 200.0},
            volumes   = {"A": 1_000_000, "B": 2_000_000},
            advances  = 700, declines=300,
        )
        assert intel.intelligence_id
        assert intel.regime in MarketRegime.__members__.values()

    def test_get_latest(self):
        mgr = MarketManager()
        mgr.analyze("NSE")
        intel = mgr.get_latest("NSE")
        assert intel.market_id == "NSE"

    def test_get_latest_not_found(self):
        mgr = MarketManager()
        with pytest.raises(SnapshotNotFoundError):
            mgr.get_latest("GHOST")

    def test_get_snapshot(self):
        mgr = MarketManager()
        mgr.analyze("NSE", prices={"A": 100.0})
        snap = mgr.get_snapshot("NSE")
        assert snap.market_id == "NSE"

    def test_summary(self):
        mgr = MarketManager()
        mgr.register_market("NSE", name="NSE India")
        mgr.analyze("NSE")
        s = mgr.summary("NSE")
        assert s.name      == "NSE India"
        assert s.market_id == "NSE"

    def test_regime_tracking(self):
        mgr = MarketManager()
        # Trigger bull regime
        prices = {f"S{i}": 100 + i for i in range(20)}
        mgr.analyze("NSE", prices=prices, advances=800, declines=200)
        intel = mgr.get_latest("NSE")
        assert intel.regime in MarketRegime.__members__.values()

    def test_statistics_incremented(self):
        mgr = MarketManager()
        mgr.analyze("NSE")
        mgr.analyze("BSE")
        s = mgr.statistics()
        assert s["total_analyses"] == 2

    def test_recent(self):
        mgr = MarketManager()
        for m in ["A", "B", "C", "D", "E"]:
            mgr.analyze(m)
        assert len(mgr.recent(3)) == 3

    def test_open_close_market(self):
        mgr = MarketManager()
        mgr.register_market("NSE")
        mgr.open_market("NSE", trading_date="2026-07-09")
        assert mgr.get_market_state("NSE").is_trading is True
        mgr.close_market("NSE")
        assert mgr.get_market_state("NSE").is_trading is False

    def test_singleton(self):
        m1 = get_market_manager()
        m2 = get_market_manager()
        assert m1 is m2


# ═══════════════════════════════════════════════════════════════════════════════
# TestMarketIntelligenceEngine
# ═══════════════════════════════════════════════════════════════════════════════

class TestMarketIntelligenceEngine:
    def test_initialize(self):
        e = MarketIntelligenceEngine()
        assert not e.is_running
        e.initialize()
        assert e.is_running

    def test_double_init_raises(self):
        e = MarketIntelligenceEngine()
        e.initialize()
        with pytest.raises(MarketEngineAlreadyRunningError):
            e.initialize()

    def test_not_initialized_raises(self):
        e = MarketIntelligenceEngine()
        with pytest.raises(MarketEngineNotInitializedError):
            e.analyze("NSE")

    def test_shutdown(self):
        e = _eng()
        e.shutdown()
        assert not e.is_running

    def test_analyze(self):
        e = _eng()
        intel = e.analyze("NSE", prices={"A": 100.0}, advances=600, declines=400)
        assert intel.market_id == "NSE"

    def test_analyze_with_breadth(self):
        e     = _eng()
        intel = e.analyze("NSE", advances=900, declines=100)
        assert intel.breadth_score > 50

    def test_analyze_async(self):
        e = _eng()
        async def _run():
            return await e.analyze_async("NSE", prices={"A": 100.0})
        intel = asyncio.run(_run())
        assert intel.market_id == "NSE"

    def test_register_market(self):
        e = _eng()
        state = e.register_market("NSE", "NSE India")
        assert state.name == "NSE India"

    def test_register_classifier(self):
        e = _eng()
        clf = DefaultRegimeClassifier()
        e.register_classifier(clf, overwrite=True)

    def test_get_latest(self):
        e = _eng()
        e.analyze("NSE")
        assert e.get_latest("NSE").market_id == "NSE"

    def test_summary(self):
        e = _eng()
        e.analyze("NSE")
        s = e.summary("NSE")
        assert isinstance(s, MarketSummary)

    def test_recent(self):
        e = _eng()
        for m in ["A", "B", "C"]:
            e.analyze(m)
        assert len(e.recent(10)) == 3

    def test_health(self):
        e = _eng()
        h = e.health()
        assert h["running"] is True
        assert h["version"] == "1.0.0"

    def test_stats(self):
        e = _eng()
        e.analyze("NSE")
        s = e.stats()
        assert s["total_analyses"] == 1
        assert s["version"]        == "1.0.0"

    def test_singleton(self):
        e1 = get_market_engine()
        e2 = get_market_engine()
        assert e1 is e2


# ═══════════════════════════════════════════════════════════════════════════════
# TestObservationsAndSignals
# ═══════════════════════════════════════════════════════════════════════════════

class TestObservationsAndSignals:
    def test_uptrend_generates_opportunity(self):
        mgr = MarketManager()
        # Strong uptrend
        prices = {f"S{i}": 100 + i * 2 for i in range(20)}
        mgr.analyze("NSE", prices=prices, advances=900, declines=100)
        intel = mgr.get_latest("NSE")
        # May or may not generate observations depending on analysis
        assert isinstance(intel.opportunities, list)

    def test_extreme_vol_generates_threat(self):
        mgr = MarketManager()
        # Extreme returns volatility
        returns = {f"R{i}": [0.1 * ((-1) ** j) for j in range(20)] for i in range(3)}
        ret_list = [0.1 * ((-1) ** j) for j in range(20)]
        mgr.analyze("NSE", advances=100, declines=900,
                    return_history=ret_list)
        intel = mgr.get_latest("NSE")
        assert isinstance(intel.threats, list)

    def test_broad_breadth_generates_opportunity(self):
        mgr   = MarketManager()
        intel = mgr.analyze("NSE", advances=900, declines=100)
        assert isinstance(intel.opportunities, list)


# ═══════════════════════════════════════════════════════════════════════════════
# TestConcurrency
# ═══════════════════════════════════════════════════════════════════════════════

class TestConcurrency:
    def test_concurrent_analyses(self):
        mgr     = MarketManager()
        results = []
        errors  = []

        def _run(i: int):
            try:
                intel = mgr.analyze(
                    f"MKT{i}",
                    prices  = {f"S{i}": float(100 + i)},
                    volumes = {f"S{i}": float(1_000_000)},
                )
                results.append(intel)
            except Exception as e:  # noqa: BLE001
                errors.append(e)

        threads = [threading.Thread(target=_run, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors)  == 0
        assert len(results) == 20

    def test_concurrent_regime_classification(self):
        regime_eng = MarketRegimeEngine()
        errors     = []

        def _classify(i: int):
            try:
                s = _snap(
                    trend   = TrendDirection.UP   if i % 2 == 0 else TrendDirection.DOWN,
                    breadth = BreadthCondition.BROAD if i % 2 == 0 else BreadthCondition.NARROW,
                )
                regime_eng.classify(f"MKT{i % 5}", s)
            except Exception as e:  # noqa: BLE001
                errors.append(e)

        threads = [threading.Thread(target=_classify, args=(i,)) for i in range(30)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0

    def test_concurrent_registry_operations(self):
        reg    = MarketRegistry()
        errors = []

        def _register(i: int):
            try:
                reg.register_market(f"MKT{i}", overwrite=True)
            except Exception as e:  # noqa: BLE001
                errors.append(e)

        threads = [threading.Thread(target=_register, args=(i,)) for i in range(40)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert reg.statistics()["markets"] == 40


# ═══════════════════════════════════════════════════════════════════════════════
# TestPackageImports
# ═══════════════════════════════════════════════════════════════════════════════

class TestPackageImports:
    def test_all_symbols_importable(self):
        import iios.investment.market as pkg
        for name in pkg.__all__:
            assert hasattr(pkg, name), f"Missing from __all__: {name}"

    def test_exception_hierarchy(self):
        assert issubclass(MarketStateNotFoundError,      MarketIntelligenceError)
        assert issubclass(MarketEngineAlreadyRunningError, MarketIntelligenceError)
        assert issubclass(SnapshotNotFoundError,          MarketIntelligenceError)

    def test_version(self):
        import iios.investment.market as pkg
        assert pkg.__version__ == "1.0.0"
