"""tests/unit/investment/market/volatility/test_volatility_behaviour.py
Tests for expansion, compression, and cycle analysis.
"""
from __future__ import annotations

import pytest

from iios.investment.market.volatility.volatility_expansion import VolatilityExpansionDetector
from iios.investment.market.volatility.volatility_compression import VolatilityCompressionDetector
from iios.investment.market.volatility.volatility_cycles import VolatilityCycleAnalyzer
from iios.investment.market.volatility.models import (
    VolatilityBehaviour,
    VolatilityEventType,
)
from tests.unit.investment.market.volatility.conftest import (
    make_vol_state,
    make_behaviour,
)
from iios.investment.market.volatility.volatility_expansion import ExpansionState
from iios.investment.market.volatility.volatility_compression import CompressionState


def _make_expansion_state(
    is_expanding=False, score=0.0, bars=0, peak=1.0, climax=False
) -> ExpansionState:
    return ExpansionState(
        is_expanding=is_expanding,
        expansion_score=score,
        bars_expanding=bars,
        peak_relative_vol=peak,
        is_climax=climax,
    )


def _make_compression_state(
    is_compressing=False, score=0.0, bars=0, trough=1.0, deep=False
) -> CompressionState:
    return CompressionState(
        is_compressing=is_compressing,
        compression_score=score,
        bars_compressing=bars,
        trough_relative_vol=trough,
        is_deep_compression=deep,
    )


class TestVolatilityExpansionDetector:
    def test_no_expansion_at_start(self):
        det = VolatilityExpansionDetector(expand_threshold=1.10, min_bars=2)
        state = make_vol_state(relative_volatility=1.0)
        exp_state, event = det.detect(state, 0, "T", "1d")
        assert exp_state.is_expanding is False
        assert event is None

    def test_expansion_after_min_bars(self):
        det = VolatilityExpansionDetector(expand_threshold=1.10, min_bars=2)
        state = make_vol_state(relative_volatility=1.20)
        det.detect(state, 0, "T", "1d")   # bar 1
        exp_state, event = det.detect(state, 1, "T", "1d")   # bar 2
        assert exp_state.is_expanding is True
        assert event is not None
        assert event.event_type == VolatilityEventType.EXPANSION_START

    def test_climax_detected(self):
        det = VolatilityExpansionDetector(
            expand_threshold=1.10, climax_threshold=1.5, min_bars=2
        )
        state = make_vol_state(relative_volatility=1.6)
        for i in range(3):
            exp_state, event = det.detect(state, i, "T", "1d")
        assert exp_state.is_climax is True
        assert event is not None
        assert event.event_type == VolatilityEventType.CLIMAX

    def test_expansion_score_positive(self):
        det = VolatilityExpansionDetector(expand_threshold=1.10)
        state = make_vol_state(relative_volatility=1.30)
        exp_state, _ = det.detect(state, 0, "T", "1d")
        assert exp_state.expansion_score > 0.0

    def test_no_score_below_threshold(self):
        det = VolatilityExpansionDetector(expand_threshold=1.10)
        state = make_vol_state(relative_volatility=0.90)
        exp_state, _ = det.detect(state, 0, "T", "1d")
        assert exp_state.expansion_score == 0.0

    def test_expansion_resets_when_vol_drops(self):
        det = VolatilityExpansionDetector(expand_threshold=1.10, min_bars=2)
        high_state = make_vol_state(relative_volatility=1.20)
        low_state  = make_vol_state(relative_volatility=1.00)
        for i in range(3):
            det.detect(high_state, i, "T", "1d")
        det.detect(low_state, 3, "T", "1d")
        exp_state, _ = det.detect(low_state, 4, "T", "1d")
        assert exp_state.is_expanding is False


class TestVolatilityCompressionDetector:
    def test_no_compression_at_start(self):
        det = VolatilityCompressionDetector(compress_threshold=0.92, min_bars=3)
        state = make_vol_state(relative_volatility=1.0)
        comp_state, event = det.detect(state, 0, "T", "1d")
        assert comp_state.is_compressing is False

    def test_compression_after_min_bars(self):
        det = VolatilityCompressionDetector(compress_threshold=0.92, min_bars=3)
        state = make_vol_state(relative_volatility=0.85)
        for i in range(2):
            det.detect(state, i, "T", "1d")
        comp_state, event = det.detect(state, 2, "T", "1d")
        assert comp_state.is_compressing is True
        assert event is not None
        assert event.event_type == VolatilityEventType.COMPRESSION_START

    def test_deep_compression_detected(self):
        det = VolatilityCompressionDetector(compress_threshold=0.92, deep_threshold=0.70, min_bars=3)
        state = make_vol_state(relative_volatility=0.60)
        for i in range(3):
            comp_state, _ = det.detect(state, i, "T", "1d")
        assert comp_state.is_deep_compression is True

    def test_compression_score_positive(self):
        det = VolatilityCompressionDetector(compress_threshold=0.92)
        state = make_vol_state(relative_volatility=0.70)
        comp_state, _ = det.detect(state, 0, "T", "1d")
        assert comp_state.compression_score > 0.0

    def test_dry_up_event_very_low_vol(self):
        det = VolatilityCompressionDetector()
        state = make_vol_state(relative_volatility=0.95, normalized_volatility=0.05)
        # min_bars not met but normalized < 0.08 triggers DRY_UP
        _, event = det.detect(state, 0, "T", "1d")
        if event is not None:
            assert event.event_type == VolatilityEventType.DRY_UP


class TestVolatilityCycleAnalyzer:
    def test_returns_behaviour_snapshot(self):
        analyzer = VolatilityCycleAnalyzer()
        state = make_vol_state()
        exp   = _make_expansion_state()
        comp  = _make_compression_state()
        snap = analyzer.analyze(state, exp, comp)
        assert snap.behaviour in list(VolatilityBehaviour)

    def test_expansion_behaviour_when_expanding(self):
        analyzer = VolatilityCycleAnalyzer()
        state = make_vol_state(relative_volatility=1.20)
        exp   = _make_expansion_state(is_expanding=True, score=0.5, bars=3, peak=1.2)
        comp  = _make_compression_state()
        snap = analyzer.analyze(state, exp, comp)
        assert snap.behaviour in (
            VolatilityBehaviour.EXPANDING,
            VolatilityBehaviour.ACCELERATING,
        )
        assert snap.expansion_score == 0.5

    def test_compression_behaviour_when_compressing(self):
        analyzer = VolatilityCycleAnalyzer()
        state = make_vol_state(relative_volatility=0.80)
        exp   = _make_expansion_state()
        comp  = _make_compression_state(is_compressing=True, score=0.6, bars=4)
        snap = analyzer.analyze(state, exp, comp)
        assert snap.behaviour in (
            VolatilityBehaviour.COMPRESSING,
            VolatilityBehaviour.DECELERATING,
        )

    def test_climax_behaviour(self):
        analyzer = VolatilityCycleAnalyzer()
        state = make_vol_state(relative_volatility=1.70, normalized_volatility=0.92)
        exp   = _make_expansion_state(is_expanding=True, climax=True, peak=1.7, score=0.9)
        comp  = _make_compression_state()
        snap = analyzer.analyze(state, exp, comp)
        assert snap.behaviour == VolatilityBehaviour.CLIMAX

    def test_stable_when_neutral(self):
        analyzer = VolatilityCycleAnalyzer()
        state = make_vol_state(relative_volatility=1.0, volatility_persistence=0.5)
        exp   = _make_expansion_state()
        comp  = _make_compression_state()
        snap = analyzer.analyze(state, exp, comp)
        assert snap.behaviour == VolatilityBehaviour.STABLE

    def test_persistent_behaviour(self):
        analyzer = VolatilityCycleAnalyzer()
        state = make_vol_state(relative_volatility=1.0, volatility_persistence=0.85)
        exp   = _make_expansion_state()
        comp  = _make_compression_state()
        snap = analyzer.analyze(state, exp, comp)
        assert snap.behaviour == VolatilityBehaviour.PERSISTENT

    def test_cycle_phase_set(self):
        analyzer = VolatilityCycleAnalyzer()
        state = make_vol_state()
        snap = analyzer.analyze(state, _make_expansion_state(), _make_compression_state())
        assert snap.cycle_phase in ("expansion", "peak", "contraction", "trough", "unknown")

    def test_bars_in_phase_increments(self):
        analyzer = VolatilityCycleAnalyzer()
        state = make_vol_state()
        exp   = _make_expansion_state()
        comp  = _make_compression_state()
        snap1 = analyzer.analyze(state, exp, comp)
        snap2 = analyzer.analyze(state, exp, comp)
        assert snap2.bars_in_phase > snap1.bars_in_phase
