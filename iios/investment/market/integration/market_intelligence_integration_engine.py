"""iios/investment/market/integration/market_intelligence_integration_engine.py
Institutional Market Intelligence Integration & Validation Engine.

Primary entry point: MarketIntelligenceIntegrationEngine.

  engine = MarketIntelligenceIntegrationEngine()
  snap   = engine.update(bundle)

This engine integrates, validates, reconciles, scores and publishes a single
canonical MarketIntelligenceSnapshot.  It never independently calculates regime,
trend, volatility, breadth, correlation, sector rotation or opportunities —
those are the responsibility of the upstream engines.
"""
from __future__ import annotations

import threading
from typing import Callable, Dict, List, Optional

from iios.common.async_exec.async_execution_manager import get_execution_manager as _get_exec_manager
from iios.common.async_exec.execution_classifier import WorkloadType
from iios.common.logging.logging_manager import get_logger
from iios.common.logging.audit_logger import get_audit_logger
from iios.common.errors.error_manager import get_error_manager as _get_err_mgr
from iios.common.errors.error_context import ErrorContext, bind_error_context

from iios.investment.market.integration.aggregation_engine import KNOWN_ENGINES
from iios.investment.market.integration.conflict_engine import ConflictEngine
from iios.investment.market.integration.consistency_rules import ConsistencyRule
from iios.investment.market.integration.consistency_validator import ConsistencyValidator
from iios.investment.market.integration.health_monitor import HealthMonitor
from iios.investment.market.integration.market_confidence import MarketConfidenceEngine
from iios.investment.market.integration.market_intelligence_aggregator import (
    MarketIntelligenceAggregator,
)
from iios.investment.market.integration.market_quality import MarketQualityEngine
from iios.investment.market.integration.market_snapshot import SnapshotBuilder
from iios.investment.market.integration.market_state import MarketStateClassifier
from iios.investment.market.integration.market_statistics import (
    avg_confidence,
    avg_quality,
    conflict_rate,
    regime_distribution,
    state_label_distribution,
)
from iios.investment.market.integration.market_summary import MarketSummaryBuilder
from iios.investment.market.integration.models import (
    EngineSource,
    IntelligenceBundle,
    MarketIntelligenceSnapshot,
    MarketStateLabel,
    QualityScore,
    ValidationReport,
)
from iios.investment.market.integration.quality_history import QualityHistory
from iios.investment.market.integration.snapshot_history import SnapshotHistory

from iios.investment.workflow.engine_lifecycle import LifecycleAwareMixin

_log = get_logger(__name__, engine_id="iios:market:intelligence:integration")
_audit = get_audit_logger(
    __name__,
    engine_id = "iios:market:intelligence:integration",
    component = "MarketIntelligenceIntegrationEngine",
)


class MarketIntelligenceIntegrationEngine(LifecycleAwareMixin):
    """Single orchestration and validation layer for all Market Intelligence.

    Downstream IIOS components (TechnicalAnalystAI, FundamentalAnalystAI,
    StrategyIntelligence, PortfolioAI, RiskAI, DecisionLayer,
    OpportunityEngine) must consume ONLY the snapshot published by this engine.

    Extensibility:
    - New upstream engines: add engine_name/source to IntelligenceBundle;
      add extractor to AggregationEngine; register with engine.
    - New consistency rules: engine.add_rule(ConsistencyRule(...))
    - New callbacks: engine.on_snapshot / on_alert / on_update
    """

    VERSION   = "1.0.0"
    SYSTEM_ID = "iios:market:intelligence:integration"

    def __init__(
        self,
        expected_engines:   Optional[List[str]] = None,
        snapshot_history_len: int = 250,
        quality_history_len:  int = 200,
        stale_threshold_bars: int = 5,
        extra_rules:          Optional[List[ConsistencyRule]] = None,
    ) -> None:
        self._lock            = threading.Lock()
        self._n_bars          = 0
        self._expected        = expected_engines or list(KNOWN_ENGINES)

        # Sub-systems
        self._aggregator     = MarketIntelligenceAggregator(snapshot_history_len)
        self._validator      = ConsistencyValidator(extra_rules)
        self._conflict_engine = ConflictEngine()
        self._quality_engine  = MarketQualityEngine(self._expected)
        self._confidence_eng  = MarketConfidenceEngine()
        self._state_clf       = MarketStateClassifier()
        self._summary_builder = MarketSummaryBuilder()
        self._snap_builder    = SnapshotBuilder()
        self._health_monitor  = HealthMonitor(self._expected, stale_threshold_bars)
        self._snap_history    = SnapshotHistory(snapshot_history_len)
        self._quality_history = QualityHistory(quality_history_len)

        # Callbacks
        self.on_snapshot:    Optional[Callable[[MarketIntelligenceSnapshot], None]] = None
        self.on_low_quality: Optional[Callable[[float], None]] = None
        self.on_conflict:    Optional[Callable[[int], None]] = None

    # ── lifecycle hooks ───────────────────────────────────────────────────────

    def _on_start(self) -> None:
        _log.info("MarketIntelligenceIntegrationEngine started.")
        _audit.log_lifecycle_event(
            self.SYSTEM_ID, "STOPPED", "RUNNING", self.VERSION,
        )

    def _on_stop(self) -> None:
        _log.info("MarketIntelligenceIntegrationEngine stopped.")
        _audit.log_lifecycle_event(
            self.SYSTEM_ID, "RUNNING", "STOPPED", self.VERSION,
        )

    # ── primary update ────────────────────────────────────────────────────────

    def update(self, bundle: IntelligenceBundle) -> MarketIntelligenceSnapshot:
        with bind_error_context(ErrorContext(
            engine_id = self.SYSTEM_ID,
            operation = "update",
            stage     = "market_intelligence_integration",
        )):
            try:
                with self._lock:
                    return self._process(bundle)
            except Exception as exc:
                _get_err_mgr().report_failure(self.SYSTEM_ID, exc)
                raise

    def _process(self, bundle: IntelligenceBundle) -> MarketIntelligenceSnapshot:
        self._n_bars += 1
        bar_index = bundle.bar_index
        self._quality_engine.advance_bar(bar_index)

        # ── 1. Aggregate ─────────────────────────────────────────────────────
        state = self._aggregator.aggregate(bundle)

        # ── 2. Validate consistency ─────────────────────────────────────────
        report = self._validator.validate(state)

        # ── 3. Detect + resolve conflicts ────────────────────────────────────
        conflicts = self._conflict_engine.process(state, report)

        # ── 4. Quality score ──────────────────────────────────────────────────
        quality = self._quality_engine.score(state, report, conflicts)
        self._quality_history.append(quality)

        # ── 5. Confidence ─────────────────────────────────────────────────────
        confidence = self._confidence_eng.compute(state, quality, conflicts)

        # ── 6. Market state ───────────────────────────────────────────────────
        label = self._state_clf.classify(state)

        # ── 7. Summary text ───────────────────────────────────────────────────
        summary = self._summary_builder.build(state, label, quality, conflicts)

        # ── 8. Health monitoring ──────────────────────────────────────────────
        self._health_monitor.update(state)
        engine_health = self._health_monitor.all_health()

        # ── 9. Assemble snapshot ──────────────────────────────────────────────
        snap = self._snap_builder.build(
            state=state,
            label=label,
            quality=quality,
            confidence=confidence,
            validation=report,
            conflicts=conflicts,
            engine_health=engine_health,
            summary_text=summary,
        )
        self._snap_history.append(snap)

        # ── 10. Callbacks ─────────────────────────────────────────────────────
        self._fire_callbacks(snap)

        return snap

    # ── async update ──────────────────────────────────────────────────────────

    async def async_update(self, bundle: IntelligenceBundle) -> MarketIntelligenceSnapshot:
        return await _get_exec_manager().execute(
            self.update,
            bundle,
            workload_type = WorkloadType.IO_BOUND,
            operation     = "market.async_update",
            engine_id     = self.SYSTEM_ID,
        )

    # ── convenience bundle builder ────────────────────────────────────────────

    @staticmethod
    def make_bundle(
        bar_index: int,
        timestamp: float,
        payloads: Dict,   # engine_name → raw payload object
        sources:  Optional[Dict[str, EngineSource]] = None,
    ) -> IntelligenceBundle:
        """Convenience: build an IntelligenceBundle from a dict of payloads."""
        from iios.investment.market.integration.models import EnginePayload
        sources = sources or {}
        bundle  = IntelligenceBundle(bar_index=bar_index, timestamp=timestamp)
        for name, payload in payloads.items():
            ep = EnginePayload(
                engine_name=name,
                source=sources.get(name, EngineSource.UNKNOWN),
                payload=payload,
                bar_index=bar_index,
                timestamp=timestamp,
            )
            bundle.add(ep)
        return bundle

    # ── rule management ───────────────────────────────────────────────────────

    def add_rule(self, rule: ConsistencyRule) -> None:
        self._validator.add_rule(rule)

    # ── query APIs ────────────────────────────────────────────────────────────

    def latest(self) -> Optional[MarketIntelligenceSnapshot]:
        return self._snap_history.latest()

    def recent_history(self, n: int = 10) -> List[MarketIntelligenceSnapshot]:
        return self._snap_history.recent(n)

    def current_quality(self) -> Optional[QualityScore]:
        return self._quality_history.latest()

    def current_regime(self) -> Optional[str]:
        snap = self._snap_history.latest()
        return snap.market_regime if snap else None

    def current_state(self) -> MarketStateLabel:
        snap = self._snap_history.latest()
        return snap.market_state_label if snap else MarketStateLabel.UNKNOWN

    def current_confidence(self) -> float:
        snap = self._snap_history.latest()
        return snap.overall_confidence if snap else 0.0

    def current_validation(self) -> Optional[ValidationReport]:
        snap = self._snap_history.latest()
        return snap.validation if snap else None

    def engine_health(self, engine_name: str = None):
        if engine_name:
            return self._health_monitor.engine_health(engine_name)
        return self._health_monitor.all_health()

    def overall_health(self):
        return self._health_monitor.overall_health()

    def cascade_failures(self):
        return self._health_monitor.cascade_failures()

    def coverage_report(self):
        return self._health_monitor.coverage_report()

    # ── aggregate statistics ──────────────────────────────────────────────────

    def statistics(self, n: int = 20) -> dict:
        snaps = self._snap_history.recent(n)
        return {
            "bars":              len(snaps),
            "avg_confidence":    round(avg_confidence(snaps), 2),
            "avg_quality":       round(avg_quality(snaps), 2),
            "conflict_rate":     round(conflict_rate(snaps), 3),
            "regime_distribution": regime_distribution(snaps),
            "state_distribution":  state_label_distribution(snaps),
            "healthy_engines":   self._health_monitor.healthy_count(),
            "overall_coverage":  round(self._health_monitor.overall_coverage(), 3),
        }

    @property
    def bars_processed(self) -> int:
        return self._n_bars

    # ── internals ─────────────────────────────────────────────────────────────

    def _fire_callbacks(self, snap: MarketIntelligenceSnapshot) -> None:
        if self.on_snapshot:
            try:
                self.on_snapshot(snap)
            except Exception as _cb_exc:
                _log.exception("on_snapshot callback error")
                _get_err_mgr().report_failure(self.SYSTEM_ID, _cb_exc)

        if self.on_low_quality and snap.quality.overall < 50.0:
            try:
                self.on_low_quality(snap.quality.overall)
            except Exception as _cb_exc:
                _log.exception("on_low_quality callback error")
                _get_err_mgr().report_failure(self.SYSTEM_ID, _cb_exc)

        if self.on_conflict and snap.conflicts.total > 0:
            try:
                self.on_conflict(snap.conflicts.total)
            except Exception as _cb_exc:
                _log.exception("on_conflict callback error")
                _get_err_mgr().report_failure(self.SYSTEM_ID, _cb_exc)
