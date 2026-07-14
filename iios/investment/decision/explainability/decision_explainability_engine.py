"""iios/investment/decision/explainability/decision_explainability_engine.py
DecisionExplainabilityEngine — main facade for the Explainability Engine.

Consumes EvidenceSnapshot, ReasoningSnapshot, ConfidenceSnapshot, RiskSnapshot.
Produces ExplanationSnapshot as canonical output.
Never analyses markets, companies, or strategies independently.
Never generates Buy/Sell/Hold recommendations.
Never executes trades.
"""
from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any, Dict, List, Optional

from iios.investment.decision.confidence.confidence_snapshot import ConfidenceSnapshot
from iios.investment.decision.evidence.evidence_snapshot import EvidenceSnapshot
from iios.investment.decision.reasoning.reasoning_snapshot import ReasoningSnapshot
from iios.investment.decision.risk.risk_snapshot import RiskSnapshot

from iios.investment.decision.explainability.audit_view import AuditView, build_audit_view
from iios.investment.decision.explainability.analyst_view import AnalystView, build_analyst_view
from iios.investment.decision.explainability.counterfactual_engine import (
    CounterfactualEngine,
    CounterfactualReport,
)
from iios.investment.decision.explainability.decision_trace import DecisionTrace
from iios.investment.decision.explainability.developer_view import DeveloperView, build_developer_view
from iios.investment.decision.explainability.executive_view import ExecutiveView, build_executive_view
from iios.investment.decision.explainability.explainability_constants import (
    ExplainabilityStatus,
)
from iios.investment.decision.explainability.explainability_health import (
    ExplainabilityHealthMonitor,
    ExplainabilityHealthReport,
)
from iios.investment.decision.explainability.explanation_formatter import (
    ExplanationFormatter,
    ExplanationFormat,
)
from iios.investment.decision.explainability.explanation_generator import (
    ExplainabilityInput,
    ExplanationGenerator,
)
from iios.investment.decision.explainability.explanation_history import ExplanationHistory
from iios.investment.decision.explainability.explanation_snapshot import ExplanationSnapshot
from iios.investment.decision.explainability.explanation_statistics import (
    ExplanationStatistics,
    ExplanationStatisticsTracker,
)
from iios.investment.decision.explainability.traceability_engine import TraceabilityEngine


class DecisionExplainabilityEngine:
    """
    Authoritative explainability layer for every IIOS decision assessment.

    Thread-safe and async-capable.
    All explanations are deterministic, reproducible, and fully traceable.
    """

    VERSION = "1.0.0"

    def __init__(self) -> None:
        self._generator   = ExplanationGenerator()
        self._formatter   = ExplanationFormatter()
        self._counterfact = CounterfactualEngine()
        self._trace_eng   = TraceabilityEngine()
        self._history     = ExplanationHistory()
        self._stats       = ExplanationStatisticsTracker()
        self._health      = ExplainabilityHealthMonitor()
        self._status      = ExplainabilityStatus.INITIALIZING

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start(self) -> None:
        self._health.set_status(ExplainabilityStatus.READY)
        self._status = ExplainabilityStatus.READY

    def stop(self) -> None:
        self._health.set_status(ExplainabilityStatus.STOPPED)
        self._status = ExplainabilityStatus.STOPPED

    # ── Core explanation generation ───────────────────────────────────────────

    async def explain(
        self,
        evidence_snapshot:   EvidenceSnapshot,
        reasoning_snapshot:  ReasoningSnapshot,
        confidence_snapshot: ConfidenceSnapshot,
        risk_snapshot:       RiskSnapshot,
        decision_id:         Optional[str] = None,
    ) -> ExplanationSnapshot:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.explain_sync,
            evidence_snapshot,
            reasoning_snapshot,
            confidence_snapshot,
            risk_snapshot,
            decision_id,
        )

    def explain_sync(
        self,
        evidence_snapshot:   EvidenceSnapshot,
        reasoning_snapshot:  ReasoningSnapshot,
        confidence_snapshot: ConfidenceSnapshot,
        risk_snapshot:       RiskSnapshot,
        decision_id:         Optional[str] = None,
    ) -> ExplanationSnapshot:
        if self._status == ExplainabilityStatus.STOPPED:
            raise RuntimeError("DecisionExplainabilityEngine is stopped — call start() first.")

        d_id = decision_id or str(uuid.uuid4())
        t0   = time.perf_counter()

        try:
            self._health.set_status(ExplainabilityStatus.GENERATING)
            inp = ExplainabilityInput(
                evidence_snapshot=evidence_snapshot,
                reasoning_snapshot=reasoning_snapshot,
                confidence_snapshot=confidence_snapshot,
                risk_snapshot=risk_snapshot,
            )
            snapshot = self._generator.generate(inp, d_id, version=1)

            self._history.record(snapshot)
            self._stats.record_success(
                outcome=snapshot.outcome,
                score=snapshot.explainability_score,
                duration_ms=(time.perf_counter() - t0) * 1000.0,
            )
            self._health.record_success((time.perf_counter() - t0) * 1000.0)
            self._health.set_status(ExplainabilityStatus.READY)
            return snapshot

        except Exception:
            self._stats.record_failure()
            self._health.record_failure((time.perf_counter() - t0) * 1000.0)
            if self._status != ExplainabilityStatus.STOPPED:
                self._health.set_status(ExplainabilityStatus.DEGRADED)
            raise

    # ── Query API ─────────────────────────────────────────────────────────────

    def get_snapshot(self, snapshot_id: str) -> Optional[ExplanationSnapshot]:
        return self._history.get(snapshot_id)

    def get_latest(self, subject_id: str) -> Optional[ExplanationSnapshot]:
        return self._history.latest_for_subject(subject_id)

    def get_history(self, subject_id: str) -> List[ExplanationSnapshot]:
        return self._history.for_subject(subject_id)

    def get_by_decision(self, decision_id: str) -> Optional[ExplanationSnapshot]:
        return self._history.for_decision(decision_id)

    def outcome_series(self, subject_id: str) -> List[str]:
        return self._history.outcome_series(subject_id)

    def score_series(self, subject_id: str) -> List[float]:
        return self._history.score_series(subject_id)

    def stats(self) -> ExplanationStatistics:
        return self._stats.summary()

    def health(self) -> ExplainabilityHealthReport:
        return self._health.report()

    # ── View generators ───────────────────────────────────────────────────────

    def executive_view(self, snapshot: ExplanationSnapshot) -> ExecutiveView:
        return build_executive_view(snapshot)

    def analyst_view(self, snapshot: ExplanationSnapshot) -> AnalystView:
        return build_analyst_view(snapshot)

    def developer_view(self, snapshot: ExplanationSnapshot) -> DeveloperView:
        return build_developer_view(snapshot)

    def audit_view(
        self,
        snapshot:           ExplanationSnapshot,
        evidence_snapshot:  EvidenceSnapshot,
        reasoning_snapshot: ReasoningSnapshot,
        confidence_snapshot: ConfidenceSnapshot,
        risk_snapshot:      RiskSnapshot,
        policy_compliance:  str = "compliant",
    ) -> AuditView:
        inp   = ExplainabilityInput(
            evidence_snapshot, reasoning_snapshot, confidence_snapshot, risk_snapshot,
        )
        trace = self._generator.build_trace(inp, snapshot.outcome.value)
        return build_audit_view(snapshot, trace, policy_compliance)

    # ── Counterfactual ────────────────────────────────────────────────────────

    def counterfactual(self, snapshot: ExplanationSnapshot) -> CounterfactualReport:
        controls_breached = snapshot.explanation.opposing_factors and any(
            "controls breached" in f.name.lower()
            for f in snapshot.explanation.opposing_factors
        )
        return self._counterfact.analyze(
            snapshot.explanation, bool(controls_breached),
        )

    # ── Trace ─────────────────────────────────────────────────────────────────

    def get_trace(
        self,
        evidence_snapshot:   EvidenceSnapshot,
        reasoning_snapshot:  ReasoningSnapshot,
        confidence_snapshot: ConfidenceSnapshot,
        risk_snapshot:       RiskSnapshot,
        outcome:             str,
    ) -> DecisionTrace:
        return self._trace_eng.build_trace(
            evidence_snapshot, reasoning_snapshot,
            confidence_snapshot, risk_snapshot, outcome,
        )

    # ── Formatting ────────────────────────────────────────────────────────────

    def format(
        self,
        snapshot: ExplanationSnapshot,
        fmt:      ExplanationFormat = ExplanationFormat.DICT,
    ) -> Any:
        return self._formatter.format(snapshot, fmt)
