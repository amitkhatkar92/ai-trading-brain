"""iios/investment/market/structure/trend_engine.py
Main trend analysis engine orchestrating classifier, strength analyser,
and transition detector.
"""
from __future__ import annotations

import logging
from typing import List, Optional

from iios.investment.market.market_constants import MarketStrength, TrendDirection
from iios.investment.market.structure.models import (
    Bar,
    TrendPhase,
    TrendState,
    TrendTransition,
)
from iios.investment.market.structure.swing_history import SwingHistory
from iios.investment.market.structure.trend_classifier import TrendClassifier
from iios.investment.market.structure.trend_strength import TrendStrengthAnalyzer
from iios.investment.market.structure.trend_transition import TrendTransitionDetector

logger = logging.getLogger(__name__)

_DEFAULT_TREND = TrendState(
    direction=TrendDirection.SIDEWAYS,
    strength=MarketStrength.NEUTRAL,
    phase=TrendPhase.CORRECTION,
    leg_count=0,
    current_leg_height=0.0,
    total_displacement=0.0,
    correction_depth=0.0,
    start_index=0,
    start_price=0.0,
    last_swing_index=0,
    last_swing_price=0.0,
    confirmed=False,
)


class TrendEngine:
    """Orchestrate all trend analysis components into a single TrendState."""

    def __init__(
        self,
        swing_history: SwingHistory,
        classifier: TrendClassifier,
        strength_analyzer: TrendStrengthAnalyzer,
        transition_detector: TrendTransitionDetector,
    ) -> None:
        self._history = swing_history
        self._classifier = classifier
        self._strength = strength_analyzer
        self._transitions = transition_detector
        self._state: TrendState = _DEFAULT_TREND

    # ── Public API ────────────────────────────────────────────────────────

    def update(self, bars: List[Bar]) -> TrendState:
        """Process new bars and return the updated TrendState."""
        if not bars:
            return self._state

        current_bar = bars[-1]
        sequence = self._history.get_sequence()
        direction, leg_count = self._classifier.classify(sequence)
        strength_enum, _ = self._strength.measure(sequence, direction)
        phase = self._determine_phase(sequence, direction, current_bar)
        corr_depth = self._strength.correction_depth(sequence, direction)

        highs = sequence.highs
        lows = sequence.lows

        start_index, start_price = self._find_trend_start(sequence, direction)
        last_swing_idx, last_swing_price = self._last_swing_info(sequence, direction)
        current_leg_height = abs(current_bar.close - last_swing_price) if last_swing_price else 0.0
        total_displacement = abs(current_bar.close - start_price) if start_price else 0.0

        self._state = TrendState(
            direction=direction,
            strength=strength_enum,
            phase=phase,
            leg_count=leg_count,
            current_leg_height=current_leg_height,
            total_displacement=total_displacement,
            correction_depth=corr_depth,
            start_index=start_index,
            start_price=start_price,
            last_swing_index=last_swing_idx,
            last_swing_price=last_swing_price,
            confirmed=leg_count >= 2,
        )

        # Check for transitions
        self._transitions.update(sequence, current_bar)

        return self._state

    def get_state(self) -> TrendState:
        return self._state

    def get_phase(self) -> TrendPhase:
        return self._state.phase

    def get_last_transition(self) -> Optional[TrendTransition]:
        return self._transitions.get_last_transition()

    # ── Private helpers ───────────────────────────────────────────────────

    def _determine_phase(
        self,
        sequence,
        direction: TrendDirection,
        current_bar: Bar,
    ) -> TrendPhase:
        if direction == TrendDirection.SIDEWAYS:
            return TrendPhase.CORRECTION

        if self._strength.is_accelerating(sequence, direction):
            return TrendPhase.ACCELERATION
        if self._strength.is_exhausting(sequence, direction):
            return TrendPhase.EXHAUSTION

        highs = sequence.highs
        lows = sequence.lows

        # Determine if we are in an impulse or correction leg
        if direction == TrendDirection.UP:
            if highs and lows:
                last_high = highs[0]
                last_low = lows[0]
                if last_high.index > last_low.index:
                    # Most recent swing is a high → impulse just completed, correcting
                    return TrendPhase.CORRECTION
                else:
                    return TrendPhase.IMPULSE
        elif direction == TrendDirection.DOWN:
            if highs and lows:
                last_high = highs[0]
                last_low = lows[0]
                if last_low.index > last_high.index:
                    return TrendPhase.CORRECTION
                else:
                    return TrendPhase.IMPULSE

        return TrendPhase.IMPULSE

    def _find_trend_start(self, sequence, direction: TrendDirection):
        highs = sequence.highs
        lows = sequence.lows
        if direction == TrendDirection.UP and lows:
            oldest_low = min(lows, key=lambda s: s.index)
            return oldest_low.index, oldest_low.price
        if direction == TrendDirection.DOWN and highs:
            oldest_high = min(highs, key=lambda s: s.index)
            return oldest_high.index, oldest_high.price
        return 0, 0.0

    def _last_swing_info(self, sequence, direction: TrendDirection):
        highs = sequence.highs
        lows = sequence.lows
        all_swings = highs + lows
        if not all_swings:
            return 0, 0.0
        last = max(all_swings, key=lambda s: s.index)
        return last.index, last.price
