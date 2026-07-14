"""iios/investment/decision/explainability/traceability_engine.py
TraceabilityEngine — builds a DecisionTrace from all 4 upstream snapshots.
"""
from __future__ import annotations

from iios.investment.decision.confidence.confidence_snapshot import ConfidenceSnapshot
from iios.investment.decision.evidence.evidence_snapshot import EvidenceSnapshot
from iios.investment.decision.reasoning.reasoning_snapshot import ReasoningSnapshot
from iios.investment.decision.risk.risk_snapshot import RiskSnapshot
from iios.investment.decision.explainability.decision_trace import DecisionTrace
from iios.investment.decision.explainability.evidence_mapper import EvidenceMapper
from iios.investment.decision.explainability.explainability_constants import (
    FULL_TRACEABILITY_ITEM_MIN,
    MIN_STEPS_FOR_FULL_TRACEABILITY,
    TraceabilityLevel,
)
from iios.investment.decision.explainability.reasoning_mapper import ReasoningMapper


def _derive_traceability_level(
    evidence_item_count: int,
    reasoning_step_count: int,
    traced_fraction: float,
) -> TraceabilityLevel:
    if (evidence_item_count >= FULL_TRACEABILITY_ITEM_MIN
            and reasoning_step_count >= MIN_STEPS_FOR_FULL_TRACEABILITY
            and traced_fraction >= 0.70):
        return TraceabilityLevel.FULL
    if evidence_item_count >= 3 and reasoning_step_count >= 1:
        return TraceabilityLevel.PARTIAL
    if evidence_item_count >= 1:
        return TraceabilityLevel.MINIMAL
    return TraceabilityLevel.NONE


class TraceabilityEngine:
    """Builds the complete traceability graph from upstream engine outputs."""

    def __init__(self) -> None:
        self._ev_mapper = EvidenceMapper()
        self._rs_mapper = ReasoningMapper()

    def build_trace(
        self,
        evidence_snapshot:   EvidenceSnapshot,
        reasoning_snapshot:  ReasoningSnapshot,
        confidence_snapshot: ConfidenceSnapshot,
        risk_snapshot:       RiskSnapshot,
        outcome:             str,
    ) -> DecisionTrace:
        # Map reasoning first to get referenced evidence keys
        reasoning_nodes, reasoned_keys = self._rs_mapper.map(reasoning_snapshot)

        # Map evidence with reference knowledge
        evidence_nodes = self._ev_mapper.map(evidence_snapshot, reasoned_keys)

        dc = confidence_snapshot.decision_confidence
        dr = risk_snapshot.decision_risk

        # Compute traced fraction
        if evidence_nodes:
            traced = sum(1 for n in evidence_nodes if n.reasoning_referenced)
            traced_fraction = traced / len(evidence_nodes)
        else:
            traced_fraction = 0.0

        trace = DecisionTrace(
            decision_id           = risk_snapshot.decision_id,
            subject_id            = evidence_snapshot.subject_id,
            evidence_nodes        = tuple(evidence_nodes),
            reasoning_nodes       = tuple(reasoning_nodes),
            reasoning_conclusion  = reasoning_snapshot.reasoning_chain.final_conclusion,
            evidence_confidence   = dc.evidence_confidence,
            reasoning_confidence  = dc.reasoning_confidence,
            overall_confidence    = confidence_snapshot.overall_confidence,
            confidence_level      = confidence_snapshot.confidence_level.value,
            market_risk           = dr.market_risk,
            company_risk          = dr.company_risk,
            strategy_risk         = dr.strategy_risk,
            execution_risk        = dr.execution_risk,
            confidence_risk_score = dr.confidence_risk,
            overall_risk          = risk_snapshot.overall_risk,
            risk_level            = risk_snapshot.risk_level.value,
            outcome               = outcome,
        )
        return trace

    def traceability_level(self, trace: DecisionTrace) -> TraceabilityLevel:
        return _derive_traceability_level(
            trace.evidence_node_count,
            trace.reasoning_node_count,
            trace.traced_evidence_fraction,
        )
