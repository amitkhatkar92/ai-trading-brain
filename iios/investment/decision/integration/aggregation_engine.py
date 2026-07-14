"""iios/investment/decision/integration/aggregation_engine.py
Stateless logic layer for creating and updating AggregationState objects.
"""
from __future__ import annotations

from typing import Any, Optional

from iios.investment.decision.confidence.confidence_snapshot import ConfidenceSnapshot
from iios.investment.decision.evidence.evidence_snapshot import EvidenceSnapshot
from iios.investment.decision.explainability.explanation_snapshot import ExplanationSnapshot
from iios.investment.decision.reasoning.reasoning_snapshot import ReasoningSnapshot
from iios.investment.decision.risk.risk_snapshot import RiskSnapshot

from iios.investment.decision.integration.aggregation_state import AggregationState
from iios.investment.decision.integration.integration_constants import ComponentId


class AggregationEngine:
    """
    Stateless aggregation logic.  Accepts upstream snapshots and merges
    them into an AggregationState without holding any mutable state itself.
    Thread safety is the caller's responsibility (via AggregationState locks).
    """

    def create(
        self,
        decision_id:    str,
        subject_id:     str,
        subject_type:   str,
        evidence:       Optional[EvidenceSnapshot]    = None,
        reasoning:      Optional[ReasoningSnapshot]   = None,
        confidence:     Optional[ConfidenceSnapshot]  = None,
        risk:           Optional[RiskSnapshot]        = None,
        explanation:    Optional[ExplanationSnapshot] = None,
        committee:      Optional[Any]                 = None,
        recommendation: Optional[Any]                 = None,
    ) -> AggregationState:
        """Create a new AggregationState and populate it."""
        state = AggregationState(decision_id, subject_id, subject_type)
        if evidence       is not None: state.update(ComponentId.EVIDENCE,       evidence)
        if reasoning      is not None: state.update(ComponentId.REASONING,      reasoning)
        if confidence     is not None: state.update(ComponentId.CONFIDENCE,     confidence)
        if risk           is not None: state.update(ComponentId.RISK,           risk)
        if explanation    is not None: state.update(ComponentId.EXPLANATION,    explanation)
        if committee      is not None: state.update(ComponentId.COMMITTEE,      committee)
        if recommendation is not None: state.update(ComponentId.RECOMMENDATION, recommendation)
        return state

    def apply_update(
        self,
        state:     AggregationState,
        component: ComponentId,
        value:     Any,
    ) -> None:
        """
        Apply a single-component update to an existing state.
        Validates that the snapshot's subject_id matches the state.
        """
        # Subject-identity guard — reject cross-subject pollution
        subject = getattr(value, "subject_id", None)
        if subject is not None and subject != state.subject_id:
            raise ValueError(
                f"Subject mismatch: state has '{state.subject_id}' "
                f"but snapshot has '{subject}'"
            )
        state.update(component, value)

    def infer_subject_type(
        self,
        evidence:    Optional[EvidenceSnapshot],
        reasoning:   Optional[ReasoningSnapshot],
        fallback:    str = "equity",
    ) -> str:
        if evidence  is not None: return evidence.subject_type
        if reasoning is not None: return reasoning.subject_type
        return fallback
