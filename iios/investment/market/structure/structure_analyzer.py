"""iios/investment/market/structure/structure_analyzer.py
Orchestrates all detection modules for a complete structure analysis pass.
"""
from __future__ import annotations

import logging
from typing import List

from iios.investment.market.structure.market_phase import MarketPhaseDetector
from iios.investment.market.structure.models import Bar, SwingPoint
from iios.investment.market.structure.structure_state import StructureState
from iios.investment.market.structure.swing_detector import SwingDetector
from iios.investment.market.structure.swing_history import SwingHistory
from iios.investment.market.structure.trend_engine import TrendEngine

logger = logging.getLogger(__name__)


class StructureAnalyzer:
    """Orchestrates swing detection, trend analysis, and phase detection."""

    def __init__(
        self,
        swing_detector: SwingDetector,
        swing_history: SwingHistory,
        trend_engine: TrendEngine,
        phase_detector: MarketPhaseDetector,
        state: StructureState,
    ) -> None:
        self._swing_detector = swing_detector
        self._swing_history = swing_history
        self._trend_engine = trend_engine
        self._phase_detector = phase_detector
        self._state = state

    def analyze(self, bars: List[Bar]) -> StructureState:
        """Full analysis pass on bars. Returns the updated state."""
        if not bars:
            return self._state

        # 1. Detect all swings
        swings: List[SwingPoint] = self._swing_detector.detect_all(bars)
        for sw in swings:
            self._swing_history.add(sw)

        # 2. Update state swings
        sequence = self._swing_history.get_sequence()
        self._state.update_swings(sequence)

        # 3. Update trend
        trend = self._trend_engine.update(bars)
        self._state.update_trend(trend)

        # 4. Detect market phase
        phase = self._phase_detector.detect(bars, trend, sequence)
        self._state.update_phase(phase)

        # 5. Track last bar
        self._state.set_last_bar_index(bars[-1].index)

        return self._state

    def update_incremental(self, new_bar: Bar, all_bars: List[Bar]) -> StructureState:
        """Incremental update for streaming. Only re-checks the new bar."""
        if not all_bars:
            return self._state

        # Detect newly confirmed swings
        new_swings: List[SwingPoint] = self._swing_detector.process_bar(all_bars)
        for sw in new_swings:
            self._swing_history.add(sw)

        sequence = self._swing_history.get_sequence()
        self._state.update_swings(sequence)

        trend = self._trend_engine.update(all_bars)
        self._state.update_trend(trend)

        phase = self._phase_detector.detect(all_bars, trend, sequence)
        self._state.update_phase(phase)

        self._state.set_last_bar_index(new_bar.index)

        return self._state
