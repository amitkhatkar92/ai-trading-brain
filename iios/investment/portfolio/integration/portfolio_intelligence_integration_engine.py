"""iios/investment/portfolio/integration/portfolio_intelligence_integration_engine.py

Portfolio Intelligence Integration & Validation Engine.

Single orchestration, validation, quality-assurance, and publishing layer
for ALL Portfolio Intelligence in IIOS.

Every downstream component must consume ONLY the PortfolioIntelligenceSnapshot
published by this engine.
"""
from __future__ import annotations

import dataclasses
import threading
import time
import uuid
from collections import deque
from typing import Any, Callable, Dict, List, Optional

from iios.investment.portfolio.integration.aggregation_state import EngineContribution
from iios.investment.portfolio.integration.conflict_engine import (
    ConflictEngine, ConflictReport,
)
from iios.investment.portfolio.integration.consistency_validator import ConsistencyValidator
from iios.investment.portfolio.integration.coverage_monitor import (
    CoverageMonitor, CoverageReport,
)
from iios.investment.portfolio.integration.health_monitor import (
    IntegrationHealthMonitor, IntegrationHealthReport,
)
from iios.investment.portfolio.integration.integration_types import (
    AggregationStatus, EngineId, IntegrationParameters,
    SnapshotStatus, now_utc,
)
from iios.investment.portfolio.integration.portfolio_confidence import (
    PortfolioConfidenceCalculator, PortfolioConfidenceScore,
)
from iios.investment.portfolio.integration.portfolio_intelligence_aggregator import (
    PortfolioIntelligenceAggregator,
)
from iios.investment.portfolio.integration.portfolio_quality import (
    PortfolioQualityAssessor, PortfolioQualityReport,
)
from iios.investment.portfolio.integration.portfolio_snapshot import (
    PortfolioIntelligenceSnapshot,
)
from iios.investment.portfolio.integration.portfolio_statistics import (
    IntegrationRunMetric, PortfolioIntegrationStatistics,
    PortfolioIntegrationStatisticsSnapshot,
)
from iios.investment.portfolio.integration.portfolio_summary import (
    PortfolioState, PortfolioSummary, build_state, build_summary,
)
from iios.investment.portfolio.integration.quality_history import QualityHistory
from iios.investment.portfolio.integration.quality_statistics import (
    QualityRunMetric, QualityStatistics,
)
from iios.investment.portfolio.integration.validation_report import (
    ConsistencyValidationReport,
)
from iios.investment.workflow.engine_lifecycle import LifecycleAwareMixin

from iios.common.logging.logging_manager import get_logger
from iios.common.logging.audit_logger import get_audit_logger
from iios.common.errors.error_manager import get_error_manager as _get_err_mgr
from iios.common.errors.error_context import ErrorContext

_log = get_logger(__name__, engine_id="iios:portfolio:intelligence:integration")
_audit = get_audit_logger(
    __name__,
    engine_id = "iios:portfolio:intelligence:integration",
    component = "PortfolioIntelligenceIntegrationEngine",
)


class _SnapshotStore:
    """Thread-safe bounded per-portfolio snapshot store."""

    def __init__(self, max_per_portfolio: int) -> None:
        self._max  = max_per_portfolio
        self._lock = threading.RLock()
        self._store: Dict[str, deque] = {}

    def add(self, snap: PortfolioIntelligenceSnapshot) -> None:
        with self._lock:
            pid = snap.portfolio_id
            if pid not in self._store:
                self._store[pid] = deque(maxlen=self._max)
            self._store[pid].appendleft(snap)

    def latest(self, portfolio_id: str) -> Optional[PortfolioIntelligenceSnapshot]:
        with self._lock:
            dq = self._store.get(portfolio_id)
            return dq[0] if dq else None

    def recent(self, portfolio_id: str, n: int) -> List[PortfolioIntelligenceSnapshot]:
        with self._lock:
            return list(self._store.get(portfolio_id, []))[:n]

    def all_portfolio_ids(self) -> List[str]:
        with self._lock:
            return list(self._store.keys())


class PortfolioIntelligenceIntegrationEngine(LifecycleAwareMixin):
    """
    Single orchestration and publishing layer for all Portfolio Intelligence.

    Integrates: Framework, Construction, Allocation, Optimization,
    Diversification, Risk, Performance, Rebalancing, Recommendation.

    Does NOT independently calculate any of the above.
    """

    VERSION   = "1.0.0"
    SYSTEM_ID = "iios:portfolio:intelligence:integration"

    def __init__(
        self,
        *,
        params:             Optional[IntegrationParameters]           = None,
        aggregator:         Optional[PortfolioIntelligenceAggregator] = None,
        consistency_validator: Optional[ConsistencyValidator]         = None,
        conflict_engine:    Optional[ConflictEngine]                  = None,
        quality_assessor:   Optional[PortfolioQualityAssessor]        = None,
        confidence_calc:    Optional[PortfolioConfidenceCalculator]   = None,
        health_monitor:     Optional[IntegrationHealthMonitor]        = None,
        coverage_monitor:   Optional[CoverageMonitor]                 = None,
        event_callback:     Optional[Callable[[str, Any], None]]      = None,
    ) -> None:
        self._params     = params          or IntegrationParameters()
        self._aggregator = aggregator      or PortfolioIntelligenceAggregator(self._params)
        self._validator  = consistency_validator or ConsistencyValidator(self._params)
        self._conflicts  = conflict_engine or ConflictEngine(self._params)
        self._quality    = quality_assessor or PortfolioQualityAssessor(self._params)
        self._confidence = confidence_calc  or PortfolioConfidenceCalculator(self._params)
        self._health     = health_monitor   or IntegrationHealthMonitor()
        self._coverage   = coverage_monitor or CoverageMonitor()
        self._callback   = event_callback

        self._lock       = threading.RLock()
        self._running    = False
        self._snapshots  = _SnapshotStore(self._params.snapshot_history_size)
        self._statistics = PortfolioIntegrationStatistics()
        self._qual_stats = QualityStatistics()
        self._qual_hist  = QualityHistory(self._params.quality_history_size)

    # ── Lifecycle ──────────────────────────────────────────────────────────────

    def _on_start(self) -> None:
        """Hook: set internal running flag."""
        with self._lock:
            self._running = True
        _log.info("PortfolioIntelligenceIntegrationEngine started.")
        _audit.log_lifecycle_event(
            self.SYSTEM_ID, "STOPPED", "RUNNING", self.VERSION,
        )

    def _on_stop(self) -> None:
        """Hook: clear internal running flag."""
        with self._lock:
            self._running = False
        _log.info("PortfolioIntelligenceIntegrationEngine stopped.")
        _audit.log_lifecycle_event(
            self.SYSTEM_ID, "RUNNING", "STOPPED", self.VERSION,
        )

    def start(self) -> None:
        """Start the engine (lifecycle + internal running flag)."""
        super().start()

    def stop(self) -> None:
        """Stop the engine (lifecycle + internal running flag)."""
        super().stop()

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self._running

    # ── Receive intelligence ───────────────────────────────────────────────────

    def receive(
        self,
        portfolio_id: str,
        engine_id:    EngineId,
        data:         Dict[str, Any],
        *,
        is_valid:     bool = True,
        error:        Optional[str] = None,
    ) -> EngineContribution:
        """
        Accept intelligence from one upstream engine for a portfolio.
        This is the primary ingestion point.
        """
        contribution = self._aggregator.contribute(
            portfolio_id, engine_id, data, is_valid=is_valid, error=error,
        )
        self._health.record_engine_check(engine_id, is_valid, error=error)
        return contribution

    # ── Integrate ─────────────────────────────────────────────────────────────

    def integrate(
        self,
        portfolio_id: str,
        *,
        publish:      bool = True,
    ) -> PortfolioIntelligenceSnapshot:
        """
        Full integration cycle:
          Aggregate → Validate consistency → Detect/resolve conflicts →
          Score quality → Build canonical snapshot → Publish.

        Returns the PortfolioIntelligenceSnapshot — the ONLY portfolio
        intelligence interface for downstream consumers.
        """
        t0 = time.monotonic()
        succeeded = False
        snapshot  = self._fallback_snapshot(portfolio_id)

        try:
            snapshot  = self._build_snapshot(portfolio_id)
            succeeded = True
        except Exception as exc:
            _get_err_mgr().report_failure(
                self.SYSTEM_ID, exc,
                ErrorContext(
                    engine_id = self.SYSTEM_ID,
                    operation = "integrate",
                    stage     = "portfolio_intelligence_integration",
                ),
            )
            _log.exception(
                "PortfolioIntelligenceIntegrationEngine.integrate failed",
                context={"portfolio_id": portfolio_id},
            )
            snapshot = self._fallback_snapshot(portfolio_id, error=str(exc))
        finally:
            dur_ms = (time.monotonic() - t0) * 1000
            self._health.record_integration(succeeded, dur_ms)
            metric = IntegrationRunMetric(
                portfolio_id       = portfolio_id,
                succeeded          = succeeded,
                duration_ms        = dur_ms,
                n_engines          = snapshot.n_engines_contributed,
                completeness       = snapshot.completeness,
                consistency_score  = snapshot.consistency_score,
                quality_score      = snapshot.quality_score,
                n_conflicts        = snapshot.n_conflicts,
                snapshot_published = publish and succeeded,
            )
            self._statistics.record(metric)

        if publish and succeeded:
            snapshot = dataclasses.replace(
                snapshot,
                status       = SnapshotStatus.PUBLISHED,
                published_at = now_utc(),
            )

        self._snapshots.add(snapshot)
        if self._callback and succeeded:
            self._callback("snapshot_published", snapshot)

        return snapshot

    # ── Query APIs ─────────────────────────────────────────────────────────────

    def current_snapshot(
        self,
        portfolio_id: str,
    ) -> Optional[PortfolioIntelligenceSnapshot]:
        return self._snapshots.latest(portfolio_id)

    def snapshot_history(
        self,
        portfolio_id: str,
        n:            int = 10,
    ) -> List[PortfolioIntelligenceSnapshot]:
        return self._snapshots.recent(portfolio_id, n)

    def portfolio_state(
        self,
        portfolio_id: str,
    ) -> Optional[PortfolioState]:
        snap = self.current_snapshot(portfolio_id)
        return build_state(snap) if snap else None

    def portfolio_summary(
        self,
        portfolio_id: str,
    ) -> Optional[PortfolioSummary]:
        snap = self.current_snapshot(portfolio_id)
        return build_summary(snap) if snap else None

    def validation_report(
        self,
        portfolio_id: str,
    ) -> Optional[ConsistencyValidationReport]:
        merged = self._aggregator.merge(portfolio_id)
        if merged is None:
            return None
        return self._validator.validate(merged, portfolio_id)

    def conflict_report(
        self,
        portfolio_id: str,
    ) -> Optional[ConflictReport]:
        merged = self._aggregator.merge(portfolio_id)
        if merged is None:
            return None
        return self._conflicts.process(merged, portfolio_id)

    def quality_report(
        self,
        portfolio_id: str,
    ) -> Optional[PortfolioQualityReport]:
        snap = self.current_snapshot(portfolio_id)
        if snap is None:
            return None
        return self._quality.assess(
            completeness_score = snap.completeness,
            consistency_score  = snap.consistency_score,
            freshness_score    = snap.freshness_score,
            confidence_score   = snap.confidence_score,
            coverage_score     = snap.completeness,
            portfolio_id       = portfolio_id,
        )

    def coverage_report(
        self,
        portfolio_id: str,
    ) -> CoverageReport:
        state   = self._aggregator.get_state(portfolio_id)
        engines = state.present_engines() if state else []
        return self._coverage.analyze(engines, portfolio_id)

    def health(self) -> IntegrationHealthReport:
        n_active = len(self._snapshots.all_portfolio_ids())
        return self._health.check(n_active)

    def statistics(self) -> PortfolioIntegrationStatisticsSnapshot:
        return self._statistics.snapshot()

    def quality_trend(self, portfolio_id: str, n: int = 10) -> List[float]:
        return self._qual_hist.trend(portfolio_id, n)

    def all_portfolio_ids(self) -> List[str]:
        return self._snapshots.all_portfolio_ids()

    def search_snapshots(
        self,
        portfolio_id: Optional[str] = None,
        min_quality:  float = 0.0,
        n:            int = 20,
    ) -> List[PortfolioIntelligenceSnapshot]:
        pids    = [portfolio_id] if portfolio_id else self._snapshots.all_portfolio_ids()
        results = []
        for pid in pids:
            for snap in self._snapshots.recent(pid, n):
                if snap.quality_score >= min_quality:
                    results.append(snap)
        return results[-n:]

    # ── Internal ──────────────────────────────────────────────────────────────

    def _build_snapshot(self, portfolio_id: str) -> PortfolioIntelligenceSnapshot:
        state = self._aggregator.get_state(portfolio_id)
        if state is None:
            return self._fallback_snapshot(portfolio_id)

        merged       = self._aggregator.merge(portfolio_id)
        completeness = state.completeness()
        freshness    = state.freshness()
        n_engines    = len(state.present_engines())

        val_report      = self._validator.validate(merged, portfolio_id)
        conflict_report = self._conflicts.process(merged, portfolio_id)

        conf_score = self._confidence.calculate(
            present_engines        = state.present_engines(),
            completeness           = completeness,
            n_unresolved_conflicts = conflict_report.n_escalated,
            portfolio_id           = portfolio_id,
        )
        quality = self._quality.assess(
            completeness_score = completeness,
            consistency_score  = val_report.consistency_score,
            freshness_score    = freshness,
            confidence_score   = conf_score.penalized_score,
            coverage_score     = completeness,
            portfolio_id       = portfolio_id,
        )

        qm = QualityRunMetric(
            portfolio_id   = portfolio_id,
            overall_score  = quality.overall_score,
            completeness   = completeness,
            consistency    = val_report.consistency_score,
            freshness      = freshness,
            confidence     = conf_score.penalized_score,
            coverage       = completeness,
            is_publishable = quality.is_publishable,
        )
        self._qual_stats.record(qm)
        self._qual_hist.add(portfolio_id, qm)

        constr = merged.get("construction",    {})
        alloc  = merged.get("allocation",      {})
        optim  = merged.get("optimization",    {})
        div    = merged.get("diversification", {})
        risk   = merged.get("risk",            {})
        perf   = merged.get("performance",     {})
        rebal  = merged.get("rebalancing",     {})
        rec    = merged.get("recommendation",  {})

        is_ready = (
            quality.is_publishable
            and val_report.is_consistent
            and conflict_report.n_escalated == 0
            and completeness >= self._params.min_completeness
        )

        return PortfolioIntelligenceSnapshot(
            portfolio_id             = portfolio_id,
            status                   = SnapshotStatus.VALIDATED,
            aggregation_status       = state.status(),
            n_engines_contributed    = n_engines,
            completeness             = round(completeness, 4),
            freshness_score          = round(freshness, 4),

            portfolio_name           = constr.get("portfolio_name",           ""),
            portfolio_value          = constr.get("portfolio_value",          0.0),
            n_positions              = constr.get("n_positions",              0),
            construction_quality     = constr.get("construction_quality",     0.0),

            equity_weight            = alloc.get("equity_weight",            0.0),
            bond_weight              = alloc.get("bond_weight",              0.0),
            cash_weight              = alloc.get("cash_weight",              0.0),
            alternative_weight       = alloc.get("alternative_weight",       0.0),
            international_weight     = alloc.get("international_weight",     0.0),
            equity_drift             = alloc.get("equity_drift",             0.0),

            optimization_quality     = optim.get("optimization_quality",     0.0),
            is_at_efficient_frontier = optim.get("is_at_efficient_frontier", False),
            optimization_score       = optim.get("optimization_score",       0.0),

            hhi                      = div.get("hhi",                        0.0),
            effective_positions      = div.get("effective_positions",        0.0),
            sector_concentration     = div.get("sector_concentration",       0.0),
            n_sectors                = div.get("n_sectors",                  0),

            portfolio_risk_score     = risk.get("portfolio_risk_score",      0.0),
            risk_budget_utilization  = risk.get("risk_budget_utilization",   0.0),
            var_utilization          = risk.get("var_utilization",           0.0),
            is_risk_within_budget    = risk.get("is_risk_within_budget",     True),
            max_drawdown             = risk.get("max_drawdown",              0.0),

            sharpe_ratio             = perf.get("sharpe_ratio",              0.0),
            alpha                    = perf.get("alpha",                     0.0),
            information_ratio        = perf.get("information_ratio",         0.0),
            ytd_return               = perf.get("ytd_return",                0.0),
            calmar_ratio             = perf.get("calmar_ratio",              0.0),

            rebalance_recommended    = rebal.get("rebalance_recommended",    False),
            rebalance_score          = rebal.get("rebalance_score",          0.0),
            drift_level              = rebal.get("drift_level",              "minor"),

            primary_action           = rec.get("primary_action",             "no_action"),
            recommendation_priority  = rec.get("priority",                   "informational"),
            recommendation_score     = rec.get("recommendation_score",       0.0),
            recommendation_confidence= rec.get("confidence",                 0.0),

            quality_score            = quality.overall_score,
            quality_grade            = quality.grade,
            consistency_score        = val_report.consistency_score,
            confidence_score         = conf_score.penalized_score,
            n_conflicts              = conflict_report.n_detected,
            n_unresolved_conflicts   = conflict_report.n_escalated,
            is_consistent            = val_report.is_consistent,
            is_ready                 = is_ready,
        )

    @staticmethod
    def _fallback_snapshot(
        portfolio_id: str,
        error:        Optional[str] = None,
    ) -> PortfolioIntelligenceSnapshot:
        return PortfolioIntelligenceSnapshot(
            portfolio_id        = portfolio_id,
            status              = SnapshotStatus.DRAFT,
            aggregation_status  = AggregationStatus.INVALID,
            is_consistent       = False,
            is_ready            = False,
        )
