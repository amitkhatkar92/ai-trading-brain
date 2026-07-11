"""iios/investment/market/correlation/correlation_intelligence_engine.py
InstitutionalCorrelationIntelligenceEngine — primary entry point for the
Correlation & Intermarket Intelligence layer.
"""
from __future__ import annotations

import asyncio
import logging
import threading
import uuid
from typing import Callable, Dict, List, Optional, Tuple

from iios.investment.market.correlation.models import (
    CorrelationEvent,
    CorrelationEventType,
    CorrelationIntelligenceSnapshot,
    CorrelationMatrix,
    CorrelationMethod,
    CorrelationRegimeType,
    DependencyGraph,
    DiversificationMetrics,
    IntermarketAnalysis,
    MultiAssetSnapshot,
    PriceObservation,
    SystemicRiskMetrics,
)
from iios.investment.market.correlation.correlation_estimator import CorrelationEstimator
from iios.investment.market.correlation.pearson_estimator import PearsonEstimator
from iios.investment.market.correlation.spearman_estimator import SpearmanEstimator
from iios.investment.market.correlation.kendall_estimator import KendallEstimator
from iios.investment.market.correlation.estimator_registry import EstimatorRegistry
from iios.investment.market.correlation.correlation_engine import CorrelationEngine
from iios.investment.market.correlation.correlation_history import CorrelationHistory
from iios.investment.market.correlation.correlation_statistics import CorrelationStatistics
from iios.investment.market.correlation.intermarket_engine import IntermarketEngine
from iios.investment.market.correlation.dependency_engine import DependencyEngine
from iios.investment.market.correlation.systemic_risk import SystemicRiskCalculator
from iios.investment.market.correlation.contagion_engine import ContagionEngine
from iios.investment.market.correlation.shock_propagation import ShockPropagationAnalyzer
from iios.investment.market.correlation.diversification_engine import DiversificationScorer
from iios.investment.market.correlation.correlation_classifier import CorrelationRegimeClassifier
from iios.investment.market.correlation.regime_transition import CorrelationRegimeTransitionDetector
from iios.investment.market.correlation.correlation_matrix import empty_correlation_matrix
from iios.investment.market.correlation.dependency_graph import build_dependency_graph

logger = logging.getLogger(__name__)


class InstitutionalCorrelationIntelligenceEngine:
    """
    Authoritative source of correlation, intermarket, dependency,
    systemic risk, and diversification intelligence for all IIOS layers.

    No other module should independently calculate market correlations.

    Callbacks:
        on_regime_change(event: CorrelationEvent)
        on_systemic_risk(event: CorrelationEvent)
        on_contagion(event: CorrelationEvent)
        on_update(snap: CorrelationIntelligenceSnapshot)
    """

    def __init__(
        self,
        symbols:               Optional[List[str]] = None,
        asset_classes:         Optional[Dict[str, str]] = None,
        window:                int = 60,
        max_lag:               int = 5,
        min_observations:      int = 10,
        history_size:          int = 500,
        primary_estimator:     Optional[CorrelationEstimator] = None,
        *,
        correlation_engine:    Optional[CorrelationEngine]               = None,
        intermarket_engine:    Optional[IntermarketEngine]               = None,
        dependency_engine:     Optional[DependencyEngine]                = None,
        systemic_risk_calc:    Optional[SystemicRiskCalculator]          = None,
        contagion_engine:      Optional[ContagionEngine]                 = None,
        shock_analyzer:        Optional[ShockPropagationAnalyzer]        = None,
        diversification_scorer: Optional[DiversificationScorer]         = None,
        regime_classifier:     Optional[CorrelationRegimeClassifier]     = None,
        transition_detector:   Optional[CorrelationRegimeTransitionDetector] = None,
    ) -> None:
        self._window          = window
        self._max_lag         = max_lag
        self._min_obs         = min_observations
        self._symbols         = list(symbols or [])
        self._asset_classes   = dict(asset_classes or {})

        # ── Sub-engines ───────────────────────────────────────────────────
        primary = primary_estimator or PearsonEstimator()
        registry = EstimatorRegistry()
        registry.register(primary)
        registry.register(SpearmanEstimator())
        registry.register(KendallEstimator())

        self._corr_engine     = correlation_engine or CorrelationEngine(
            window=window,
            min_observations=min_observations,
            primary_estimator=primary,
            registry=registry,
        )
        self._intermarket     = intermarket_engine    or IntermarketEngine()
        self._dep_engine      = dependency_engine     or DependencyEngine(
            primary_calc=self._corr_engine._calculators[primary.name],
            window=window,
            max_lag=max_lag,
        )
        self._sys_risk        = systemic_risk_calc    or SystemicRiskCalculator()
        self._contagion       = contagion_engine      or ContagionEngine()
        self._shock           = shock_analyzer        or ShockPropagationAnalyzer()
        self._div_scorer      = diversification_scorer or DiversificationScorer()
        self._classifier      = regime_classifier     or CorrelationRegimeClassifier()
        self._transition      = transition_detector   or CorrelationRegimeTransitionDetector()

        # ── State ─────────────────────────────────────────────────────────
        self._history         = CorrelationHistory(maxlen=history_size)
        self._current:  Optional[CorrelationIntelligenceSnapshot] = None
        self._events:   List[CorrelationEvent] = []
        self._bar_index: int = 0
        self._lock      = threading.Lock()

        # ── Callbacks ─────────────────────────────────────────────────────
        self.on_regime_change: Optional[Callable[[CorrelationEvent], None]] = None
        self.on_systemic_risk: Optional[Callable[[CorrelationEvent], None]] = None
        self.on_contagion:     Optional[Callable[[CorrelationEvent], None]] = None
        self.on_update:        Optional[Callable[[CorrelationIntelligenceSnapshot], None]] = None

    # ── Primary API ───────────────────────────────────────────────────────

    def update(
        self,
        snapshot: MultiAssetSnapshot,
        *,
        structure:  Optional[object] = None,
        regime:     Optional[object] = None,
        trend:      Optional[object] = None,
        liquidity:  Optional[object] = None,
        volatility: Optional[object] = None,
        breadth:    Optional[object] = None,
    ) -> CorrelationIntelligenceSnapshot:
        with self._lock:
            return self._update_internal(
                snapshot, structure, regime, trend, liquidity, volatility, breadth
            )

    def update_batch(
        self,
        snapshots: List[MultiAssetSnapshot],
        **kwargs,
    ) -> CorrelationIntelligenceSnapshot:
        if not snapshots:
            raise ValueError("snapshots must be non-empty")
        snap = None
        for s in snapshots:
            snap = self.update(s, **kwargs)
        return snap  # type: ignore[return-value]

    async def async_update(
        self, snapshot: MultiAssetSnapshot, **kwargs
    ) -> CorrelationIntelligenceSnapshot:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, lambda: self.update(snapshot, **kwargs)
        )

    # ── Query APIs ────────────────────────────────────────────────────────

    def current(self) -> Optional[CorrelationIntelligenceSnapshot]:
        return self._current

    def history(self, n: int = 20) -> List[CorrelationIntelligenceSnapshot]:
        return self._history.recent(n)

    def events(self, n: int = 20) -> List[CorrelationEvent]:
        return self._events[-n:]

    def correlation_matrix(self) -> Optional[CorrelationMatrix]:
        if self._current is None:
            return None
        return self._current.correlation_matrix

    def get_correlation(self, s1: str, s2: str) -> Optional[float]:
        m = self.correlation_matrix()
        return m.get(s1, s2) if m else None

    def dependency_graph(self) -> Optional[DependencyGraph]:
        if self._current is None:
            return None
        return self._current.dependency_graph

    def systemic_risk(self) -> Optional[SystemicRiskMetrics]:
        if self._current is None:
            return None
        return self._current.systemic_risk

    def diversification(self) -> Optional[DiversificationMetrics]:
        if self._current is None:
            return None
        return self._current.diversification

    def current_regime(self) -> CorrelationRegimeType:
        return self._transition.current_regime

    def highly_correlated_pairs(
        self, threshold: float = 0.70
    ) -> List[Tuple[str, str, float]]:
        m = self.correlation_matrix()
        return m.highly_correlated_pairs(threshold) if m else []

    def inversely_correlated_pairs(
        self, threshold: float = -0.70
    ) -> List[Tuple[str, str, float]]:
        m = self.correlation_matrix()
        return m.inversely_correlated_pairs(threshold) if m else []

    def leading_assets(self) -> List[str]:
        g = self.dependency_graph()
        return g.leading_assets() if g else []

    def best_hedge(self, symbol: str) -> Optional[Tuple[str, float]]:
        from iios.investment.market.correlation import hedging_analysis as ha
        m = self.correlation_matrix()
        if m is None:
            return None
        return ha.best_hedge_for_asset(symbol, m)

    # ── Estimator management ──────────────────────────────────────────────

    def register_estimator(self, estimator: CorrelationEstimator) -> None:
        self._corr_engine.register_estimator(estimator)

    def unregister_estimator(self, name: str) -> None:
        self._corr_engine.unregister_estimator(name)

    # ── Internal ──────────────────────────────────────────────────────────

    def _update_internal(
        self,
        snapshot: MultiAssetSnapshot,
        structure, regime, trend, liquidity, volatility, breadth,
    ) -> CorrelationIntelligenceSnapshot:
        bar_index = self._bar_index
        self._bar_index += 1

        # Update asset-class registry from snapshot metadata
        for obs in snapshot.observations:
            if obs.asset_class and obs.asset_class not in ("unknown",):
                self._asset_classes[obs.symbol] = obs.asset_class

        # 1 — Correlation matrix (primary)
        matrix = self._corr_engine.update(snapshot)
        if matrix is None:
            matrix = empty_correlation_matrix(bar_index, snapshot.timestamp)

        # 2 — Dependency graph
        dep_graph = self._dep_engine.update(snapshot, matrix)

        # 3 — Intermarket analysis
        intermarket = self._intermarket.update(matrix, snapshot)

        # 4 — Systemic risk
        sys_risk = self._sys_risk.calculate(matrix, dep_graph)

        # 5 — Diversification
        diversification = self._div_scorer.score(matrix)

        # 6 — Confidence
        confidence = self._build_confidence(matrix, snapshot)

        # 7 — Regime classification
        stats = self._corr_engine.statistics()
        regime_snap = self._classifier.classify(
            matrix, stats, intermarket, sys_risk,
            previous_regime=self._transition.previous_regime,
            duration_bars=self._transition.duration_bars,
        )

        # 8 — Transitions
        transition_events = self._transition.update(regime_snap, bar_index)

        # 9 — Contagion
        contagion_events = self._contagion.update(sys_risk, bar_index)

        # 10 — Shock propagation (check for large moves in this snapshot)
        current_returns = snapshot.returns()
        shock_paths, shock_events = self._shock.analyze(
            matrix, dep_graph, current_returns, bar_index
        )

        # 11 — Diversification collapse event
        div_events: List[CorrelationEvent] = []
        if diversification.diversification_score < 15.0:
            div_events.append(CorrelationEvent(
                event_type=CorrelationEventType.DIVERSIFICATION_COLLAPSE,
                bar_index=bar_index,
                severity=1.0 - diversification.diversification_score / 15.0,
                description="Diversification collapse detected",
            ))

        all_events = transition_events + contagion_events + shock_events + div_events
        self._events.extend(all_events)
        if len(self._events) > 2000:
            self._events = self._events[-1000:]

        # 12 — Build snapshot
        snap = CorrelationIntelligenceSnapshot(
            snapshot_id=str(uuid.uuid4()),
            bar_index=bar_index,
            timestamp=snapshot.timestamp,
            correlation_matrix=matrix,
            regime_snapshot=regime_snap,
            dependency_graph=dep_graph,
            systemic_risk=sys_risk,
            diversification=diversification,
            intermarket=intermarket,
            confidence=confidence,
            active_events=all_events,
            last_event=all_events[-1] if all_events else None,
            market_regime=_extract_str(regime),
            volatility_regime=_extract_str(volatility),
            breadth_regime=_extract_str(breadth),
            trend_stage=_extract_str(trend),
        )
        self._current = snap
        self._history.append(snap)

        # 13 — Fire callbacks
        self._fire_callbacks(snap, all_events)

        logger.debug(
            "corr_engine bar=%d regime=%s avg_corr=%.3f n_assets=%d",
            bar_index,
            regime_snap.regime.value,
            matrix.avg_abs_correlation(),
            len(matrix.symbols),
        )
        return snap

    def _build_confidence(
        self,
        matrix: CorrelationMatrix,
        snapshot: MultiAssetSnapshot,
    ):
        from iios.investment.market.correlation.models import CorrelationConfidenceScore
        n = len(matrix.symbols)
        obs = matrix.n_observations
        win = max(matrix.window, 1)

        data_quality    = 1.0 if snapshot.total > 0 else 0.0
        window_fullness = min(1.0, obs / win)
        n_assets_score  = min(1.0, n / 10)
        stats           = self._corr_engine.statistics()
        stability       = stats.correlation_stability() if len(stats) >= 5 else 0.5

        overall = (
            data_quality    * 0.20
            + window_fullness * 0.35
            + n_assets_score  * 0.25
            + stability       * 0.20
        ) * 100

        return CorrelationConfidenceScore(
            data_quality=round(data_quality, 4),
            window_fullness=round(window_fullness, 4),
            n_assets_score=round(n_assets_score, 4),
            stability_score=round(stability, 4),
            overall_score=round(max(0.0, min(100.0, overall)), 2),
        )

    def _fire_callbacks(
        self,
        snap: CorrelationIntelligenceSnapshot,
        events: List[CorrelationEvent],
    ) -> None:
        if self.on_update:
            try:
                self.on_update(snap)
            except Exception:
                logger.exception("on_update callback raised")

        for ev in events:
            if ev.event_type == CorrelationEventType.REGIME_CHANGE and self.on_regime_change:
                try:
                    self.on_regime_change(ev)
                except Exception:
                    logger.exception("on_regime_change callback raised")
            if ev.event_type in (
                CorrelationEventType.SYSTEMIC_RISK_ELEVATED,
            ) and self.on_systemic_risk:
                try:
                    self.on_systemic_risk(ev)
                except Exception:
                    logger.exception("on_systemic_risk callback raised")
            if ev.event_type in (
                CorrelationEventType.CONTAGION_DETECTED,
                CorrelationEventType.SHOCK_PROPAGATION,
            ) and self.on_contagion:
                try:
                    self.on_contagion(ev)
                except Exception:
                    logger.exception("on_contagion callback raised")


# ── Helpers ───────────────────────────────────────────────────────────────

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
