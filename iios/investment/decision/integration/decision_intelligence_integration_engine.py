"""iios/investment/decision/integration/decision_intelligence_integration_engine.py
DecisionIntelligenceIntegrationEngine — the single orchestration, validation,
quality assurance, and publishing layer for all Decision Intelligence.

Every downstream component (Execution, Portfolio Intelligence, Monitoring,
Reporting, Audit) must consume ONLY the DecisionIntelligenceSnapshot produced
by this engine.

This engine NEVER independently calculates Evidence, Reasoning, Scores,
Confidence, Risk, Explainability, Committee Results, or Recommendations.
Its sole responsibility: integrate, validate, reconcile, score, monitor,
and publish one canonical DecisionIntelligenceSnapshot.
"""
from __future__ import annotations

import threading
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any, Deque, Dict, List, Optional

from iios.common.async_exec.async_execution_manager import get_execution_manager as _get_exec_manager
from iios.common.async_exec.execution_classifier import WorkloadType

from iios.investment.decision.confidence.confidence_snapshot import ConfidenceSnapshot
from iios.investment.decision.evidence.evidence_snapshot import EvidenceSnapshot
from iios.investment.decision.explainability.explanation_snapshot import ExplanationSnapshot
from iios.investment.decision.reasoning.reasoning_snapshot import ReasoningSnapshot
from iios.investment.decision.risk.risk_snapshot import RiskSnapshot

from iios.investment.decision.integration.aggregation_state import _AggregationStateSnapshot
from iios.investment.decision.integration.conflict_engine import ConflictEngine, ConflictReport
from iios.investment.decision.integration.consistency_validator import ConsistencyValidator
from iios.investment.decision.integration.coverage_monitor import CoverageReport
from iios.investment.decision.integration.decision_confidence import (
    IntegrationConfidenceCalculator,
)
from iios.investment.decision.integration.decision_quality import DecisionQualityEvaluator
from iios.investment.decision.integration.decision_snapshot import (
    DecisionIntelligenceSnapshot,
    build_decision_snapshot,
)
from iios.investment.decision.integration.decision_state import build_decision_state
from iios.investment.decision.integration.decision_statistics import (
    IntegrationStatistics,
    IntegrationStatisticsTracker,
)
from iios.investment.decision.integration.decision_summary import DecisionSummaryBuilder
from iios.investment.decision.integration.decision_intelligence_aggregator import (
    DecisionIntelligenceAggregator,
)
from iios.investment.decision.integration.health_monitor import (
    IntegrationHealthMonitor,
    IntegrationHealthReport,
)
from iios.investment.decision.integration.integration_constants import (
    ComponentId,
    IntegrationStatus,
    SnapshotStatus,
    ValidationStatus,
)
from iios.investment.decision.integration.quality_history import QualityHistory
from iios.investment.decision.integration.quality_statistics import (
    QualityStatistics,
    QualityStatisticsTracker,
)
from iios.investment.decision.integration.validation_report import ValidationReport
from iios.investment.workflow.engine_lifecycle import LifecycleAwareMixin

from iios.common.logging.logging_manager import get_logger
from iios.common.logging.audit_logger import get_audit_logger

_log = get_logger(__name__, engine_id="iios:decision:intelligence:integration")
_audit = get_audit_logger(
    __name__,
    engine_id = "iios:decision:intelligence:integration",
    component = "DecisionIntelligenceIntegrationEngine",
)


class DecisionIntelligenceIntegrationEngine(LifecycleAwareMixin):
    """
    Single orchestration layer for all Decision Intelligence.

    Usage (sync):
        engine = DecisionIntelligenceIntegrationEngine()
        engine.start()
        snap = engine.integrate_sync(
            evidence=ev, reasoning=rs, confidence=cs,
            risk=ri, explanation=ex, committee=cr,
            decision_id="DEC-001",
        )
        engine.stop()

    Usage (async):
        async with asyncio.TaskGroup() as tg:
            snap = await engine.integrate(...)
    """

    VERSION   = "1.0.0"
    SYSTEM_ID = "iios:decision:intelligence:integration"

    def __init__(self) -> None:
        self._lock          = threading.RLock()
        self._status        = IntegrationStatus.INITIALIZING

        # Sub-engines (all stateless or thread-safe)
        self._aggregator    = DecisionIntelligenceAggregator()
        self._validator     = ConsistencyValidator()
        self._conflict_eng  = ConflictEngine()
        self._quality_eval  = DecisionQualityEvaluator()
        self._conf_calc     = IntegrationConfidenceCalculator()
        self._summary_bld   = DecisionSummaryBuilder()

        # State stores
        self._snapshots:    Dict[str, DecisionIntelligenceSnapshot] = {}
        self._snapshot_hist: Deque[DecisionIntelligenceSnapshot]    = deque(maxlen=500)

        # Monitoring + stats
        self._health        = IntegrationHealthMonitor()
        self._stats         = IntegrationStatisticsTracker()
        self._quality_stats = QualityStatisticsTracker()
        self._quality_hist  = QualityHistory()

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def _on_start(self) -> None:
        """Hook: set internal IntegrationStatus to READY."""
        self._health.set_status(IntegrationStatus.READY)
        with self._lock:
            self._status = IntegrationStatus.READY
        _log.info("DecisionIntelligenceIntegrationEngine ready.")
        _audit.log_lifecycle_event(
            self.SYSTEM_ID, "STOPPED", "RUNNING", self.VERSION,
        )

    def _on_stop(self) -> None:
        """Hook: set internal IntegrationStatus to STOPPED."""
        self._health.set_status(IntegrationStatus.STOPPED)
        with self._lock:
            self._status = IntegrationStatus.STOPPED
        _log.info("DecisionIntelligenceIntegrationEngine stopped.")
        _audit.log_lifecycle_event(
            self.SYSTEM_ID, "RUNNING", "STOPPED", self.VERSION,
        )

    def start(self) -> None:
        """Start the integration engine (lifecycle + internal status update)."""
        super().start()

    def stop(self) -> None:
        """Stop the integration engine (lifecycle + internal status update)."""
        super().stop()

    # ── Primary synchronous entry point ───────────────────────────────────────

    def integrate_sync(
        self,
        decision_id:    str,
        subject_id:     str = "",
        subject_type:   str = "equity",
        version:        int = 1,
        evidence:       Optional[EvidenceSnapshot]    = None,
        reasoning:      Optional[ReasoningSnapshot]   = None,
        confidence:     Optional[ConfidenceSnapshot]  = None,
        risk:           Optional[RiskSnapshot]        = None,
        explanation:    Optional[ExplanationSnapshot] = None,
        committee:      Optional[Any]                 = None,
        recommendation: Optional[Any]                 = None,
    ) -> DecisionIntelligenceSnapshot:
        self._assert_running()
        t0 = time.perf_counter()

        # Resolve subject_id / subject_type from snapshots if not supplied
        for snap in (evidence, reasoning, explanation, committee):
            if snap is not None:
                sid  = getattr(snap, "subject_id",   None)
                stype= getattr(snap, "subject_type",  None)
                if sid   and not subject_id:   subject_id   = sid
                if stype and not subject_type: subject_type = stype
                break

        try:
            # 1 — Aggregate all upstream snapshots
            agg_state = self._aggregator._engine.create(
                decision_id    = decision_id,
                subject_id     = subject_id,
                subject_type   = subject_type,
                evidence       = evidence,
                reasoning      = reasoning,
                confidence     = confidence,
                risk           = risk,
                explanation    = explanation,
                committee      = committee,
                recommendation = recommendation,
            )
            snap = agg_state.snapshot()

            # Notify health monitors
            for cid, val in [
                (ComponentId.EVIDENCE,       evidence),
                (ComponentId.REASONING,      reasoning),
                (ComponentId.CONFIDENCE,     confidence),
                (ComponentId.RISK,           risk),
                (ComponentId.EXPLANATION,    explanation),
                (ComponentId.COMMITTEE,      committee),
                (ComponentId.RECOMMENDATION, recommendation),
            ]:
                if val is not None:
                    self._health.record_component_update(cid)

            # 2 — Validate consistency
            validation_report = self._validator.validate(snap)

            # 3 — Detect and resolve conflicts
            conflict_report = self._conflict_eng.run(snap)

            # 4 — Coverage
            coverage_report = self._health.coverage_monitor.evaluate(snap.present_components)

            # 5 — Calculate integration confidence and quality
            integration_conf = self._conf_calc.calculate(snap)
            quality_score    = self._quality_eval.evaluate(
                snap, validation_report, conflict_report, integration_conf,
            )
            intel_score = self._quality_eval.overall_intelligence_score(
                snap, integration_conf, quality_score, conflict_report,
            )

            # 6 — Build per-engine summaries
            ev_sum  = self._summary_bld.evidence(snap)
            rs_sum  = self._summary_bld.reasoning(snap)
            cs_sum  = self._summary_bld.confidence(snap)
            ri_sum  = self._summary_bld.risk(snap)
            ex_sum  = self._summary_bld.explanation(snap)
            cm_sum  = self._summary_bld.committee(snap)
            rec_sum = self._summary_bld.recommendation(snap)

            # 7 — Determine overall status
            ss = SnapshotStatus.COMPLETE if snap.is_complete else SnapshotStatus.PARTIAL
            vs = validation_report.overall_status

            # 8 — Build decision state
            dec_state = build_decision_state(
                decision_id       = decision_id,
                subject_id        = subject_id,
                subject_type      = subject_type,
                completeness      = snap.completeness,
                present           = snap.present_components,
                blocks_publishing = conflict_report.blocks_publishing,
                is_valid          = not validation_report.overall_status.is_blocking,
                version           = version,
            )

            # 9 — Build canonical snapshot
            dur_ms = (time.perf_counter() - t0) * 1000.0
            di_snap = build_decision_snapshot(
                decision_id            = decision_id,
                subject_id             = subject_id,
                subject_type           = subject_type,
                version                = version,
                decision_state         = dec_state,
                snapshot_status        = ss,
                validation_status      = vs,
                evidence_summary       = ev_sum,
                reasoning_summary      = rs_sum,
                confidence_summary     = cs_sum,
                risk_summary           = ri_sum,
                explanation_summary    = ex_sum,
                committee_summary      = cm_sum,
                recommendation_summary = rec_sum,
                overall_intelligence_score = intel_score,
                overall_confidence         = integration_conf,
                quality_score              = quality_score,
                completeness               = snap.completeness,
                total_conflicts            = len(conflict_report.all_conflicts),
                unresolved_conflicts       = len(conflict_report.unresolved),
                blocking_conflicts         = conflict_report.critical_count,
                validation_check_count     = len(validation_report.checks),
                validation_warning_count   = validation_report.warning_count,
                validation_invalid_count   = validation_report.invalid_count,
                integration_duration_ms    = dur_ms,
            )

            # 10 — Store and record metrics
            with self._lock:
                self._snapshots[decision_id]       = di_snap
                self._snapshot_hist.append(di_snap)

            self._stats.record_success(
                ss, quality_score, integration_conf,
                had_conflicts=bool(conflict_report.all_conflicts),
            )
            self._quality_stats.record(quality_score, snap.completeness)
            self._quality_hist.record(
                decision_id, subject_id, quality_score,
                intel_score, integration_conf, snap.completeness,
            )
            self._health.record_success(dur_ms)

            return di_snap

        except Exception:
            _log.exception(
                "DecisionIntelligenceIntegrationEngine.integrate_sync failed",
                context={"decision_id": decision_id},
            )
            self._stats.record_failure()
            self._health.record_failure()
            raise

    # ── Async entry point ─────────────────────────────────────────────────────

    async def integrate(
        self,
        decision_id:    str,
        subject_id:     str = "",
        subject_type:   str = "equity",
        version:        int = 1,
        evidence:       Optional[EvidenceSnapshot]    = None,
        reasoning:      Optional[ReasoningSnapshot]   = None,
        confidence:     Optional[ConfidenceSnapshot]  = None,
        risk:           Optional[RiskSnapshot]        = None,
        explanation:    Optional[ExplanationSnapshot] = None,
        committee:      Optional[Any]                 = None,
        recommendation: Optional[Any]                 = None,
    ) -> DecisionIntelligenceSnapshot:
        return await _get_exec_manager().execute(
            lambda: self.integrate_sync(
                decision_id    = decision_id,
                subject_id     = subject_id,
                subject_type   = subject_type,
                version        = version,
                evidence       = evidence,
                reasoning      = reasoning,
                confidence     = confidence,
                risk           = risk,
                explanation    = explanation,
                committee      = committee,
                recommendation = recommendation,
            ),
            workload_type = WorkloadType.IO_BOUND,
            operation     = "decision.integrate",
            engine_id     = self.SYSTEM_ID,
        )

    # ── Individual snapshot submission API ────────────────────────────────────

    def submit_evidence(self, snapshot: EvidenceSnapshot) -> None:
        self._assert_running()
        self._aggregator.submit_evidence(snapshot)
        self._health.record_component_update(ComponentId.EVIDENCE)

    def submit_reasoning(self, snapshot: ReasoningSnapshot) -> None:
        self._assert_running()
        self._aggregator.submit_reasoning(snapshot)
        self._health.record_component_update(ComponentId.REASONING)

    def submit_confidence(self, snapshot: ConfidenceSnapshot) -> None:
        self._assert_running()
        self._aggregator.submit_confidence(snapshot)
        self._health.record_component_update(ComponentId.CONFIDENCE)

    def submit_risk(self, snapshot: RiskSnapshot) -> None:
        self._assert_running()
        self._aggregator.submit_risk(snapshot)
        self._health.record_component_update(ComponentId.RISK)

    def submit_explanation(self, snapshot: ExplanationSnapshot) -> None:
        self._assert_running()
        self._aggregator.submit_explanation(snapshot)
        self._health.record_component_update(ComponentId.EXPLANATION)

    def submit_committee(self, report: Any) -> None:
        self._assert_running()
        self._aggregator.submit_committee(report)
        self._health.record_component_update(ComponentId.COMMITTEE)

    def submit_recommendation(self, snapshot: Any) -> None:
        self._assert_running()
        self._aggregator.submit_recommendation(snapshot)
        self._health.record_component_update(ComponentId.RECOMMENDATION)

    # ── Query API ─────────────────────────────────────────────────────────────

    def get_snapshot(self, decision_id: str) -> Optional[DecisionIntelligenceSnapshot]:
        with self._lock:
            return self._snapshots.get(decision_id)

    def get_latest_for_subject(self, subject_id: str) -> Optional[DecisionIntelligenceSnapshot]:
        rec = self._quality_hist.for_subject(subject_id)
        if not rec:
            return None
        latest = rec[-1]
        return self.get_snapshot(latest.decision_id)

    def get_validation_report(self, decision_id: str) -> Optional[ValidationReport]:
        """Re-validates the latest aggregation state for a decision."""
        state = self._aggregator.get_state(decision_id)
        if state is None:
            return None
        snap = state.snapshot()
        return self._validator.validate(snap)

    def get_conflict_report(self, decision_id: str) -> Optional[ConflictReport]:
        state = self._aggregator.get_state(decision_id)
        if state is None:
            return None
        return self._conflict_eng.run(state.snapshot())

    def recent_snapshots(self, n: int = 20) -> List[DecisionIntelligenceSnapshot]:
        with self._lock:
            items = list(self._snapshot_hist)
            return items[-n:]

    def known_decisions(self) -> List[str]:
        with self._lock:
            return list(self._snapshots.keys())

    def intelligence_score_series(self, subject_id: str) -> List[float]:
        return [r.intelligence_score for r in self._quality_hist.for_subject(subject_id)]

    def quality_score_series(self, subject_id: str) -> List[float]:
        return self._quality_hist.quality_series(subject_id)

    # ── Monitoring & statistics ───────────────────────────────────────────────

    def stats(self) -> IntegrationStatistics:
        return self._stats.summary()

    def quality_stats(self) -> QualityStatistics:
        return self._quality_stats.summary()

    def health(self) -> IntegrationHealthReport:
        return self._health.report()

    # ── Guard ─────────────────────────────────────────────────────────────────

    def _assert_running(self) -> None:
        with self._lock:
            if not self._status.is_operational:
                raise RuntimeError(
                    f"DecisionIntelligenceIntegrationEngine is not operational "
                    f"(status={self._status.value}). Call start() first."
                )
