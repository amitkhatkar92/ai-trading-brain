"""iios/investment/market/liquidity/volume_liquidity_engine.py
Institutional Volume & Liquidity Intelligence Engine — authoritative source for IIOS.
"""
from __future__ import annotations

import asyncio
import logging
import threading
from collections import deque
from typing import Any, Callable, List, Optional, TYPE_CHECKING

from iios.investment.market.liquidity.models import (
    VolumeBar, VolumeProfile, ParticipationSnapshot, LiquidityProfile,
    EffortResultAnalysis, OrderFlowSnapshot, LiquidityEvent, VolumeLiquiditySnapshot,
    VolumeLevel, VolumeTrend,
)
from iios.investment.market.liquidity.volume_engine import VolumeEngine
from iios.investment.market.liquidity.participation_engine import ParticipationEngine
from iios.investment.market.liquidity.liquidity_engine import LiquidityEngine
from iios.investment.market.liquidity.volume_price_engine import VolumePriceEngine
from iios.investment.market.liquidity.order_flow_engine import OrderFlowEngine
from iios.investment.market.liquidity.liquidity_event import LiquidityEventDetector
from iios.investment.market.liquidity.liquidity_transition import LiquidityTransitionDetector
from iios.investment.market.liquidity.liquidity_alerts import LiquidityAlertGenerator
from iios.investment.market.liquidity.liquidity_confidence import LiquidityConfidenceCalculator
from iios.investment.market.liquidity.volume_quality import VolumeQualityScorer
from iios.investment.market.liquidity.liquidity_score import LiquidityScoreCalculator
from iios.investment.market.liquidity.liquidity_statistics import (
    LiquidityStatistics, VolumeLiquidityStats,
)
from iios.investment.market.liquidity.flow_statistics import FlowStats

if TYPE_CHECKING:
    from iios.investment.market.structure.models import Bar
    from iios.investment.market.regime.models import RegimeType

logger = logging.getLogger(__name__)


class InstitutionalVolumeLiquidityEngine:
    """
    Authoritative volume and liquidity intelligence source for IIOS.

    Consumes:
    - Bar (required): raw OHLCV data
    - MarketStructureSnapshot (optional): structure context
    - RegimeSnapshot (optional): regime context
    - TrendIntelligenceSnapshot (optional): trend context

    Thread-safe. Supports incremental, batch, and async updates.
    """

    def __init__(
        self,
        symbol: str,
        timeframe: str = "1d",
        volume_window: int = 20,
        volume_engine: Optional[VolumeEngine] = None,
        participation_engine: Optional[ParticipationEngine] = None,
        liquidity_engine: Optional[LiquidityEngine] = None,
        volume_price_engine: Optional[VolumePriceEngine] = None,
        order_flow_engine: Optional[OrderFlowEngine] = None,
        event_detector: Optional[LiquidityEventDetector] = None,
        transition_detector: Optional[LiquidityTransitionDetector] = None,
        alert_generator: Optional[LiquidityAlertGenerator] = None,
        confidence_calculator: Optional[LiquidityConfidenceCalculator] = None,
        volume_quality_scorer: Optional[VolumeQualityScorer] = None,
        liquidity_score_calculator: Optional[LiquidityScoreCalculator] = None,
        statistics: Optional[LiquidityStatistics] = None,
        history_size: int = 500,
    ) -> None:
        self._symbol = symbol
        self._timeframe = timeframe
        self._volume_window = volume_window

        self._volume_engine = volume_engine or VolumeEngine(window=volume_window)
        self._participation_engine = participation_engine or ParticipationEngine(window=volume_window)
        self._liquidity_engine = liquidity_engine or LiquidityEngine(window=volume_window)
        self._volume_price_engine = volume_price_engine or VolumePriceEngine(window=10)
        self._order_flow_engine = order_flow_engine or OrderFlowEngine(window=volume_window)
        self._event_detector = event_detector or LiquidityEventDetector()
        self._transition_detector = transition_detector or LiquidityTransitionDetector()
        self._alert_generator = alert_generator or LiquidityAlertGenerator()
        self._confidence_calculator = confidence_calculator or LiquidityConfidenceCalculator()
        self._volume_quality_scorer = volume_quality_scorer or VolumeQualityScorer()
        self._liquidity_score_calculator = liquidity_score_calculator or LiquidityScoreCalculator()
        self._statistics = statistics or LiquidityStatistics()

        # Rolling avg_range for EffortResult
        self._range_stats: deque[float] = deque(maxlen=volume_window)

        # History of snapshots
        self._history: deque[VolumeLiquiditySnapshot] = deque(maxlen=history_size)
        self._event_history: deque[LiquidityEvent] = deque(maxlen=history_size)

        # Thread safety
        self._lock = threading.RLock()

        # Current state
        self._current: Optional[VolumeLiquiditySnapshot] = None

        # Callbacks
        self._on_liquidity_event_cbs: List[Callable[[LiquidityEvent], None]] = []
        self._on_volume_spike_cbs: List[Callable[[VolumeLiquiditySnapshot], None]] = []
        self._on_climax_cbs: List[Callable[[VolumeLiquiditySnapshot], None]] = []
        self._on_update_cbs: List[Callable[[VolumeLiquiditySnapshot], None]] = []

    # ── Core API ──────────────────────────────────────────────────────────────

    def update(
        self,
        bar: "Bar",
        structure: Optional[Any] = None,
        regime: Optional[Any] = None,
        trend: Optional[Any] = None,
    ) -> VolumeLiquiditySnapshot:
        """Thread-safe incremental update."""
        with self._lock:
            return self._update_internal(bar, structure, regime, trend)

    def _update_internal(
        self,
        bar: "Bar",
        structure: Optional[Any],
        regime: Optional[Any],
        trend: Optional[Any],
    ) -> VolumeLiquiditySnapshot:
        # 1. Volume engine
        vbar, vol_profile = self._volume_engine.update(bar)

        # Track avg_range
        self._range_stats.append(bar.range)
        avg_range = (
            sum(self._range_stats) / len(self._range_stats)
            if self._range_stats else max(bar.range, 0.001)
        )

        # 2. Participation
        participation = self._participation_engine.update(vbar, vbar.relative_volume)

        # 3. Volume quality
        vol_quality = self._volume_quality_scorer.score(
            vbar, self._volume_engine._stats
        )

        # 4. Liquidity engine
        recent_vbars = self._volume_engine._history.recent(self._volume_window)
        regime_type = self._extract_regime(regime)
        liquidity_profile, liquidity_score = self._liquidity_engine.update(
            recent_vbars,
            vol_profile.avg_volume,
            participation,
            vol_quality,
            vol_profile,
            regime_type,
        )

        # 5. Effort-result
        er_analysis = self._volume_price_engine.update(vbar, vol_profile.avg_volume, avg_range)

        # 6. Order flow
        order_flow = self._order_flow_engine.update(vbar, vbar.relative_volume)

        # 7. Event detection
        events = self._event_detector.detect(
            vbar, vol_profile, participation, er_analysis,
            self._symbol, self._timeframe,
        )

        # 8. Transition detection
        self._transition_detector.detect(liquidity_profile, bar.index)

        # 9. Alert generation
        self._alert_generator.generate(events)

        # 10. Overall confidence
        shock_event = any(
            e.event_type.value == "shock" for e in events
        )
        has_active_events = len(events) > 0
        overall_confidence = self._confidence_calculator.calculate_confidence(
            liquidity_profile, participation, vol_quality, has_active_events, shock_event
        )

        # 11. Execution readiness
        execution_readiness = self._confidence_calculator.execution_readiness(
            liquidity_profile, order_flow, vol_quality, shock_event
        )

        # 12. Extract regime/trend context
        regime_str = self._extract_regime_str(regime)
        trend_stage_str = self._extract_trend_stage(trend)

        # 13. Build snapshot
        last_event = events[-1] if events else None
        snap = VolumeLiquiditySnapshot(
            symbol=self._symbol,
            timeframe=self._timeframe,
            bar_index=bar.index,
            timestamp=bar.timestamp,
            volume_bar=vbar,
            volume_profile=vol_profile,
            volume_level=vbar.volume_level,
            volume_trend=vol_profile.volume_trend,
            volume_quality=vol_quality,
            participation=participation,
            liquidity=liquidity_profile,
            effort_result=er_analysis,
            order_flow=order_flow,
            active_events=events,
            last_event=last_event,
            overall_confidence=overall_confidence,
            execution_readiness=execution_readiness,
            liquidity_score=liquidity_score,
            regime=regime_str,
            trend_stage=trend_stage_str,
        )

        # 14. Record in history
        self._history.append(snap)
        for e in events:
            self._event_history.append(e)

        # 15. Update statistics
        self._statistics.record(snap)

        # 16. Fire callbacks
        self._current = snap
        self._fire_callbacks(snap, events)

        return snap

    def _extract_regime(self, regime: Optional[Any]) -> Optional["RegimeType"]:
        if regime is None:
            return None
        if hasattr(regime, "primary"):
            return regime.primary
        return None

    def _extract_regime_str(self, regime: Optional[Any]) -> str:
        if regime is None:
            return "unknown"
        if hasattr(regime, "primary"):
            r = regime.primary
            return r.value if hasattr(r, "value") else str(r)
        return "unknown"

    def _extract_trend_stage(self, trend: Optional[Any]) -> str:
        if trend is None:
            return "unknown"
        if hasattr(trend, "stage"):
            s = trend.stage
            return s.value if hasattr(s, "value") else str(s)
        return "unknown"

    def _fire_callbacks(
        self,
        snap: VolumeLiquiditySnapshot,
        events: List[LiquidityEvent],
    ) -> None:
        for e in events:
            for cb in self._on_liquidity_event_cbs:
                try:
                    cb(e)
                except Exception:
                    logger.exception("Error in on_liquidity_event callback")
            if e.event_type.value == "volume_spike":
                for cb in self._on_volume_spike_cbs:
                    try:
                        cb(snap)
                    except Exception:
                        logger.exception("Error in on_volume_spike callback")
            if e.event_type.value in ("buying_climax", "selling_climax"):
                for cb in self._on_climax_cbs:
                    try:
                        cb(snap)
                    except Exception:
                        logger.exception("Error in on_climax callback")

        for cb in self._on_update_cbs:
            try:
                cb(snap)
            except Exception:
                logger.exception("Error in on_update callback")

    def update_batch(
        self,
        bars: List["Bar"],
        structure_snaps: Optional[List[Any]] = None,
        regime_snaps: Optional[List[Any]] = None,
        trend_snaps: Optional[List[Any]] = None,
    ) -> VolumeLiquiditySnapshot:
        last: Optional[VolumeLiquiditySnapshot] = None
        for i, bar in enumerate(bars):
            struct = structure_snaps[i] if structure_snaps and i < len(structure_snaps) else None
            reg = regime_snaps[i] if regime_snaps and i < len(regime_snaps) else None
            tr = trend_snaps[i] if trend_snaps and i < len(trend_snaps) else None
            last = self.update(bar, struct, reg, tr)
        if last is None:
            raise ValueError("update_batch() requires at least one bar")
        return last

    async def async_update(
        self,
        bar: "Bar",
        structure: Optional[Any] = None,
        regime: Optional[Any] = None,
        trend: Optional[Any] = None,
    ) -> VolumeLiquiditySnapshot:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, lambda: self.update(bar, structure, regime, trend)
        )

    # ── Query API ─────────────────────────────────────────────────────────────

    def current(self) -> Optional[VolumeLiquiditySnapshot]:
        return self._current

    def current_volume_level(self) -> VolumeLevel:
        if self._current is None:
            return VolumeLevel.NONE
        return self._current.volume_level

    def current_volume_trend(self) -> VolumeTrend:
        if self._current is None:
            return VolumeTrend.STABLE
        return self._current.volume_trend

    def current_liquidity_score(self) -> float:
        if self._current is None:
            return 0.0
        return self._current.liquidity_score

    def current_execution_readiness(self) -> float:
        if self._current is None:
            return 0.0
        return self._current.execution_readiness

    def current_participation(self) -> Optional[ParticipationSnapshot]:
        if self._current is None:
            return None
        return self._current.participation

    def current_order_flow(self) -> Optional[OrderFlowSnapshot]:
        if self._current is None:
            return None
        return self._current.order_flow

    def is_liquid(self, threshold: float = 50.0) -> bool:
        return self.current_liquidity_score() >= threshold

    def is_high_volume(self) -> bool:
        if self._current is None:
            return False
        return self._current.volume_bar.relative_volume >= 1.5

    def is_climax(self) -> bool:
        return self._volume_price_engine.is_in_climax()

    def is_absorption(self) -> bool:
        return self._volume_price_engine.is_in_absorption()

    def history(self, n: int = 20) -> List[VolumeLiquiditySnapshot]:
        with self._lock:
            return list(self._history)[-n:]

    def events(self, n: int = 20) -> List[LiquidityEvent]:
        with self._lock:
            return list(self._event_history)[-n:]

    def volume_profile(self) -> Optional[VolumeProfile]:
        return self._volume_engine.current_profile()

    def liquidity_profile(self) -> Optional[LiquidityProfile]:
        return self._liquidity_engine.current_profile()

    def statistics(self) -> VolumeLiquidityStats:
        return self._statistics.stats()

    def flow_statistics(self) -> FlowStats:
        return self._order_flow_engine.stats()

    # ── Event API ─────────────────────────────────────────────────────────────

    def on_liquidity_event(self, cb: Callable[[LiquidityEvent], None]) -> None:
        self._on_liquidity_event_cbs.append(cb)

    def on_volume_spike(self, cb: Callable[[VolumeLiquiditySnapshot], None]) -> None:
        self._on_volume_spike_cbs.append(cb)

    def on_climax(self, cb: Callable[[VolumeLiquiditySnapshot], None]) -> None:
        self._on_climax_cbs.append(cb)

    def on_update(self, cb: Callable[[VolumeLiquiditySnapshot], None]) -> None:
        self._on_update_cbs.append(cb)

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def symbol(self) -> str:
        return self._symbol

    @property
    def timeframe(self) -> str:
        return self._timeframe

    # ── L2 Extension ─────────────────────────────────────────────────────────

    def connect_l2_feed(self, feed: Any) -> None:
        """Future L2 integration point. Delegates to OrderFlowEngine."""
        self._order_flow_engine.connect_l2_feed(feed)
