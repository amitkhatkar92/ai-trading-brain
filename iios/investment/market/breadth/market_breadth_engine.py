"""iios/investment/market/breadth/market_breadth_engine.py
InstitutionalMarketBreadthEngine — primary entry point for the breadth layer.
"""
from __future__ import annotations

import asyncio
import logging
import threading
import uuid
from typing import Callable, Dict, List, Optional

from iios.investment.market.breadth.models import (
    BreadthData,
    BreadthEvent,
    BreadthIntelligenceSnapshot,
    BreadthRegimeType,
    DivergenceSignal,
    MarketHealthSnapshot,
    UniverseSnapshot,
)
from iios.investment.market.breadth.breadth_metric import BreadthMetric
from iios.investment.market.breadth.metric_registry import MetricRegistry
from iios.investment.market.breadth.advance_decline_metric import AdvanceDeclineMetric
from iios.investment.market.breadth.participation_rate_metric import ParticipationRateMetric
from iios.investment.market.breadth.new_high_low_metric import NewHighLowMetric
from iios.investment.market.breadth.above_ma_metric import AboveMa20Metric, AboveMa50Metric
from iios.investment.market.breadth.breadth_engine import BreadthEngine
from iios.investment.market.breadth.breadth_history import BreadthHistory
from iios.investment.market.breadth.participation_engine import ParticipationEngine
from iios.investment.market.breadth.market_health import MarketHealthAnalyzer
from iios.investment.market.breadth.divergence_engine import DivergenceEngine
from iios.investment.market.breadth.breadth_classifier import BreadthClassifier
from iios.investment.market.breadth.breadth_transition import BreadthTransitionDetector
from iios.investment.market.breadth.breadth_confidence import BreadthConfidenceCalculator

logger = logging.getLogger(__name__)


class InstitutionalMarketBreadthEngine:
    """
    Layer-6 breadth intelligence engine.

    Consumes a UniverseSnapshot (cross-sectional collection of
    SecurityObservation) and produces a BreadthIntelligenceSnapshot every
    bar.  Optional context from upstream layers (structure, regime, trend,
    liquidity, volatility) enriches divergence detection.

    Callbacks:
        on_regime_change(event: BreadthEvent)
        on_divergence(signal: DivergenceSignal)
        on_health_change(event: BreadthEvent)
        on_update(snap: BreadthIntelligenceSnapshot)
    """

    def __init__(
        self,
        universe_id: str = "default",
        metrics: Optional[List[BreadthMetric]] = None,
        window: int = 50,
        history_size: int = 500,
        *,
        breadth_engine:       Optional[BreadthEngine]             = None,
        regime_classifier:    Optional[BreadthClassifier]         = None,
        transition_detector:  Optional[BreadthTransitionDetector] = None,
        participation_engine: Optional[ParticipationEngine]       = None,
        health_analyzer:      Optional[MarketHealthAnalyzer]      = None,
        divergence_engine:    Optional[DivergenceEngine]          = None,
        confidence_calc:      Optional[BreadthConfidenceCalculator] = None,
    ) -> None:
        self.universe_id = universe_id

        # Build metric registry
        self._registry = MetricRegistry()
        _default_metrics: List[BreadthMetric] = [
            AdvanceDeclineMetric(),
            ParticipationRateMetric(),
            NewHighLowMetric(),
            AboveMa20Metric(),
            AboveMa50Metric(),
        ]
        for m in (_default_metrics if metrics is None else metrics):
            self._registry.register(m)

        # Sub-engines (DI or defaults)
        self._breadth_engine       = breadth_engine       or BreadthEngine(self._registry, window=window)
        self._regime_classifier    = regime_classifier    or BreadthClassifier()
        self._transition_detector  = transition_detector  or BreadthTransitionDetector()
        self._participation_engine = participation_engine or ParticipationEngine()
        self._health_analyzer      = health_analyzer      or MarketHealthAnalyzer()
        self._divergence_engine    = divergence_engine    or DivergenceEngine()
        self._confidence_calc      = confidence_calc      or BreadthConfidenceCalculator()

        self._history              = BreadthHistory(maxlen=history_size)
        self._events: List[BreadthEvent] = []
        self._current: Optional[BreadthIntelligenceSnapshot] = None
        self._bar_index: int = 0
        self._lock = threading.Lock()

        # Callbacks
        self.on_regime_change: Optional[Callable[[BreadthEvent], None]] = None
        self.on_divergence:    Optional[Callable[[DivergenceSignal], None]] = None
        self.on_health_change: Optional[Callable[[BreadthEvent], None]] = None
        self.on_update:        Optional[Callable[[BreadthIntelligenceSnapshot], None]] = None

    # ── Main API ──────────────────────────────────────────────────────────

    def update(
        self,
        universe: UniverseSnapshot,
        *,
        structure:  Optional[object] = None,
        regime:     Optional[object] = None,
        trend:      Optional[object] = None,
        liquidity:  Optional[object] = None,
        volatility: Optional[object] = None,
    ) -> BreadthIntelligenceSnapshot:
        with self._lock:
            return self._update_internal(
                universe, structure, regime, trend, liquidity, volatility
            )

    def update_batch(
        self,
        universes: List[UniverseSnapshot],
        *,
        structure=None,
        regime=None,
        trend=None,
        liquidity=None,
        volatility=None,
    ) -> BreadthIntelligenceSnapshot:
        snap = None
        for u in universes:
            snap = self.update(
                u,
                structure=structure,
                regime=regime,
                trend=trend,
                liquidity=liquidity,
                volatility=volatility,
            )
        if snap is None:
            raise ValueError("universes must be non-empty")
        return snap

    async def async_update(
        self,
        universe: UniverseSnapshot,
        **kwargs,
    ) -> BreadthIntelligenceSnapshot:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, lambda: self.update(universe, **kwargs)
        )

    # ── Queries ───────────────────────────────────────────────────────────

    def current(self) -> Optional[BreadthIntelligenceSnapshot]:
        return self._current

    def history(self, n: int = 20) -> List[BreadthIntelligenceSnapshot]:
        return self._history.recent(n)

    def events(self, n: int = 20) -> List[BreadthEvent]:
        return self._events[-n:]

    def current_regime(self) -> BreadthRegimeType:
        return self._transition_detector.current_regime

    def current_health(self) -> Optional[MarketHealthSnapshot]:
        if self._current is None:
            return None
        return self._current.market_health

    def is_broad_participation(self) -> bool:
        r = self.current_regime()
        return r in (
            BreadthRegimeType.BROAD_RALLY,
            BreadthRegimeType.STRONG_PARTICIPATION,
            BreadthRegimeType.HEALTHY_PARTICIPATION,
        )

    def is_broad_rally(self) -> bool:
        return self.current_regime() == BreadthRegimeType.BROAD_RALLY

    def is_broad_selloff(self) -> bool:
        return self.current_regime() == BreadthRegimeType.BROAD_SELLOFF

    def active_divergences(self) -> List[DivergenceSignal]:
        if self._current is None:
            return []
        return list(self._current.active_divergences)

    def is_strategy_bullish_breadth(self) -> bool:
        """True when broad participation + no confirmed bearish divergences."""
        if not self.is_broad_participation():
            return False
        for div in self.active_divergences():
            if div.confirmed and "bearish" in div.divergence_type.value:
                return False
        return True

    # ── Metric management ─────────────────────────────────────────────────

    def register_metric(self, metric: BreadthMetric) -> None:
        self._registry.register(metric)
        self._breadth_engine.register_metric(metric)

    def unregister_metric(self, name: str) -> None:
        self._registry.unregister(name)
        self._breadth_engine.unregister_metric(name)

    # ── Internal ──────────────────────────────────────────────────────────

    def _update_internal(
        self,
        universe: UniverseSnapshot,
        structure,
        regime,
        trend,
        liquidity,
        volatility,
    ) -> BreadthIntelligenceSnapshot:
        bar_index = self._bar_index
        self._bar_index += 1

        # 1 — Participation
        participation = self._participation_engine.update(universe)

        # 2 — Breadth data
        above_ma20_pct = participation.above_ma20_pct
        health_prev    = (
            self._current.market_health.health_score / 100
            if self._current else 0.5
        )
        breadth_data = self._breadth_engine.update(
            universe, above_ma20_pct=above_ma20_pct, health_score=health_prev
        )

        # 3 — Market health
        health = self._health_analyzer.analyze(breadth_data, participation)

        # 4 — Divergences
        market_regime_str = _extract_str(regime)
        trend_stage_str   = _extract_str(trend)
        divergences, div_events = self._divergence_engine.update(
            breadth_data, participation, health,
            bar_index=bar_index,
            universe_id=self.universe_id,
            market_regime=market_regime_str,
            trend_stage=trend_stage_str,
        )

        # 5 — Regime classification
        regime_snap = self._regime_classifier.classify(
            breadth_data,
            participation,
            health,
            previous_regime=self._transition_detector.previous_regime,
            duration_bars=self._transition_detector.duration_bars,
        )

        # 6 — Regime transition
        transition_events = self._transition_detector.update(
            regime_snap, bar_index=bar_index, universe_id=self.universe_id
        )

        # 7 — Confidence
        confidence = self._confidence_calc.calculate(
            universe, breadth_data, participation, health, regime_snap
        )

        # 8 — All events
        all_events = transition_events + div_events
        self._events.extend(all_events)
        if len(self._events) > 1000:
            self._events = self._events[-500:]

        # 9 — Build snapshot
        snap = BreadthIntelligenceSnapshot(
            snapshot_id=str(uuid.uuid4()),
            universe_id=self.universe_id,
            bar_index=bar_index,
            timestamp=universe.timestamp,
            breadth_data=breadth_data,
            participation=participation,
            market_health=health,
            regime_snapshot=regime_snap,
            active_divergences=divergences,
            confidence=confidence,
            active_events=all_events,
            last_event=all_events[-1] if all_events else None,
            market_regime=market_regime_str,
            trend_stage=trend_stage_str,
            volatility_regime=_extract_str(volatility),
            liquidity_score=_extract_float(liquidity),
        )
        self._current = snap
        self._history.append(snap)

        # 10 — Fire callbacks
        self._fire_callbacks(snap, all_events, divergences)

        logger.debug(
            "breadth_engine bar=%d regime=%s breadth=%.1f%%",
            bar_index,
            regime_snap.regime.value,
            breadth_data.breadth_pct * 100,
        )
        return snap

    def _fire_callbacks(
        self,
        snap: BreadthIntelligenceSnapshot,
        events: List[BreadthEvent],
        divergences: List[DivergenceSignal],
    ) -> None:
        if self.on_update:
            try:
                self.on_update(snap)
            except Exception:
                logger.exception("on_update callback raised")

        from iios.investment.market.breadth.models import BreadthEventType
        for ev in events:
            if ev.event_type == BreadthEventType.REGIME_CHANGE and self.on_regime_change:
                try:
                    self.on_regime_change(ev)
                except Exception:
                    logger.exception("on_regime_change callback raised")
            if ev.event_type in (
                BreadthEventType.HEALTH_IMPROVEMENT,
                BreadthEventType.HEALTH_DETERIORATION,
            ) and self.on_health_change:
                try:
                    self.on_health_change(ev)
                except Exception:
                    logger.exception("on_health_change callback raised")

        if self.on_divergence:
            for sig in divergences:
                if sig.confirmed:
                    try:
                        self.on_divergence(sig)
                    except Exception:
                        logger.exception("on_divergence callback raised")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _extract_str(ctx: object) -> Optional[str]:
    if ctx is None:
        return None
    if isinstance(ctx, str):
        return ctx
    for attr in ("regime", "trend_stage", "stage", "state", "name", "value"):
        val = getattr(ctx, attr, None)
        if val is not None:
            return str(val.value if hasattr(val, "value") else val)
    return str(ctx)


def _extract_float(ctx: object) -> Optional[float]:
    if ctx is None:
        return None
    if isinstance(ctx, (int, float)):
        return float(ctx)
    for attr in ("score", "liquidity_score", "value"):
        val = getattr(ctx, attr, None)
        if val is not None:
            try:
                return float(val)
            except (TypeError, ValueError):
                pass
    return None
