"""iios/investment/market/structure/market_structure_engine.py
The Institutional Market Structure Engine — authoritative source of market structure.

Every component that needs market structure must consume this engine.
No other module may independently calculate market structure.

Thread-safe. Supports incremental updates for streaming use.
"""
from __future__ import annotations

import asyncio
import logging
import threading
from typing import Callable, List, Optional

from iios.investment.market.market_constants import TrendDirection
from iios.investment.market.structure.breakout_classifier import BreakoutClassifier
from iios.investment.market.structure.breakout_engine import BreakoutEngine
from iios.investment.market.structure.breakout_statistics import BreakoutStatistics
from iios.investment.market.structure.compression_detector import CompressionDetector
from iios.investment.market.structure.confidence_calculator import ConfidenceCalculator
from iios.investment.market.structure.consolidation_engine import ConsolidationEngine
from iios.investment.market.structure.false_breakout import FalseBreakoutDetector
from iios.investment.market.structure.market_phase import MarketPhaseDetector
from iios.investment.market.structure.models import (
    Bar,
    BreakoutEvent,
    ConsolidationState,
    MarketStructureSnapshot,
    StructurePhase,
    StructureQualityScore,
    SwingSequence,
    TrendState,
    TrendTransition,
    Zone,
)
from iios.investment.market.structure.range_detector import RangeDetector
from iios.investment.market.structure.structure_analyzer import StructureAnalyzer
from iios.investment.market.structure.structure_history import StructureHistory
from iios.investment.market.structure.structure_quality import StructureQualityAssessor
from iios.investment.market.structure.structure_score import StructureScorer
from iios.investment.market.structure.structure_state import StructureState
from iios.investment.market.structure.support_resistance_engine import SupportResistanceEngine
from iios.investment.market.structure.swing_detector import SwingDetector
from iios.investment.market.structure.swing_history import SwingHistory
from iios.investment.market.structure.trend_classifier import TrendClassifier
from iios.investment.market.structure.trend_engine import TrendEngine
from iios.investment.market.structure.trend_strength import TrendStrengthAnalyzer
from iios.investment.market.structure.trend_transition import TrendTransitionDetector
from iios.investment.market.structure.zone_detector import ZoneDetector
from iios.investment.market.structure.zone_registry import ZoneRegistry
from iios.investment.market.structure.zone_strength import ZoneStrengthCalculator

logger = logging.getLogger(__name__)


class InstitutionalMarketStructureEngine:
    """
    Authoritative source of market structure for the entire IIOS.

    Every component that needs market structure must consume this engine.
    No other module may independently calculate market structure.

    Thread-safe. Supports incremental updates for streaming use.
    """

    def __init__(
        self,
        symbol: str,
        timeframe: str = "1d",
        swing_detector: Optional[SwingDetector] = None,
        trend_engine: Optional[TrendEngine] = None,
        sr_engine: Optional[SupportResistanceEngine] = None,
        breakout_engine: Optional[BreakoutEngine] = None,
        consolidation_engine: Optional[ConsolidationEngine] = None,
        quality_assessor: Optional[StructureQualityAssessor] = None,
    ) -> None:
        self._symbol = symbol
        self._timeframe = timeframe
        self._lock = threading.RLock()
        self._bars: List[Bar] = []

        # Build defaults where not injected
        sw_hist = SwingHistory()
        self._swing_history = sw_hist

        self._swing_detector = swing_detector or SwingDetector()
        self._sr_engine = sr_engine or self._build_sr_engine()
        self._breakout_engine = breakout_engine or self._build_breakout_engine()
        self._consolidation_engine = consolidation_engine or self._build_consolidation_engine()
        self._quality_assessor = quality_assessor or self._build_quality_assessor()

        if trend_engine is not None:
            self._trend_engine = trend_engine
        else:
            self._trend_engine = TrendEngine(
                swing_history=sw_hist,
                classifier=TrendClassifier(),
                strength_analyzer=TrendStrengthAnalyzer(),
                transition_detector=TrendTransitionDetector(),
            )

        self._state = StructureState()
        self._history = StructureHistory()
        self._phase_detector = MarketPhaseDetector()

        self._analyzer = StructureAnalyzer(
            swing_detector=self._swing_detector,
            swing_history=sw_hist,
            trend_engine=self._trend_engine,
            phase_detector=self._phase_detector,
            state=self._state,
        )

        # Event callbacks
        self._on_trend_change: List[Callable[[TrendTransition], None]] = []
        self._on_breakout: List[Callable[[BreakoutEvent], None]] = []
        self._on_zone_break: List[Callable[[Zone], None]] = []
        self._on_structure_update: List[Callable[[MarketStructureSnapshot], None]] = []

        self._last_snapshot: Optional[MarketStructureSnapshot] = None

    # ── Core API ──────────────────────────────────────────────────────────

    def initialize(self, bars: List[Bar]) -> MarketStructureSnapshot:
        """Full initialization from historical bars."""
        with self._lock:
            self._bars = list(bars)
            self._analyzer.analyze(bars)
            self._refresh_sr_and_breakout(bars)
            self._refresh_consolidation(bars)
            self._refresh_quality(bars)
            snap = self._state.snapshot(self._symbol, self._timeframe)
            self._history.record(snap)
            self._last_snapshot = snap
            return snap

    def update(self, new_bar: Bar) -> MarketStructureSnapshot:
        """Incremental update with a single new bar. Sub-millisecond target."""
        with self._lock:
            self._bars.append(new_bar)
            self._analyzer.update_incremental(new_bar, self._bars)
            self._refresh_sr_and_breakout(self._bars)
            self._refresh_consolidation(self._bars)
            self._refresh_quality(self._bars)

            snap = self._state.snapshot(self._symbol, self._timeframe)
            self._history.record(snap)

            prev = self._last_snapshot
            self._last_snapshot = snap

            # Fire callbacks
            if prev and snap.trend.direction != prev.trend.direction:
                if snap.last_transition:
                    for cb in self._on_trend_change:
                        try:
                            cb(snap.last_transition)
                        except Exception:
                            logger.exception("Error in trend_change callback")

            if snap.active_breakout:
                for cb in self._on_breakout:
                    try:
                        cb(snap.active_breakout)
                    except Exception:
                        logger.exception("Error in breakout callback")

            for cb in self._on_structure_update:
                try:
                    cb(snap)
                except Exception:
                    logger.exception("Error in structure_update callback")

            return snap

    def update_batch(self, bars: List[Bar]) -> MarketStructureSnapshot:
        """Batch update."""
        with self._lock:
            snap: Optional[MarketStructureSnapshot] = None
            for bar in bars:
                snap = self.update(bar)
            return snap or self._state.snapshot(self._symbol, self._timeframe)

    # ── Query API ─────────────────────────────────────────────────────────

    def get_current(self) -> Optional[MarketStructureSnapshot]:
        return self._last_snapshot

    def get_trend(self) -> Optional[TrendState]:
        return self._state.get_trend()

    def get_phase(self) -> Optional[StructurePhase]:
        return self._state.get_phase()

    def get_swings(self, n: int = 10) -> SwingSequence:
        seq = self._swing_history.get_sequence()
        return SwingSequence(
            highs=seq.highs[:n],
            lows=seq.lows[:n],
            timeframe=self._timeframe,
        )

    def get_last_swing_high(self):
        return self._swing_history.get_last_high()

    def get_last_swing_low(self):
        return self._swing_history.get_last_low()

    def get_all_zones(self) -> List[Zone]:
        return self._sr_engine.get_all_zones()

    def get_nearest_resistance(self, price: float) -> Optional[Zone]:
        return self._sr_engine.get_nearest_resistance(price)

    def get_nearest_support(self, price: float) -> Optional[Zone]:
        return self._sr_engine.get_nearest_support(price)

    def get_active_breakout(self) -> Optional[BreakoutEvent]:
        return self._breakout_engine.get_active_breakout()

    def get_consolidation(self) -> Optional[ConsolidationState]:
        return self._consolidation_engine.get_active()

    def get_quality(self) -> Optional[StructureQualityScore]:
        snap = self._last_snapshot
        return snap.quality if snap else None

    # ── Historical Query ──────────────────────────────────────────────────

    def get_history(self, from_idx: int, to_idx: int) -> List[MarketStructureSnapshot]:
        return self._history.get_range(from_idx, to_idx)

    def trend_at(self, bar_index: int) -> Optional[TrendDirection]:
        snap = self._history.get_at(bar_index)
        return snap.trend.direction if snap else None

    def transitions_since(self, bar_index: int) -> List[TrendTransition]:
        return self._history.transitions_since(bar_index)

    # ── Event callbacks ───────────────────────────────────────────────────

    def on_trend_change(self, callback: Callable[[TrendTransition], None]) -> None:
        self._on_trend_change.append(callback)

    def on_breakout(self, callback: Callable[[BreakoutEvent], None]) -> None:
        self._on_breakout.append(callback)

    def on_zone_break(self, callback: Callable[[Zone], None]) -> None:
        self._on_zone_break.append(callback)

    def on_structure_update(self, callback: Callable[[MarketStructureSnapshot], None]) -> None:
        self._on_structure_update.append(callback)

    # ── Async wrappers ────────────────────────────────────────────────────

    async def async_update(self, new_bar: Bar) -> MarketStructureSnapshot:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.update, new_bar)

    async def async_initialize(self, bars: List[Bar]) -> MarketStructureSnapshot:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.initialize, bars)

    # ── Factory ───────────────────────────────────────────────────────────

    @classmethod
    def create_default(
        cls,
        symbol: str,
        timeframe: str = "1d",
    ) -> "InstitutionalMarketStructureEngine":
        """Factory method with sensible defaults."""
        return cls(symbol=symbol, timeframe=timeframe)

    # ── Internal helpers ──────────────────────────────────────────────────

    def _refresh_sr_and_breakout(self, bars: List[Bar]) -> None:
        sequence = self._swing_history.get_sequence()
        zones = self._sr_engine.update(bars, sequence)
        self._state.set_zones(zones)
        if bars:
            breakout_event = self._breakout_engine.update(bars, bars[-1])
            if breakout_event:
                self._state.update_breakout(breakout_event)
                for cb in self._on_breakout:
                    try:
                        cb(breakout_event)
                    except Exception:
                        logger.exception("Error in breakout callback")
            elif self._state.get_trend() is not None:
                # Keep existing breakout if still active
                pass

    def _refresh_consolidation(self, bars: List[Bar]) -> None:
        consol = self._consolidation_engine.update(bars)
        self._state.update_consolidation(consol)

    def _refresh_quality(self, bars: List[Bar]) -> None:
        trend = self._state.get_trend()
        if trend is None:
            return
        sequence = self._swing_history.get_sequence()
        zones = self._state.get_zones()
        breakout = self._breakout_engine.get_active_breakout()
        quality = self._quality_assessor.assess(bars, trend, sequence, zones, breakout)
        self._state.update_quality(quality)

    def _build_sr_engine(self) -> SupportResistanceEngine:
        return SupportResistanceEngine(
            detector=ZoneDetector(),
            strength_calc=ZoneStrengthCalculator(),
            registry=ZoneRegistry(),
        )

    def _build_breakout_engine(self) -> BreakoutEngine:
        registry = ZoneRegistry()
        return BreakoutEngine(
            classifier=BreakoutClassifier(),
            false_detector=FalseBreakoutDetector(),
            stats=BreakoutStatistics(),
            zone_registry=registry,
        )

    def _build_consolidation_engine(self) -> ConsolidationEngine:
        return ConsolidationEngine(
            range_detector=RangeDetector(),
            compression_detector=CompressionDetector(),
        )

    def _build_quality_assessor(self) -> StructureQualityAssessor:
        return StructureQualityAssessor(
            calculator=ConfidenceCalculator(),
            scorer=StructureScorer(),
        )
