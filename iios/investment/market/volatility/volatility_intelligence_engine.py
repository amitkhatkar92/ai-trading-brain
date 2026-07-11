"""iios/investment/market/volatility/volatility_intelligence_engine.py
InstitutionalVolatilityIntelligenceEngine — primary entry point.

Orchestrates all sub-engines to produce a VolatilityIntelligenceSnapshot on
each bar update.  Fully thread-safe; supports streaming, batch, and async
update modes.
"""
from __future__ import annotations

import asyncio
import logging
import threading
import uuid
from collections import deque
from typing import Any, Callable, Deque, List, Optional, TYPE_CHECKING

from iios.investment.market.volatility.models import (
    BehaviourSnapshot,
    ConfidenceScore,
    RiskProfile,
    StrategyCompatibility,
    StrategyType,
    VolatilityBehaviour,
    VolatilityEvent,
    VolatilityEventType,
    VolatilityIntelligenceSnapshot,
    VolatilityRegimeType,
)
from iios.investment.market.volatility.estimator_registry import EstimatorRegistry
from iios.investment.market.volatility.close_to_close_estimator import CloseToCloseEstimator
from iios.investment.market.volatility.volatility_engine import VolatilityEngine
from iios.investment.market.volatility.regime_classifier import RegimeClassifier
from iios.investment.market.volatility.regime_transition import RegimeTransitionDetector
from iios.investment.market.volatility.volatility_expansion import VolatilityExpansionDetector
from iios.investment.market.volatility.volatility_compression import VolatilityCompressionDetector
from iios.investment.market.volatility.volatility_cycles import VolatilityCycleAnalyzer
from iios.investment.market.volatility.volatility_risk import VolatilityRiskAssessor
from iios.investment.market.volatility.risk_statistics import RiskStatistics
from iios.investment.market.volatility.strategy_volatility_mapper import StrategyVolatilityMapper
from iios.investment.market.volatility.volatility_confidence import VolatilityConfidenceCalculator
from iios.investment.market.volatility.confidence_history import ConfidenceHistory
from iios.investment.market.volatility.volatility_history import VolatilityHistory
from iios.investment.market.volatility.volatility_estimator import VolatilityEstimator

if TYPE_CHECKING:
    from iios.investment.market.structure.models import Bar

_log = logging.getLogger(__name__)


class InstitutionalVolatilityIntelligenceEngine:
    """
    Authoritative source of volatility intelligence for the IIOS.

    Parameters
    ----------
    symbol:          Instrument identifier.
    timeframe:       Bar timeframe string (e.g. "1d", "1h").
    estimators:      Pluggable estimator list.  Defaults to
                     [CloseToCloseEstimator(window=20)].
    volume_window:   Rolling window size passed to state tracker etc.
    history_size:    Maximum number of snapshots retained in history.
    """

    def __init__(
        self,
        symbol: str,
        timeframe: str,
        estimators: Optional[List[VolatilityEstimator]] = None,
        volume_window: int = 20,
        history_size: int = 500,
        # Optional dependency injection
        vol_engine: Optional[VolatilityEngine] = None,
        regime_classifier: Optional[RegimeClassifier] = None,
        transition_detector: Optional[RegimeTransitionDetector] = None,
        expansion_detector: Optional[VolatilityExpansionDetector] = None,
        compression_detector: Optional[VolatilityCompressionDetector] = None,
        cycle_analyzer: Optional[VolatilityCycleAnalyzer] = None,
        risk_assessor: Optional[VolatilityRiskAssessor] = None,
        strategy_mapper: Optional[StrategyVolatilityMapper] = None,
        confidence_calculator: Optional[VolatilityConfidenceCalculator] = None,
        risk_statistics: Optional[RiskStatistics] = None,
    ) -> None:
        self._symbol = symbol
        self._timeframe = timeframe

        # ── Build estimator registry ───────────────────────────────────────
        self._registry = EstimatorRegistry()
        _estimators = estimators or [CloseToCloseEstimator(window=volume_window)]
        for est in _estimators:
            self._registry.register(est)

        # ── Sub-engines ───────────────────────────────────────────────────
        self._vol_engine = vol_engine or VolatilityEngine(
            registry=self._registry,
            bar_buffer_len=max(100, volume_window * 3),
            medium_window=volume_window,
        )
        self._regime_classifier   = regime_classifier   or RegimeClassifier()
        self._transition_detector = transition_detector or RegimeTransitionDetector()
        self._expansion_detector  = expansion_detector  or VolatilityExpansionDetector()
        self._compression_detector = compression_detector or VolatilityCompressionDetector()
        self._cycle_analyzer      = cycle_analyzer      or VolatilityCycleAnalyzer()
        self._risk_assessor       = risk_assessor       or VolatilityRiskAssessor()
        self._strategy_mapper     = strategy_mapper     or StrategyVolatilityMapper()
        self._confidence_calc     = confidence_calculator or VolatilityConfidenceCalculator()
        self._risk_stats          = risk_statistics     or RiskStatistics()

        # ── History / state ───────────────────────────────────────────────
        self._history          = VolatilityHistory(maxlen=history_size)
        self._confidence_hist  = ConfidenceHistory(maxlen=history_size)
        self._event_history: Deque[VolatilityEvent] = deque(maxlen=history_size)
        self._current: Optional[VolatilityIntelligenceSnapshot] = None

        # ── Thread safety ──────────────────────────────────────────────────
        self._lock = threading.RLock()

        # ── Callbacks ─────────────────────────────────────────────────────
        self._on_regime_change_cbs: List[Callable[[VolatilityEvent], None]] = []
        self._on_expansion_cbs: List[Callable[[VolatilityIntelligenceSnapshot], None]] = []
        self._on_compression_cbs: List[Callable[[VolatilityIntelligenceSnapshot], None]] = []
        self._on_risk_alert_cbs: List[Callable[[VolatilityEvent], None]] = []
        self._on_update_cbs: List[Callable[[VolatilityIntelligenceSnapshot], None]] = []

        _log.info(
            "InstitutionalVolatilityIntelligenceEngine initialised: "
            "symbol=%s timeframe=%s estimators=%s",
            symbol, timeframe,
            [e.name for e in self._registry.all()],
        )

    # ── Properties ────────────────────────────────────────────────────────

    @property
    def symbol(self) -> str:
        return self._symbol

    @property
    def timeframe(self) -> str:
        return self._timeframe

    # ── Core update API ───────────────────────────────────────────────────

    def update(
        self,
        bar: "Bar",
        structure: Optional[Any] = None,
        regime: Optional[Any] = None,
        trend: Optional[Any] = None,
        liquidity: Optional[Any] = None,
    ) -> VolatilityIntelligenceSnapshot:
        """Thread-safe single-bar update."""
        with self._lock:
            return self._update_internal(bar, structure, regime, trend, liquidity)

    def update_batch(
        self,
        bars: "List[Bar]",
        structure: Optional[Any] = None,
        regime: Optional[Any] = None,
        trend: Optional[Any] = None,
        liquidity: Optional[Any] = None,
    ) -> VolatilityIntelligenceSnapshot:
        """Process multiple bars; returns the snapshot from the last bar."""
        with self._lock:
            snap = None
            for bar in bars:
                snap = self._update_internal(bar, structure, regime, trend, liquidity)
            return snap  # type: ignore[return-value]

    async def async_update(
        self,
        bar: "Bar",
        structure: Optional[Any] = None,
        regime: Optional[Any] = None,
        trend: Optional[Any] = None,
        liquidity: Optional[Any] = None,
    ) -> VolatilityIntelligenceSnapshot:
        """Async wrapper; runs update in the default executor."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.update(bar, structure, regime, trend, liquidity),
        )

    # ── Query API ─────────────────────────────────────────────────────────

    def current(self) -> Optional[VolatilityIntelligenceSnapshot]:
        return self._current

    def history(self, n: int = 20) -> List[VolatilityIntelligenceSnapshot]:
        return self._history.recent(n)

    def events(self, n: int = 20) -> List[VolatilityEvent]:
        with self._lock:
            return list(self._event_history)[-n:]

    def current_regime(self) -> VolatilityRegimeType:
        if self._current:
            return self._current.regime_snapshot.regime
        return VolatilityRegimeType.UNKNOWN

    def current_risk_profile(self) -> Optional[RiskProfile]:
        return self._current.risk_profile if self._current else None

    def current_behaviour(self) -> Optional[VolatilityBehaviour]:
        return (
            self._current.behaviour_snapshot.behaviour if self._current else None
        )

    def current_confidence(self) -> Optional[ConfidenceScore]:
        return self._current.confidence if self._current else None

    def current_strategy_compatibility(self) -> Optional[StrategyCompatibility]:
        return self._current.strategy_compatibility if self._current else None

    def is_strategy_permitted(self, strategy: str) -> bool:
        if self._current:
            return self._current.strategy_compatibility.is_permitted(strategy)
        return False

    def is_high_volatility(self) -> bool:
        if self._current:
            return self._current.regime_snapshot.regime in (
                VolatilityRegimeType.HIGH,
                VolatilityRegimeType.EXTREME,
                VolatilityRegimeType.SHOCK,
            )
        return False

    def is_shock(self) -> bool:
        if self._current:
            return self._current.regime_snapshot.regime == VolatilityRegimeType.SHOCK
        return False

    def is_expanding(self) -> bool:
        if self._current:
            return self._current.behaviour_snapshot.behaviour in (
                VolatilityBehaviour.EXPANDING,
                VolatilityBehaviour.CLIMAX,
                VolatilityBehaviour.ACCELERATING,
            )
        return False

    def is_compressing(self) -> bool:
        if self._current:
            return self._current.behaviour_snapshot.behaviour in (
                VolatilityBehaviour.COMPRESSING,
                VolatilityBehaviour.COOLING,
            )
        return False

    def normalized_volatility(self) -> float:
        return (
            self._current.normalized_volatility if self._current else 0.0
        )

    def realized_volatility(self) -> float:
        return (
            self._current.realized_volatility if self._current else 0.0
        )

    def risk_statistics(self) -> "RiskStats":  # type: ignore[name-defined]
        from iios.investment.market.volatility.risk_statistics import RiskStats
        return self._risk_stats.stats()

    # ── Callback registration ─────────────────────────────────────────────

    def on_regime_change(self, cb: Callable[[VolatilityEvent], None]) -> None:
        self._on_regime_change_cbs.append(cb)

    def on_expansion(
        self, cb: Callable[[VolatilityIntelligenceSnapshot], None]
    ) -> None:
        self._on_expansion_cbs.append(cb)

    def on_compression(
        self, cb: Callable[[VolatilityIntelligenceSnapshot], None]
    ) -> None:
        self._on_compression_cbs.append(cb)

    def on_risk_alert(self, cb: Callable[[VolatilityEvent], None]) -> None:
        self._on_risk_alert_cbs.append(cb)

    def on_update(
        self, cb: Callable[[VolatilityIntelligenceSnapshot], None]
    ) -> None:
        self._on_update_cbs.append(cb)

    # ── Estimator management ──────────────────────────────────────────────

    def register_estimator(self, estimator: VolatilityEstimator) -> None:
        self._registry.register(estimator)

    def unregister_estimator(self, name: str) -> None:
        self._registry.unregister(name)

    # ── Internal pipeline ──────────────────────────────────────────────────

    def _update_internal(
        self,
        bar: "Bar",
        structure: Optional[Any],
        regime: Optional[Any],
        trend: Optional[Any],
        liquidity: Optional[Any],
    ) -> VolatilityIntelligenceSnapshot:
        # 1. Run all estimators → VolatilityProfile
        vol_profile = self._vol_engine.update(bar)
        state       = vol_profile.state
        estimates   = vol_profile.estimates

        # 2. Expansion / compression
        exp_state, exp_event = self._expansion_detector.detect(
            state, bar.index, self._symbol, self._timeframe
        )
        comp_state, comp_event = self._compression_detector.detect(
            state, bar.index, self._symbol, self._timeframe
        )

        # 3. Behaviour / cycle
        behaviour = self._cycle_analyzer.analyze(state, exp_state, comp_state)

        # 4. Regime classification
        prev_regime = self._transition_detector.previous_regime
        regime_snap = self._regime_classifier.classify(
            state,
            behaviour.behaviour,
            prev_regime,
            self._transition_detector.duration_bars,
        )

        # 5. Transition detection (may emit REGIME_CHANGE event)
        transition_event = self._transition_detector.update(
            regime_snap.regime, bar.index, self._symbol, self._timeframe
        )
        # Refresh duration after transition update
        regime_snap = self._regime_classifier.classify(
            state,
            behaviour.behaviour,
            self._transition_detector.previous_regime,
            self._transition_detector.duration_bars,
        )

        # 6. Risk assessment
        risk_profile, shock_event = self._risk_assessor.assess(
            state, regime_snap.regime, behaviour,
            bar.index, self._symbol, self._timeframe,
        )
        self._risk_stats.record(risk_profile)

        # 7. Strategy compatibility
        strategy_compat = self._strategy_mapper.evaluate(
            regime_snap.regime, state, behaviour
        )

        # 8. Confidence
        confidence = self._confidence_calc.calculate(
            state, regime_snap, behaviour, estimates
        )
        self._confidence_hist.append(confidence)

        # 9. Collect events
        active_events: List[VolatilityEvent] = []
        for ev in (exp_event, comp_event, transition_event, shock_event):
            if ev is not None:
                active_events.append(ev)
                self._event_history.append(ev)

        # 10. Check spike
        if state.normalized_volatility >= 0.90 and not shock_event:
            spike_ev = VolatilityEvent(
                event_type=VolatilityEventType.SPIKE,
                symbol=self._symbol,
                timeframe=self._timeframe,
                bar_index=bar.index,
                severity=state.normalized_volatility,
            )
            active_events.append(spike_ev)
            self._event_history.append(spike_ev)

        # 11. Extract cross-engine context
        structure_regime = self._extract_structure(structure)
        market_regime    = self._extract_market_regime(regime)
        trend_stage      = self._extract_trend_stage(trend)
        liq_score        = self._extract_liquidity(liquidity)

        # 12. Compute scalar volatility score (0-100)
        volatility_score = state.normalized_volatility * 100.0

        # 13. Assemble snapshot
        snap = VolatilityIntelligenceSnapshot(
            snapshot_id=str(uuid.uuid4()),
            symbol=self._symbol,
            timeframe=self._timeframe,
            bar_index=bar.index,
            timestamp=bar.timestamp,
            volatility_profile=vol_profile,
            realized_volatility=state.realized_volatility,
            relative_volatility=state.relative_volatility,
            normalized_volatility=state.normalized_volatility,
            volatility_score=volatility_score,
            regime_snapshot=regime_snap,
            behaviour_snapshot=behaviour,
            risk_profile=risk_profile,
            strategy_compatibility=strategy_compat,
            confidence=confidence,
            active_events=active_events,
            last_event=active_events[-1] if active_events else None,
            structure_regime=structure_regime,
            market_regime=market_regime,
            trend_stage=trend_stage,
            liquidity_score=liq_score,
        )

        self._history.append(snap)
        self._current = snap

        # 14. Fire callbacks
        self._fire_callbacks(snap, transition_event, shock_event)

        return snap

    # ── Context extraction helpers ────────────────────────────────────────

    def _extract_structure(self, structure: Optional[Any]) -> Optional[str]:
        if structure is None:
            return None
        for attr in ("trend_state", "phase", "structure_phase"):
            val = getattr(structure, attr, None)
            if val is not None:
                return str(val.value) if hasattr(val, "value") else str(val)
        return None

    def _extract_market_regime(self, regime: Optional[Any]) -> Optional[str]:
        if regime is None:
            return None
        for attr in ("regime", "regime_type", "market_regime"):
            val = getattr(regime, attr, None)
            if val is not None:
                return str(val.value) if hasattr(val, "value") else str(val)
        return None

    def _extract_trend_stage(self, trend: Optional[Any]) -> Optional[str]:
        if trend is None:
            return None
        for attr in ("trend_stage", "stage", "trend_state"):
            val = getattr(trend, attr, None)
            if val is not None:
                return str(val.value) if hasattr(val, "value") else str(val)
        return None

    def _extract_liquidity(self, liquidity: Optional[Any]) -> Optional[float]:
        if liquidity is None:
            return None
        for attr in ("liquidity_score", "liquidity", "score"):
            val = getattr(liquidity, attr, None)
            if isinstance(val, (int, float)):
                return float(val)
        return None

    # ── Callback dispatch ─────────────────────────────────────────────────

    def _fire_callbacks(
        self,
        snap: VolatilityIntelligenceSnapshot,
        transition_event: Optional[VolatilityEvent],
        shock_event: Optional[VolatilityEvent],
    ) -> None:
        if transition_event is not None:
            for cb in self._on_regime_change_cbs:
                try:
                    cb(transition_event)
                except Exception:
                    _log.exception("on_regime_change callback error")

        if snap.behaviour_snapshot.behaviour in (
            VolatilityBehaviour.EXPANDING,
            VolatilityBehaviour.CLIMAX,
            VolatilityBehaviour.ACCELERATING,
        ):
            for cb in self._on_expansion_cbs:
                try:
                    cb(snap)
                except Exception:
                    _log.exception("on_expansion callback error")

        if snap.behaviour_snapshot.behaviour in (
            VolatilityBehaviour.COMPRESSING,
            VolatilityBehaviour.COOLING,
        ):
            for cb in self._on_compression_cbs:
                try:
                    cb(snap)
                except Exception:
                    _log.exception("on_compression callback error")

        if shock_event is not None:
            for cb in self._on_risk_alert_cbs:
                try:
                    cb(shock_event)
                except Exception:
                    _log.exception("on_risk_alert callback error")

        for cb in self._on_update_cbs:
            try:
                cb(snap)
            except Exception:
                _log.exception("on_update callback error")
