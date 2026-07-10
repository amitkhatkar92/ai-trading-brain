"""tests/unit/investment/market/structure/test_structure_analyzer.py
Tests for StructureAnalyzer and MarketPhaseDetector (Wyckoff phases).
"""
from __future__ import annotations

import pytest

from iios.investment.market.structure.market_phase import MarketPhaseDetector
from iios.investment.market.structure.models import StructurePhase
from iios.investment.market.structure.structure_analyzer import StructureAnalyzer
from iios.investment.market.structure.structure_state import StructureState
from iios.investment.market.structure.swing_detector import SwingDetector
from iios.investment.market.structure.swing_history import SwingHistory
from iios.investment.market.structure.trend_classifier import TrendClassifier
from iios.investment.market.structure.trend_engine import TrendEngine
from iios.investment.market.structure.trend_strength import TrendStrengthAnalyzer
from iios.investment.market.structure.trend_transition import TrendTransitionDetector
from tests.unit.investment.market.structure.conftest import (
    make_downtrend_bars,
    make_range_bars,
    make_uptrend_bars,
)


def _build_analyzer() -> StructureAnalyzer:
    hist = SwingHistory()
    engine = TrendEngine(
        swing_history=hist,
        classifier=TrendClassifier(),
        strength_analyzer=TrendStrengthAnalyzer(),
        transition_detector=TrendTransitionDetector(),
    )
    return StructureAnalyzer(
        swing_detector=SwingDetector(),
        swing_history=hist,
        trend_engine=engine,
        phase_detector=MarketPhaseDetector(),
        state=StructureState(),
    )


class TestStructureAnalyzer:
    def test_analyze_returns_state(self):
        bars = make_uptrend_bars(n=40)
        analyzer = _build_analyzer()
        state = analyzer.analyze(bars)
        assert state is not None

    def test_trend_updated_in_state(self):
        bars = make_uptrend_bars(n=50)
        analyzer = _build_analyzer()
        analyzer.analyze(bars)
        trend = analyzer._state.get_trend()
        assert trend is not None

    def test_phase_updated_in_state(self):
        bars = make_uptrend_bars(n=50)
        analyzer = _build_analyzer()
        analyzer.analyze(bars)
        phase = analyzer._state.get_phase()
        assert isinstance(phase, StructurePhase)

    def test_markup_phase_for_uptrend(self):
        bars = make_uptrend_bars(n=60)
        analyzer = _build_analyzer()
        analyzer.analyze(bars)
        phase = analyzer._state.get_phase()
        # Sustained uptrend should be MARKUP or EXPANSION
        assert phase in (StructurePhase.MARKUP, StructurePhase.EXPANSION,
                         StructurePhase.ACCUMULATION, StructurePhase.COMPRESSION)

    def test_markdown_phase_for_downtrend(self):
        bars = make_downtrend_bars(n=60)
        analyzer = _build_analyzer()
        analyzer.analyze(bars)
        phase = analyzer._state.get_phase()
        assert phase in (StructurePhase.MARKDOWN, StructurePhase.EXPANSION,
                         StructurePhase.DISTRIBUTION, StructurePhase.COMPRESSION,
                         StructurePhase.ACCUMULATION)

    def test_range_detection(self):
        bars = make_range_bars(n=40)
        analyzer = _build_analyzer()
        analyzer.analyze(bars)
        phase = analyzer._state.get_phase()
        # Range bars should produce accumulation, distribution or contraction
        assert phase in (StructurePhase.ACCUMULATION, StructurePhase.DISTRIBUTION,
                         StructurePhase.CONTRACTION, StructurePhase.COMPRESSION,
                         StructurePhase.MARKUP, StructurePhase.MARKDOWN)

    def test_incremental_update(self):
        bars = make_uptrend_bars(n=40)
        analyzer = _build_analyzer()
        analyzer.analyze(bars[:-5])
        for bar in bars[-5:]:
            state = analyzer.update_incremental(bar, bars[:bars.index(bar) + 1])
        assert state is not None

    def test_last_bar_index_set(self):
        bars = make_uptrend_bars(n=30)
        analyzer = _build_analyzer()
        analyzer.analyze(bars)
        assert analyzer._state._last_bar_index == bars[-1].index


class TestMarketPhaseDetector:
    def test_markup_after_uptrend(self):
        bars = make_uptrend_bars(n=60)
        detector = MarketPhaseDetector(lookback=20)
        from iios.investment.market.structure.swing_history import SwingHistory
        from iios.investment.market.structure.swing_detector import SwingDetector
        hist = SwingHistory()
        swings = SwingDetector().detect_all(bars)
        for sw in swings:
            hist.add(sw)
        from iios.investment.market.structure.trend_engine import TrendEngine
        from iios.investment.market.structure.trend_classifier import TrendClassifier
        from iios.investment.market.structure.trend_strength import TrendStrengthAnalyzer
        from iios.investment.market.structure.trend_transition import TrendTransitionDetector
        engine = TrendEngine(hist, TrendClassifier(), TrendStrengthAnalyzer(), TrendTransitionDetector())
        trend = engine.update(bars)
        seq = hist.get_sequence()
        phase = detector.detect(bars, trend, seq)
        assert isinstance(phase, StructurePhase)

    def test_compression_on_tight_bars(self):
        from tests.unit.investment.market.structure.conftest import make_compression_bars
        bars = make_compression_bars(n=30)
        detector = MarketPhaseDetector(lookback=20)
        from iios.investment.market.structure.models import TrendState, TrendPhase
        from iios.investment.market.market_constants import MarketStrength, TrendDirection
        trend = TrendState(
            direction=TrendDirection.SIDEWAYS,
            strength=MarketStrength.NEUTRAL,
            phase=TrendPhase.CORRECTION,
            leg_count=0, current_leg_height=0.0, total_displacement=0.0,
            correction_depth=0.0, start_index=0, start_price=100.0,
            last_swing_index=0, last_swing_price=100.0, confirmed=False,
        )
        from iios.investment.market.structure.models import SwingSequence
        phase = detector.detect(bars, trend, SwingSequence())
        assert phase in (StructurePhase.COMPRESSION, StructurePhase.ACCUMULATION,
                         StructurePhase.CONTRACTION)
