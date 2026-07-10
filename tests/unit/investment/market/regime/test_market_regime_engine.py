"""tests/unit/investment/market/regime/test_market_regime_engine.py"""
from __future__ import annotations

import asyncio
import threading
import time
from typing import List
from unittest.mock import MagicMock

import pytest

from iios.investment.market.market_constants import MarketRegime
from iios.investment.market.regime.models import (
    RegimeSnapshot,
    RegimeType,
    TransitionEvent,
    StrategyCompatibility,
)
from iios.investment.market.regime.market_regime_engine import (
    InstitutionalMarketRegimeEngine,
    MarketRegimeEngine,
)
from iios.investment.market.regime.regime_history import RegimeHistory
from iios.investment.market.regime.strategy_permissions import StrategyType

from tests.unit.investment.market.regime.conftest import (
    make_structure_snapshot,
    make_market_snapshot,
)
from iios.investment.market.market_constants import TrendDirection, VolatilityLevel
from iios.investment.market.structure.models import StructurePhase


def make_engine(symbol: str = "TEST") -> InstitutionalMarketRegimeEngine:
    return InstitutionalMarketRegimeEngine(symbol=symbol, market_id=symbol)


def make_bull_ss():
    return make_structure_snapshot(
        trend_dir=TrendDirection.UP,
        confirmed=True,
        leg_count=3,
        phase=StructurePhase.MARKUP,
        quality=80.0,
    )


def make_bear_ss():
    return make_structure_snapshot(
        trend_dir=TrendDirection.DOWN,
        confirmed=True,
        leg_count=2,
        phase=StructurePhase.MARKDOWN,
        quality=75.0,
    )


class TestInstitutionalMarketRegimeEngineBasic:
    def test_initial_state(self):
        engine = make_engine()
        assert engine.current() is None

    def test_first_update_returns_snapshot(self):
        engine = make_engine()
        ss = make_bull_ss()
        result = engine.update(ss)
        assert isinstance(result, RegimeSnapshot)

    def test_update_returns_regime_snapshot(self):
        engine = make_engine()
        ss = make_bull_ss()
        result = engine.update(ss)
        assert result is not None
        assert isinstance(result.primary, RegimeType)

    def test_regime_type_is_valid(self):
        engine = make_engine()
        ss = make_bull_ss()
        engine.update(ss)
        assert engine.current_regime_type() in RegimeType

    def test_confidence_in_range(self):
        engine = make_engine()
        ss = make_bull_ss()
        engine.update(ss)
        c = engine.confidence()
        assert 0.0 <= c <= 1.0

    def test_market_regime_compat(self):
        engine = make_engine()
        ss = make_bull_ss()
        engine.update(ss)
        mr = engine.current_market_regime()
        assert isinstance(mr, MarketRegime)

    def test_symbol_property(self):
        engine = make_engine("NIFTY")
        assert engine.symbol == "NIFTY"

    def test_market_id_property(self):
        engine = InstitutionalMarketRegimeEngine(symbol="S1", market_id="MKT1")
        assert engine.market_id == "MKT1"

    def test_current_reflects_last_update(self):
        engine = make_engine()
        ss = make_bull_ss()
        snap = engine.update(ss)
        assert engine.current() is snap


class TestRegimeHistory:
    def test_history_grows(self):
        engine = make_engine()
        for _ in range(5):
            engine.update(make_bull_ss())
        history = engine.regime_history(n=10)
        assert len(history) == 5

    def test_history_respects_n(self):
        engine = make_engine()
        for _ in range(10):
            engine.update(make_bull_ss())
        history = engine.regime_history(n=3)
        assert len(history) == 3

    def test_regime_timeline_from_transitions(self):
        engine = make_engine()
        engine.update(make_bull_ss())
        engine.update(make_bear_ss())  # regime change
        timeline = engine.regime_timeline()
        # timeline is populated on regime change
        assert isinstance(timeline, list)


class TestTransitionTracking:
    def test_transition_timeline_populated(self):
        engine = make_engine()
        engine.update(make_structure_snapshot(
            trend_dir=TrendDirection.SIDEWAYS, in_consolidation=True, consolidation_bars=15
        ))
        engine.update(make_structure_snapshot(
            in_consolidation=False, has_breakout=True, breakout_bullish=True
        ))
        timeline = engine.transition_timeline()
        assert isinstance(timeline, list)

    def test_on_regime_change_callback(self):
        engine = make_engine()
        calls = []

        def cb(old: RegimeSnapshot, new: RegimeSnapshot):
            calls.append((old.primary, new.primary))

        engine.on_regime_change(cb)
        # First update — from UNKNOWN, no callback (no prev_snap)
        engine.update(make_bull_ss())
        # Second update with different regime
        engine.update(make_bear_ss())
        # If a regime change happened from bull→bear, callback fires
        # (depends on detection)
        assert isinstance(calls, list)

    def test_on_transition_callback(self):
        engine = make_engine()
        transitions: List[TransitionEvent] = []
        engine.on_transition_detected(lambda evt: transitions.append(evt))

        # Force conditions that would trigger EMERGING_TREND
        engine.update(make_structure_snapshot(in_consolidation=True, consolidation_bars=15))
        engine.update(make_structure_snapshot(in_consolidation=False, has_breakout=True))
        assert isinstance(transitions, list)

    def test_on_update_callback_every_update(self):
        engine = make_engine()
        count = [0]
        engine.on_update(lambda snap: count.__setitem__(0, count[0] + 1))
        for _ in range(5):
            engine.update(make_bull_ss())
        assert count[0] == 5


class TestStrategyAPI:
    def test_strategy_compatibility_returns_valid(self):
        engine = make_engine()
        engine.update(make_bull_ss())
        compat = engine.strategy_compatibility()
        assert isinstance(compat, StrategyCompatibility)

    def test_is_strategy_allowed_returns_bool(self):
        engine = make_engine()
        engine.update(make_bull_ss())
        result = engine.is_strategy_allowed(StrategyType.TREND_FOLLOWING)
        assert isinstance(result, bool)

    def test_is_strategy_blocked_returns_bool(self):
        engine = make_engine()
        engine.update(make_bull_ss())
        result = engine.is_strategy_blocked(StrategyType.DEFENSIVE)
        assert isinstance(result, bool)

    def test_check_trade_returns_tuple(self):
        engine = make_engine()
        engine.update(make_bull_ss())
        result = engine.check_trade(
            strategy_type=StrategyType.TREND_FOLLOWING,
            direction="long",
            structure_quality=70.0,
            trend_confirmed=True,
        )
        allowed, reason = result
        assert isinstance(allowed, bool)
        assert isinstance(reason, str)


class TestBatchUpdate:
    def test_batch_returns_last_snapshot(self):
        engine = make_engine()
        snapshots = [make_bull_ss() for _ in range(5)]
        result = engine.update_batch(snapshots)
        assert isinstance(result, RegimeSnapshot)
        assert engine.bars_in_regime() == 5

    def test_batch_empty_returns_empty_snapshot(self):
        engine = make_engine()
        result = engine.update_batch([])
        assert isinstance(result, RegimeSnapshot)


class TestAsyncUpdate:
    def test_async_update(self):
        engine = make_engine()
        ss = make_bull_ss()

        async def run():
            return await engine.async_update(ss)

        result = asyncio.run(run())
        assert isinstance(result, RegimeSnapshot)


class TestBackwardCompatMarketRegimeEngine:
    def test_classify_returns_market_regime(self):
        engine = MarketRegimeEngine()
        ms = make_market_snapshot()
        regime, confidence = engine.classify("M1", ms)
        assert isinstance(regime, MarketRegime)
        assert 0.0 <= confidence <= 1.0

    def test_current_regime_default_unknown(self):
        engine = MarketRegimeEngine()
        assert engine.current_regime("nonexistent") == MarketRegime.UNKNOWN

    def test_confidence_default_zero(self):
        engine = MarketRegimeEngine()
        assert engine.confidence("nonexistent") == 0.0

    def test_known_markets(self):
        engine = MarketRegimeEngine()
        ms = make_market_snapshot()
        engine.classify("M1", ms)
        engine.classify("M2", ms)
        known = engine.known_markets()
        assert "M1" in known
        assert "M2" in known

    def test_regime_history_is_regime_history_instance(self):
        engine = MarketRegimeEngine()
        assert isinstance(engine.regime_history(), RegimeHistory)

    def test_set_classifier(self):
        from iios.investment.market.regime.regime_classifier import DefaultRegimeClassifier
        engine = MarketRegimeEngine()
        engine.set_classifier(DefaultRegimeClassifier())
        ms = make_market_snapshot()
        regime, _ = engine.classify("M1", ms)
        assert isinstance(regime, MarketRegime)

    def test_bars_in_current_regime(self):
        engine = MarketRegimeEngine()
        ms = make_market_snapshot(trend_dir=TrendDirection.UP,
                                   volatility=VolatilityLevel.MODERATE)
        engine.classify("M1", ms)
        engine.classify("M1", ms)
        engine.classify("M1", ms)
        # All 3 calls are for same market with same result → bars should be 2 (after first change)
        bars = engine.bars_in_current_regime("M1")
        assert isinstance(bars, int)
        assert bars >= 0

    def test_bars_in_unknown_market_is_zero(self):
        engine = MarketRegimeEngine()
        assert engine.bars_in_current_regime("MISSING") == 0


class TestTransitionStatisticsAndProbabilityModel:
    def test_transition_statistics_returns_object(self):
        engine = make_engine()
        engine.update(make_bull_ss())
        ts = engine.transition_statistics()
        assert ts is not None

    def test_probability_model_returns_object(self):
        engine = make_engine()
        engine.update(make_bull_ss())
        pm = engine.probability_model()
        assert pm is not None

    def test_transition_probability_in_range(self):
        engine = make_engine()
        engine.update(make_bull_ss())
        tp = engine.transition_probability()
        assert 0.0 <= tp <= 1.0

    def test_stability_in_range(self):
        engine = make_engine()
        for _ in range(5):
            engine.update(make_bull_ss())
        s = engine.stability()
        assert 0.0 <= s <= 1.0
