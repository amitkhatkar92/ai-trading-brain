"""iios/investment/decision/risk/decision_risk_engine.py
DecisionRiskEngine — main facade for the Decision Risk Engine.
Consumes EvidenceSnapshot, ReasoningSnapshot, ConfidenceSnapshot.
Produces RiskSnapshot as canonical output.
"""
from __future__ import annotations

import asyncio
import time
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from iios.investment.decision.confidence.confidence_snapshot import ConfidenceSnapshot
from iios.investment.decision.evidence.evidence_snapshot import EvidenceSnapshot
from iios.investment.decision.reasoning.reasoning_snapshot import ReasoningSnapshot
from iios.investment.decision.risk.control_registry import ControlRegistry
from iios.investment.decision.risk.decision_risk import DecisionRisk
from iios.investment.decision.risk.risk_constants import (
    DEFAULT_RISK_TIMEOUT_SECS,
    RiskEngineStatus,
    RiskPolicyStatus,
    RiskQualityGrade,
)
from iios.investment.decision.risk.risk_health import RiskHealthMonitor, RiskHealthReport
from iios.investment.decision.risk.risk_history import RiskHistory
from iios.investment.decision.risk.risk_pipeline import BaseRiskModule, PipelineResult, RiskContext, RiskPipeline
from iios.investment.decision.risk.risk_quality import RiskQualityReport
from iios.investment.decision.risk.risk_snapshot import RiskSnapshot, build_risk_snapshot
from iios.investment.decision.risk.risk_statistics import RiskStatistics, RiskStatisticsTracker
from iios.investment.decision.risk.scenario_registry import ScenarioRegistry


class DecisionRiskEngine:
    """
    Authoritative risk intelligence facade.
    Thread-safe and async-capable.
    Does NOT generate recommendations or execute trades.
    """

    VERSION = "1.0.0"

    def __init__(
        self,
        scenario_registry:  Optional[ScenarioRegistry]    = None,
        control_registry:   Optional[ControlRegistry]     = None,
        custom_modules:     Optional[List[BaseRiskModule]] = None,
        max_allowed_risk:   float = 70.0,
        timeout_secs:       float = DEFAULT_RISK_TIMEOUT_SECS,
    ) -> None:
        self._pipeline  = RiskPipeline(
            scenario_registry=scenario_registry,
            control_registry=control_registry,
            custom_modules=custom_modules,
            max_allowed_risk=max_allowed_risk,
        )
        self._history    = RiskHistory()
        self._stats      = RiskStatisticsTracker()
        self._health     = RiskHealthMonitor()
        self._timeout    = timeout_secs
        self._status     = RiskEngineStatus.INITIALIZING

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start(self) -> None:
        self._health.set_status(RiskEngineStatus.READY)
        self._status = RiskEngineStatus.READY

    def stop(self) -> None:
        self._health.set_status(RiskEngineStatus.STOPPED)
        self._status = RiskEngineStatus.STOPPED

    # ── Core evaluation ───────────────────────────────────────────────────────

    async def evaluate(
        self,
        evidence_snapshot:   EvidenceSnapshot,
        reasoning_snapshot:  ReasoningSnapshot,
        confidence_snapshot: ConfidenceSnapshot,
        decision_id:         Optional[str] = None,
    ) -> RiskSnapshot:
        """
        Async evaluation (runs pipeline in a thread-pool executor to avoid
        blocking the event loop for CPU-bound work).
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.evaluate_sync,
            evidence_snapshot,
            reasoning_snapshot,
            confidence_snapshot,
            decision_id,
        )

    def evaluate_sync(
        self,
        evidence_snapshot:   EvidenceSnapshot,
        reasoning_snapshot:  ReasoningSnapshot,
        confidence_snapshot: ConfidenceSnapshot,
        decision_id:         Optional[str] = None,
    ) -> RiskSnapshot:
        """Synchronous evaluation — runs the full 7-stage pipeline."""
        if self._status == RiskEngineStatus.STOPPED:
            raise RuntimeError("DecisionRiskEngine is stopped — call start() first.")

        d_id = decision_id or str(uuid.uuid4())
        t0   = time.perf_counter()
        t0_dt = datetime.now(timezone.utc)

        try:
            self._health.set_status(RiskEngineStatus.EVALUATING)
            ctx = RiskContext(
                evidence_snapshot=evidence_snapshot,
                reasoning_snapshot=reasoning_snapshot,
                confidence_snapshot=confidence_snapshot,
                decision_id=d_id,
            )
            result: PipelineResult = self._pipeline.run(ctx)
            duration_ms = (time.perf_counter() - t0) * 1000.0

            snapshot = build_risk_snapshot(
                decision_risk          = result.decision_risk,
                evidence_snapshot_id   = evidence_snapshot.snapshot_id,
                reasoning_snapshot_id  = reasoning_snapshot.snapshot_id,
                confidence_snapshot_id = confidence_snapshot.snapshot_id,
                policy_status          = result.policy_result.status,
                quality_grade          = result.quality_report.grade,
                evaluation_start       = t0_dt,
                version                = 1,
            )

            self._history.record(snapshot)
            self._stats.record_success(
                overall_risk=snapshot.overall_risk,
                duration_ms=duration_ms,
            )
            self._health.record_success(duration_ms)
            self._health.set_status(RiskEngineStatus.READY)
            return snapshot

        except Exception as exc:
            duration_ms = (time.perf_counter() - t0) * 1000.0
            self._stats.record_failure()
            self._health.record_failure(duration_ms)
            self._health.set_status(
                RiskEngineStatus.DEGRADED if self._status != RiskEngineStatus.STOPPED
                else RiskEngineStatus.STOPPED
            )
            raise

    # ── Query API ─────────────────────────────────────────────────────────────

    def get_snapshot(self, snapshot_id: str) -> Optional[RiskSnapshot]:
        return self._history.get(snapshot_id)

    def get_history(self, subject_id: str) -> List[RiskSnapshot]:
        return self._history.for_subject(subject_id)

    def get_latest(self, subject_id: str) -> Optional[RiskSnapshot]:
        return self._history.latest_for_subject(subject_id)

    def risk_series(self, subject_id: str) -> List[float]:
        return self._history.risk_series(subject_id)

    def stats(self) -> RiskStatistics:
        return self._stats.summary()

    def health(self) -> RiskHealthReport:
        return self._health.report()

    def get_quality(self, snapshot_id: str) -> Optional[RiskQualityGrade]:
        snap = self._history.get(snapshot_id)
        return snap.quality_grade if snap else None

    def validate_controls(
        self,
        evidence_snapshot:   EvidenceSnapshot,
        reasoning_snapshot:  ReasoningSnapshot,
        confidence_snapshot: ConfidenceSnapshot,
        decision_id:         Optional[str] = None,
    ) -> bool:
        """
        Run a full evaluation and return True iff controls pass.
        Convenience method for pipeline integration.
        """
        snap = self.evaluate_sync(
            evidence_snapshot, reasoning_snapshot, confidence_snapshot, decision_id,
        )
        return not snap.blocks_execution

    def record_outcome(self, snapshot_id: str, outcome: str) -> None:
        """
        Record the eventual outcome of a decision for future calibration.
        Stored as metadata (no scoring model yet).
        """
        # Future: feed into calibration / learning system
        pass
