"""iios/investment/decision/explainability/explanation_generator.py
ExplanationGenerator — orchestrates generation of a complete ExplanationSnapshot.
"""
from __future__ import annotations

import time
from dataclasses import dataclass

from iios.investment.decision.confidence.confidence_snapshot import ConfidenceSnapshot
from iios.investment.decision.evidence.evidence_snapshot import EvidenceSnapshot
from iios.investment.decision.reasoning.reasoning_snapshot import ReasoningSnapshot
from iios.investment.decision.risk.risk_snapshot import RiskSnapshot
from iios.investment.decision.explainability.decision_trace import DecisionTrace
from iios.investment.decision.explainability.explanation_snapshot import (
    ExplanationSnapshot,
    build_explanation_snapshot,
)
from iios.investment.decision.explainability.summary_builder import SummaryBuilder, derive_outcome
from iios.investment.decision.explainability.traceability_engine import TraceabilityEngine
from iios.investment.decision.explainability.transparency_score import TransparencyScorer
from iios.investment.decision.explainability.explainability_quality import ExplainabilityQualityEvaluator


@dataclass(frozen=True)
class ExplainabilityInput:
    """Immutable bundle of all upstream engine snapshots."""
    evidence_snapshot:   EvidenceSnapshot
    reasoning_snapshot:  ReasoningSnapshot
    confidence_snapshot: ConfidenceSnapshot
    risk_snapshot:       RiskSnapshot


class ExplanationGenerator:
    """
    Orchestrates explanation generation from 4 upstream engine snapshots.
    Thread-safe — all components are stateless per-call.
    """

    def __init__(self) -> None:
        self._summary_builder  = SummaryBuilder()
        self._trace_engine     = TraceabilityEngine()
        self._transparency     = TransparencyScorer()
        self._quality          = ExplainabilityQualityEvaluator()

    def generate(
        self,
        inp:         ExplainabilityInput,
        decision_id: str,
        version:     int = 1,
    ) -> ExplanationSnapshot:
        t0 = time.perf_counter()

        ev = inp.evidence_snapshot
        rs = inp.reasoning_snapshot
        cs = inp.confidence_snapshot
        ri = inp.risk_snapshot

        # 1. Derive deterministic outcome
        outcome = derive_outcome(ev, cs, ri)

        # 2. Build structured explanation
        explanation = self._summary_builder.build(ev, rs, cs, ri)

        # 3. Build traceability graph
        trace = self._trace_engine.build_trace(ev, rs, cs, ri, outcome.value)
        traceability_level = self._trace_engine.traceability_level(trace)

        # 4. Compute transparency score
        transparency_score = self._transparency.score(explanation, trace)

        # 5. Compute overall explainability quality
        quality_score = self._quality.evaluate(explanation, trace, transparency_score)

        duration_ms = (time.perf_counter() - t0) * 1000.0

        return build_explanation_snapshot(
            decision_id            = decision_id,
            subject_id             = ev.subject_id,
            subject_type           = ev.subject_type,
            evidence_snapshot_id   = ev.snapshot_id,
            reasoning_snapshot_id  = rs.snapshot_id,
            confidence_snapshot_id = cs.snapshot_id,
            risk_snapshot_id       = ri.snapshot_id,
            explanation            = explanation,
            outcome                = outcome,
            explainability_score   = quality_score,
            transparency_score     = transparency_score,
            traceability_level     = traceability_level,
            generation_duration_ms = round(duration_ms, 2),
            version                = version,
        )

    def build_trace(self, inp: ExplainabilityInput, outcome: str) -> DecisionTrace:
        """Standalone trace build (used by query API)."""
        return self._trace_engine.build_trace(
            inp.evidence_snapshot,
            inp.reasoning_snapshot,
            inp.confidence_snapshot,
            inp.risk_snapshot,
            outcome,
        )
