"""iios/investment/market/structure/structure_state.py
Mutable, thread-safe state container for the current market structure.
"""
from __future__ import annotations

import logging
import threading
from typing import List, Optional

from iios.investment.market.structure.models import (
    BreakoutEvent,
    ConsolidationState,
    MarketStructureSnapshot,
    StructurePhase,
    StructureQualityScore,
    SwingPoint,
    SwingSequence,
    TrendState,
    TrendTransition,
    Zone,
)

logger = logging.getLogger(__name__)


class StructureState:
    """Thread-safe mutable container for the live market structure."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._trend: Optional[TrendState] = None
        self._phase: StructurePhase = StructurePhase.ACCUMULATION
        self._swing_sequence: SwingSequence = SwingSequence(highs=[], lows=[])
        self._active_zones: List[Zone] = []
        self._active_breakout: Optional[BreakoutEvent] = None
        self._consolidation: Optional[ConsolidationState] = None
        self._last_transition: Optional[TrendTransition] = None
        self._quality: Optional[StructureQualityScore] = None
        self._last_bar_index: int = -1

    # ── Mutators ──────────────────────────────────────────────────────────

    def update_trend(self, trend: TrendState) -> None:
        with self._lock:
            self._trend = trend

    def update_phase(self, phase: StructurePhase) -> None:
        with self._lock:
            self._phase = phase

    def update_swings(self, sequence: SwingSequence) -> None:
        with self._lock:
            self._swing_sequence = sequence

    def add_zone(self, zone: Zone) -> None:
        with self._lock:
            # Avoid duplicates
            if not any(z.zone_id == zone.zone_id for z in self._active_zones):
                self._active_zones.append(zone)

    def remove_zone(self, zone_id: str) -> None:
        with self._lock:
            self._active_zones = [z for z in self._active_zones if z.zone_id != zone_id]

    def set_zones(self, zones: List[Zone]) -> None:
        with self._lock:
            self._active_zones = list(zones)

    def update_breakout(self, event: Optional[BreakoutEvent]) -> None:
        with self._lock:
            self._active_breakout = event

    def update_consolidation(self, state: Optional[ConsolidationState]) -> None:
        with self._lock:
            self._consolidation = state

    def update_quality(self, quality: StructureQualityScore) -> None:
        with self._lock:
            self._quality = quality

    def update_transition(self, transition: Optional[TrendTransition]) -> None:
        with self._lock:
            self._last_transition = transition

    def set_last_bar_index(self, idx: int) -> None:
        with self._lock:
            self._last_bar_index = idx

    # ── Accessors ─────────────────────────────────────────────────────────

    def get_trend(self) -> Optional[TrendState]:
        with self._lock:
            return self._trend

    def get_phase(self) -> StructurePhase:
        with self._lock:
            return self._phase

    def get_zones(self) -> List[Zone]:
        with self._lock:
            return list(self._active_zones)

    def get_nearest_resistance(self, price: float) -> Optional[Zone]:
        with self._lock:
            candidates = [
                z for z in self._active_zones
                if z.lower > price and not z.broken
            ]
            if not candidates:
                return None
            return min(candidates, key=lambda z: z.lower - price)

    def get_nearest_support(self, price: float) -> Optional[Zone]:
        with self._lock:
            candidates = [
                z for z in self._active_zones
                if z.upper < price and not z.broken
            ]
            if not candidates:
                return None
            return min(candidates, key=lambda z: price - z.upper)

    # ── Snapshot ──────────────────────────────────────────────────────────

    def snapshot(self, symbol: str, timeframe: str) -> MarketStructureSnapshot:
        with self._lock:
            from iios.investment.market.market_constants import MarketStrength, TrendDirection
            from iios.investment.market.structure.models import TrendPhase

            trend = self._trend
            if trend is None:
                trend = TrendState(
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

            quality = self._quality
            if quality is None:
                quality = StructureQualityScore(
                    overall=0.0,
                    swing_confidence=0.0,
                    trend_confidence=0.0,
                    zone_confidence=0.0,
                    breakout_confidence=0.0,
                    data_quality=0.0,
                    bar_count=0,
                    valid_swing_count=0,
                )

            highs = self._swing_sequence.highs
            lows = self._swing_sequence.lows
            last_high: Optional[SwingPoint] = highs[0] if highs else None
            last_low: Optional[SwingPoint] = lows[0] if lows else None

            price_ref = (
                trend.last_swing_price
                if trend.last_swing_price
                else (last_high.price if last_high else 0.0)
            )

            return MarketStructureSnapshot(
                symbol=symbol,
                timeframe=timeframe,
                bar_index=self._last_bar_index,
                timestamp=float(self._last_bar_index),
                trend=trend,
                structure_phase=self._phase,
                last_swing_high=last_high,
                last_swing_low=last_low,
                swing_sequence=SwingSequence(
                    highs=list(highs),
                    lows=list(lows),
                    timeframe=timeframe,
                ),
                active_zones=list(self._active_zones),
                nearest_resistance=self.get_nearest_resistance(price_ref),
                nearest_support=self.get_nearest_support(price_ref),
                active_breakout=self._active_breakout,
                consolidation=self._consolidation,
                last_transition=self._last_transition,
                quality=quality,
            )
