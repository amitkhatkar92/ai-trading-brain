"""iios/investment/market/trend/trend_intelligence_engine.py
Institutional Trend Intelligence Engine — authoritative trend intelligence for IIOS.
"""
from __future__ import annotations

import asyncio
import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple, TYPE_CHECKING

from iios.investment.market.market_constants import TrendDirection
from iios.investment.market.regime.models import RegimeType
from iios.investment.market.trend.models import (
    TrendStage,
    TrendEventType,
    TrendEventRecord,
    TrendTransitionRecord,
    TrendQualityMetrics,
    TrendMomentumState,
    TrendScore,
    StrategyReadiness,
    TrendIntelligenceSnapshot,
)
from iios.investment.market.trend.trend_state import TrendIntelligenceState
from iios.investment.market.trend.trend_tracker import TrendTracker
from iios.investment.market.trend.trend_history import TrendHistory
from iios.investment.market.trend.trend_snapshot import TrendSnapshotBuilder, _is_regime_aligned
from iios.investment.market.trend.trend_quality import TrendQualityAnalyzer
from iios.investment.market.trend.trend_strength import TrendStrengthCalculator
from iios.investment.market.trend.trend_stability import TrendStabilityCalculator
from iios.investment.market.trend.trend_persistence import TrendPersistenceCalculator
from iios.investment.market.trend.trend_momentum import TrendMomentumAnalyzer
from iios.investment.market.trend.trend_lifecycle import TrendLifecycleDetector
from iios.investment.market.trend.trend_transition import TrendTransitionDetector
from iios.investment.market.trend.trend_confidence import TrendConfidenceCalculator
from iios.investment.market.trend.trend_score import TrendScorer
from iios.investment.market.trend.trend_statistics import TrendStatistics
from iios.investment.market.trend.trend_strategy_mapper import TrendStrategyMapper

if TYPE_CHECKING:
    from iios.investment.market.structure.models import MarketStructureSnapshot
    from iios.investment.market.regime.models import RegimeSnapshot

logger = logging.getLogger(__name__)


class InstitutionalTrendIntelligenceEngine:
    """
    Authoritative trend intelligence source for IIOS.

    Consumes:
    - MarketStructureSnapshot from InstitutionalMarketStructureEngine
    - RegimeSnapshot from InstitutionalMarketRegimeEngine (optional but recommended)

    Does NOT independently calculate swings, pivots, or market structure.

    Thread-safe. Supports incremental, batch, and async updates.

    Contract:
    - Every strategy must query this engine for trend intelligence
    - No strategy computes trend independently
    - Engine is the single canonical trend intelligence model
    """

    def __init__(
        self,
        symbol: str,
        timeframe: str = "1d",
        tracker_window: int = 30,
        tracker: Optional[TrendTracker] = None,
        quality_analyzer: Optional[TrendQualityAnalyzer] = None,
        strength_calculator: Optional[TrendStrengthCalculator] = None,
        stability_calculator: Optional[TrendStabilityCalculator] = None,
        persistence_calculator: Optional[TrendPersistenceCalculator] = None,
        momentum_analyzer: Optional[TrendMomentumAnalyzer] = None,
        lifecycle_detector: Optional[TrendLifecycleDetector] = None,
        transition_detector: Optional[TrendTransitionDetector] = None,
        confidence_calculator: Optional[TrendConfidenceCalculator] = None,
        scorer: Optional[TrendScorer] = None,
        strategy_mapper: Optional[TrendStrategyMapper] = None,
        statistics: Optional[TrendStatistics] = None,
        history_size: int = 500,
    ) -> None:
        self._symbol = symbol
        self._timeframe = timeframe

        self._tracker = tracker or TrendTracker(window=tracker_window)
        self._quality_analyzer = quality_analyzer or TrendQualityAnalyzer()
        self._strength_calc = strength_calculator or TrendStrengthCalculator()
        self._stability_calc = stability_calculator or TrendStabilityCalculator()
        self._persistence_calc = persistence_calculator or TrendPersistenceCalculator()
        self._momentum_analyzer = momentum_analyzer or TrendMomentumAnalyzer()
        self._lifecycle_detector = lifecycle_detector or TrendLifecycleDetector()
        self._transition_detector = transition_detector or TrendTransitionDetector()
        self._confidence_calc = confidence_calculator or TrendConfidenceCalculator()
        self._scorer = scorer or TrendScorer()
        self._strategy_mapper = strategy_mapper or TrendStrategyMapper()
        self._statistics = statistics or TrendStatistics()

        self._state = TrendIntelligenceState(symbol, timeframe)
        self._history = TrendHistory(max_size=history_size)
        self._snapshot_builder = TrendSnapshotBuilder()

        self._lock = threading.RLock()

        # Callbacks
        self._on_update_cbs: List[Callable[[TrendIntelligenceSnapshot], None]] = []
        self._on_stage_change_cbs: List[Callable[[TrendIntelligenceSnapshot, TrendIntelligenceSnapshot], None]] = []
        self._on_transition_cbs: List[Callable[[TrendTransitionRecord], None]] = []
        self._on_event_cbs: List[Callable[[TrendEventRecord], None]] = []

        # Event timeline
        self._events: List[TrendEventRecord] = []

    # ── Core API ──────────────────────────────────────────────────────────────

    def update(
        self,
        structure_snapshot: "MarketStructureSnapshot",
        regime_snapshot: Optional["RegimeSnapshot"] = None,
    ) -> TrendIntelligenceSnapshot:
        """Thread-safe incremental update."""
        with self._lock:
            return self._update_internal(structure_snapshot, regime_snapshot)

    def _update_internal(
        self,
        structure: "MarketStructureSnapshot",
        regime: Optional["RegimeSnapshot"],
    ) -> TrendIntelligenceSnapshot:
        # 1. Track structure
        self._tracker.update(structure)

        # 2. Compute legs
        legs = self._tracker.compute_leg_metrics()

        # 3. Extract trend state fields
        trend_state = structure.trend
        direction = trend_state.direction
        phase_str = trend_state.phase.value
        correction_depth = trend_state.correction_depth

        # 4. Compute momentum
        momentum = self._momentum_analyzer.analyze(
            legs, direction, phase_str, correction_depth
        )

        # 5. Previous stage
        prev_snap = self._state.current()
        prev_stage = prev_snap.stage if prev_snap is not None else TrendStage.EMERGING
        prev_direction = prev_snap.direction if prev_snap is not None else TrendDirection.UNDEFINED

        # 6. Detect lifecycle stage
        stage, stage_confidence = self._lifecycle_detector.detect(
            trend_state, legs, momentum, prev_stage
        )

        # 7. Regime info
        regime_type = regime.primary if regime is not None else RegimeType.UNKNOWN
        regime_stability = regime.stability if regime is not None else 0.5
        regime_confidence = regime.confidence if regime is not None else 0.5
        regime_aligned = _is_regime_aligned(direction, regime_type)

        # 8. Quality
        quality = self._quality_analyzer.analyze(
            legs,
            structure_quality=structure.quality.overall,
            correction_depth=correction_depth,
            regime_stability=regime_stability,
        )

        # 9. Persistence — update quality.persistence
        persistence = self._persistence_calc.calculate(
            stage, quality, regime_aligned,
            momentum.is_accelerating, momentum.is_decelerating
        )
        quality = TrendQualityMetrics(
            smoothness=quality.smoothness,
            reliability=quality.reliability,
            efficiency=quality.efficiency,
            consistency=quality.consistency,
            stability=quality.stability,
            persistence=persistence,
            overall=quality.overall,
        )

        # 10. Confidence
        confidence = self._confidence_calc.calculate(
            trend_state, stage, quality, momentum, regime_aligned,
            structure.quality.overall
        )

        # 11. Probabilities
        continuation_prob = self._confidence_calc.continuation_probability(
            stage, quality, momentum, regime_aligned
        )
        failure_prob = self._confidence_calc.failure_probability(stage, momentum)
        reversal_prob = self._confidence_calc.reversal_probability(
            phase_str, stage, correction_depth
        )
        remaining_legs = self._confidence_calc.expected_remaining_legs(
            stage, trend_state.leg_count, quality
        )

        # 12. Strategy readiness
        readiness = self._strategy_mapper.readiness(
            stage, direction, quality, momentum, confidence
        )

        # 13. Score
        score = self._scorer.score(
            quality, momentum, stage, regime_aligned, regime_confidence
        )

        # 14. Detect transition / event
        transition = self._transition_detector.detect(
            prev_stage=prev_stage,
            new_stage=stage,
            prev_direction=prev_direction,
            new_direction=direction,
            confidence=confidence,
            bar_index=structure.bar_index,
            symbol=self._symbol,
            timeframe=self._timeframe,
        )

        last_event: Optional[TrendEventRecord] = None
        if transition is not None:
            self._history.record_transition(transition)
            event_type = self._lifecycle_detector.detect_event(
                prev_stage, stage, trend_state
            )
            if event_type is not None:
                last_event = TrendEventRecord(
                    event_type=event_type,
                    symbol=self._symbol,
                    timeframe=self._timeframe,
                    timestamp=structure.timestamp,
                    bar_index=structure.bar_index,
                    stage_before=prev_stage,
                    stage_after=stage,
                    description=f"{prev_stage.value}→{stage.value}",
                )
                self._events.append(last_event)
                self._statistics.record_event(event_type)

        # 15. Build snapshot
        snap = self._snapshot_builder.build(
            symbol=self._symbol,
            timeframe=self._timeframe,
            structure=structure,
            regime=regime,
            stage=stage,
            stage_confidence=stage_confidence,
            quality=quality,
            momentum=momentum,
            confidence=confidence,
            continuation_probability=continuation_prob,
            failure_probability=failure_prob,
            reversal_probability=reversal_prob,
            expected_remaining_legs=remaining_legs,
            strategy_readiness=readiness,
            score=score,
            last_event=last_event,
        )

        # 16. Update state
        stage_changed = self._state.update(snap)

        # 17. Record in history
        self._history.record(snap)

        # 18. Update statistics
        if stage_changed and prev_snap is not None:
            bars_in_prev = max(0, structure.bar_index - (prev_snap.bar_index if prev_snap else 0))
            self._statistics.record_stage_end(prev_stage, bars_in_prev, confidence)

        # 19. Fire callbacks
        for cb in self._on_update_cbs:
            try:
                cb(snap)
            except Exception:
                logger.warning("on_update callback raised", exc_info=True)

        if stage_changed and prev_snap is not None:
            for cb in self._on_stage_change_cbs:
                try:
                    cb(prev_snap, snap)
                except Exception:
                    logger.warning("on_stage_change callback raised", exc_info=True)

        if transition is not None:
            for cb in self._on_transition_cbs:
                try:
                    cb(transition)
                except Exception:
                    logger.warning("on_transition callback raised", exc_info=True)

        if last_event is not None:
            for cb in self._on_event_cbs:
                try:
                    cb(last_event)
                except Exception:
                    logger.warning("on_event callback raised", exc_info=True)

        return snap

    def update_batch(
        self,
        structure_snapshots: List["MarketStructureSnapshot"],
        regime_snapshots: Optional[List["RegimeSnapshot"]] = None,
    ) -> TrendIntelligenceSnapshot:
        """Process a list. Returns final snapshot."""
        last: Optional[TrendIntelligenceSnapshot] = None
        for i, struct in enumerate(structure_snapshots):
            regime = None
            if regime_snapshots and i < len(regime_snapshots):
                regime = regime_snapshots[i]
            last = self.update(struct, regime)
        if last is None:
            return TrendIntelligenceSnapshot(symbol=self._symbol, timeframe=self._timeframe)
        return last

    async def async_update(
        self,
        structure_snapshot: "MarketStructureSnapshot",
        regime_snapshot: Optional["RegimeSnapshot"] = None,
    ) -> TrendIntelligenceSnapshot:
        """Async wrapper using run_in_executor."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self.update, structure_snapshot, regime_snapshot
        )

    # ── Query API ─────────────────────────────────────────────────────────────

    def current(self) -> Optional[TrendIntelligenceSnapshot]:
        return self._state.current()

    def current_stage(self) -> TrendStage:
        return self._state.current_stage()

    def current_direction(self) -> TrendDirection:
        return self._state.current_direction()

    def current_confidence(self) -> float:
        snap = self._state.current()
        return snap.confidence if snap is not None else 0.0

    def current_quality(self) -> Optional[TrendQualityMetrics]:
        snap = self._state.current()
        return snap.quality if snap is not None else None

    def current_momentum(self) -> Optional[TrendMomentumState]:
        snap = self._state.current()
        return snap.momentum if snap is not None else None

    def strategy_readiness(self) -> Optional[StrategyReadiness]:
        snap = self._state.current()
        return snap.strategy_readiness if snap is not None else None

    def continuation_probability(self) -> float:
        snap = self._state.current()
        return snap.continuation_probability if snap is not None else 0.0

    def failure_probability(self) -> float:
        snap = self._state.current()
        return snap.failure_probability if snap is not None else 0.0

    def reversal_probability(self) -> float:
        snap = self._state.current()
        return snap.reversal_probability if snap is not None else 0.0

    def history(self, n: int = 20) -> List[TrendIntelligenceSnapshot]:
        """Last n snapshots, most recent last."""
        return self._history.recent(n)

    def trend_timeline(self) -> List[TrendEventRecord]:
        """All recorded events in chronological order."""
        with self._lock:
            return list(self._events)

    def transition_timeline(self) -> List[TrendTransitionRecord]:
        """All detected stage transitions."""
        return self._history.get_transitions()

    def statistics(self) -> TrendStatistics:
        return self._statistics

    def is_strategy_suitable(self, strategy_type: str) -> bool:
        snap = self._state.current()
        if snap is None:
            return False
        return self._strategy_mapper.is_suitable(strategy_type, snap.stage)

    def check_trade(
        self,
        strategy_type: str,
        direction: str,
        confidence: float = 0.0,
        quality_overall: float = 0.0,
        trend_confirmed: bool = False,
    ) -> Tuple[bool, str]:
        snap = self._state.current()
        if snap is None:
            return (False, "No trend data available")
        return self._strategy_mapper.check_trade(
            strategy_type=strategy_type,
            stage=snap.stage,
            direction=direction,
            confidence=confidence or snap.confidence,
            quality_overall=quality_overall or snap.quality.overall,
            trend_confirmed=trend_confirmed or snap.confirmed,
        )

    # ── Event API ─────────────────────────────────────────────────────────────

    def on_stage_change(
        self,
        cb: Callable[["TrendIntelligenceSnapshot", "TrendIntelligenceSnapshot"], None],
    ) -> None:
        self._on_stage_change_cbs.append(cb)

    def on_transition(self, cb: Callable[[TrendTransitionRecord], None]) -> None:
        self._on_transition_cbs.append(cb)

    def on_event(self, cb: Callable[[TrendEventRecord], None]) -> None:
        self._on_event_cbs.append(cb)

    def on_update(self, cb: Callable[["TrendIntelligenceSnapshot"], None]) -> None:
        self._on_update_cbs.append(cb)

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def symbol(self) -> str:
        return self._symbol

    @property
    def timeframe(self) -> str:
        return self._timeframe
