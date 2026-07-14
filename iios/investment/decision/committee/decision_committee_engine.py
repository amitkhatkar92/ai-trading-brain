"""iios/investment/decision/committee/decision_committee_engine.py
DecisionCommitteeEngine — main public facade for the Committee Engine.

Responsibilities:
  - Initialise committee runtime (start / stop lifecycle)
  - Accept complete decision packages (Evidence + Reasoning + Confidence + Risk + Explanation)
  - Run committee deliberation (sync and async)
  - Maintain session history
  - Expose query APIs (reports, stats, health)

This engine does NOT generate investment recommendations.
It does NOT execute trades.
It does NOT independently analyse markets, companies, or strategies.
"""
from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any, Dict, List, Optional

from iios.investment.decision.confidence.confidence_snapshot import ConfidenceSnapshot
from iios.investment.decision.evidence.evidence_snapshot import EvidenceSnapshot
from iios.investment.decision.explainability.explanation_snapshot import ExplanationSnapshot
from iios.investment.decision.reasoning.reasoning_snapshot import ReasoningSnapshot
from iios.investment.decision.risk.risk_snapshot import RiskSnapshot

from iios.investment.decision.committee.committee_constants import CommitteeStatus
from iios.investment.decision.committee.committee_context import CommitteeContext
from iios.investment.decision.committee.committee_health import (
    CommitteeHealthMonitor,
    CommitteeHealthReport,
)
from iios.investment.decision.committee.committee_history import CommitteeHistory
from iios.investment.decision.committee.committee_orchestrator import CommitteeOrchestrator
from iios.investment.decision.committee.committee_report import CommitteeReport
from iios.investment.decision.committee.committee_statistics import (
    CommitteeStatistics,
    CommitteeStatisticsTracker,
)
from iios.investment.decision.committee.member_registry import MemberRegistry


class DecisionCommitteeEngine:
    """
    Authoritative multi-agent committee layer of IIOS Decision Intelligence.

    All committee actions are deterministic, reproducible, explainable,
    auditable, version-controlled, and fully traceable back to the underlying
    evidence and reasoning.

    Thread-safe and async-capable.
    """

    VERSION = "1.0.0"

    def __init__(
        self,
        registry: Optional[MemberRegistry] = None,
    ) -> None:
        self._registry    = registry
        self._orchestrator = CommitteeOrchestrator(registry)
        self._history     = CommitteeHistory()
        self._stats       = CommitteeStatisticsTracker()
        self._health      = CommitteeHealthMonitor()
        self._status      = CommitteeStatus.INITIALIZING

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start(self) -> None:
        self._health.set_status(CommitteeStatus.READY)
        self._status = CommitteeStatus.READY

    def stop(self) -> None:
        self._health.set_status(CommitteeStatus.STOPPED)
        self._status = CommitteeStatus.STOPPED

    # ── Primary entry points ──────────────────────────────────────────────────

    async def run_committee(
        self,
        evidence_snapshot:    EvidenceSnapshot,
        reasoning_snapshot:   ReasoningSnapshot,
        confidence_snapshot:  ConfidenceSnapshot,
        risk_snapshot:        RiskSnapshot,
        explanation_snapshot: ExplanationSnapshot,
        decision_id:          Optional[str] = None,
        version:              int           = 1,
    ) -> CommitteeReport:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.run_committee_sync,
            evidence_snapshot,
            reasoning_snapshot,
            confidence_snapshot,
            risk_snapshot,
            explanation_snapshot,
            decision_id,
            version,
        )

    def run_committee_sync(
        self,
        evidence_snapshot:    EvidenceSnapshot,
        reasoning_snapshot:   ReasoningSnapshot,
        confidence_snapshot:  ConfidenceSnapshot,
        risk_snapshot:        RiskSnapshot,
        explanation_snapshot: ExplanationSnapshot,
        decision_id:          Optional[str] = None,
        version:              int           = 1,
    ) -> CommitteeReport:
        if self._status == CommitteeStatus.STOPPED:
            raise RuntimeError("DecisionCommitteeEngine is stopped — call start() first.")

        d_id = decision_id or str(uuid.uuid4())
        t0   = time.perf_counter()

        try:
            self._health.set_status(CommitteeStatus.RUNNING)

            ctx = CommitteeContext(
                decision_id  = d_id,
                subject_id   = evidence_snapshot.subject_id,
                subject_type = evidence_snapshot.subject_type,
                evidence     = evidence_snapshot,
                reasoning    = reasoning_snapshot,
                confidence   = confidence_snapshot,
                risk         = risk_snapshot,
                explanation  = explanation_snapshot,
            )

            report = self._orchestrator.run_sync(ctx, d_id, version)
            duration_ms = (time.perf_counter() - t0) * 1000.0

            self._history.record(report)
            self._stats.record_success(report.position, report.committee_score, duration_ms)
            self._health.record_success(duration_ms)
            self._health.set_status(CommitteeStatus.READY)
            return report

        except Exception:
            duration_ms = (time.perf_counter() - t0) * 1000.0
            self._stats.record_failure(duration_ms)
            self._health.record_failure(duration_ms)
            if self._status != CommitteeStatus.STOPPED:
                self._health.set_status(CommitteeStatus.DEGRADED)
            raise

    # ── Query APIs ────────────────────────────────────────────────────────────

    def get_report(self, report_id: str) -> Optional[CommitteeReport]:
        return self._history.get(report_id)

    def get_by_decision(self, decision_id: str) -> Optional[CommitteeReport]:
        return self._history.for_decision(decision_id)

    def get_latest(self, subject_id: str) -> Optional[CommitteeReport]:
        return self._history.latest_for_subject(subject_id)

    def get_history(self, subject_id: str) -> List[CommitteeReport]:
        return self._history.for_subject(subject_id)

    def recent(self, n: int = 10) -> List[CommitteeReport]:
        return self._history.recent(n)

    def position_series(self, subject_id: str) -> List[str]:
        return self._history.position_series(subject_id)

    def score_series(self, subject_id: str) -> List[float]:
        return self._history.score_series(subject_id)

    def known_subjects(self) -> List[str]:
        return self._history.known_subjects()

    # ── Stats & Health ────────────────────────────────────────────────────────

    def stats(self) -> CommitteeStatistics:
        return self._stats.summary()

    def health(self) -> CommitteeHealthReport:
        return self._health.report()
